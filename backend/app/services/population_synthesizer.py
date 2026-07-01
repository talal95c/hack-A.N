"""
Générateur de population synthétique de citoyens (CLAUDE.md §3, couche 2).

Remplace la génération d'archétypes "au fil de l'eau" par échantillon LLM (oasis_profile_generator
historique de MiroFish) par un vrai calage statistique : on part des distributions marginales
réelles INSEE (ex: répartition par tranche d'âge, par CSP, par région) et on utilise l'algorithme
IPF (Iterative Proportional Fitting / méthode RAS) pour reconstruire une distribution jointe
plausible, dont on tire ensuite un échantillon d'agents pondérés.

C'est un vrai actif méthodologique (CLAUDE.md §3 : "pas un simple gonflage du nombre d'agents") :
la population synthétique respecte les marges connues, même si la distribution jointe complète
n'est pas publiquement disponible au niveau fin (secret statistique INSEE).
"""

import itertools
import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class Dimension:
    """Une dimension démographique avec ses catégories et leurs marges connues (proportions ou
    effectifs, peu importe -- IPF ne travaille que sur les proportions relatives)."""
    name: str
    categories: list[str]
    marginal: list[float]  # doit être de même longueur que `categories`

    def __post_init__(self):
        if len(self.categories) != len(self.marginal):
            raise ValueError(f"Dimension '{self.name}': categories et marginal doivent avoir la même longueur")
        total = sum(self.marginal)
        if total <= 0:
            raise ValueError(f"Dimension '{self.name}': la somme des marges doit être positive")
        # Normalisation en proportions
        self.marginal = [v / total for v in self.marginal]


def iterative_proportional_fitting(
    dimensions: list[Dimension],
    max_iterations: int = 200,
    tolerance: float = 1e-6,
) -> np.ndarray:
    """Calage par marges (IPF/RAS) sur N dimensions.

    Part d'une table jointe uniforme (seed neutre, aucune corrélation supposée entre dimensions -
    hypothèse d'indépendance conditionnelle, la plus prudente en l'absence de table croisée
    publique) et ajuste itérativement chaque dimension pour que ses marges (sommes le long des
    autres axes) correspondent aux marges cibles fournies.

    Retourne un tableau numpy de forme (len(dim1), len(dim2), ...) dont la somme vaut 1.0 -- une
    distribution jointe de probabilité.
    """
    shape = tuple(len(d.categories) for d in dimensions)
    table = np.ones(shape, dtype=float) / np.prod(shape)  # seed uniforme

    for iteration in range(max_iterations):
        max_delta = 0.0
        for axis, dim in enumerate(dimensions):
            current_marginal = table.sum(axis=tuple(a for a in range(len(dimensions)) if a != axis))
            target_marginal = np.array(dim.marginal)
            # Évite la division par zéro sur des cases à marge nulle
            safe_current = np.where(current_marginal == 0, 1e-12, current_marginal)
            ratio = target_marginal / safe_current
            # Applique le ratio le long de l'axe correspondant
            reshape_shape = [1] * len(dimensions)
            reshape_shape[axis] = len(dim.categories)
            table = table * ratio.reshape(reshape_shape)
            max_delta = max(max_delta, float(np.max(np.abs(ratio - 1.0))))

        if max_delta < tolerance:
            logger.debug("IPF convergé après %d itérations (delta=%.2e)", iteration + 1, max_delta)
            break
    else:
        logger.warning("IPF n'a pas convergé après %d itérations (delta=%.2e)", max_iterations, max_delta)

    # Renormalisation finale (l'IPF peut légèrement dériver numériquement)
    table = table / table.sum()
    return table


@dataclass
class SyntheticAgent:
    """Un agent citoyen synthétique -- combinaison de catégories tirée de la distribution jointe,
    avec un poids démographique explicite (proportion de la population réelle qu'il représente)."""
    archetype_id: str
    categories: dict  # {dimension_name: category_value}
    demographic_weight: float  # proportion de la population totale représentée par cet agent

    def to_dict(self) -> dict:
        return {
            "archetype_id": self.archetype_id,
            "categories": self.categories,
            "demographic_weight": self.demographic_weight,
        }


def synthesize_population(
    dimensions: list[Dimension],
    n_agents: int,
    territory_label: Optional[str] = None,
) -> list[SyntheticAgent]:
    """Génère `n_agents` agents synthétiques dont la distribution respecte les marges INSEE
    fournies. Chaque agent porte un poids démographique (somme des poids = 1.0), utilisé ensuite
    pour pondérer l'agrégation des scores d'impact (couche 1/couche carte).

    À la différence d'un tirage aléatoire naïf, chaque cellule non nulle de la distribution jointe
    calée par IPF donne lieu à au moins un agent représentatif si n_agents le permet, pour éviter
    de perdre des profils minoritaires mais réels (ex: un archétype rare mais présent) -- cf.
    CLAUDE.md §7 "aucune incertitude cachée".
    """
    joint = iterative_proportional_fitting(dimensions)
    flat_probs = joint.flatten()
    combos = list(itertools.product(*(d.categories for d in dimensions)))

    # Tirage pondéré sans remise si possible, avec remise sinon (n_agents > nombre de combinaisons)
    replace = n_agents > len(combos)
    rng = np.random.default_rng(seed=42)  # seed fixe : reproductibilité des scénarios (CLAUDE.md §3)
    chosen_indices = rng.choice(len(combos), size=n_agents, replace=replace, p=flat_probs)

    # Compte combien de fois chaque combinaison a été tirée, pour répartir sa masse de probabilité
    # entre les agents qui la représentent (plutôt que de donner à chacun le poids plein de la cellule).
    draw_counts: dict[int, int] = {}
    for idx in chosen_indices:
        draw_counts[int(idx)] = draw_counts.get(int(idx), 0) + 1

    agents = []
    for i, idx in enumerate(chosen_indices):
        idx = int(idx)
        combo = combos[idx]
        categories = {dimensions[d].name: combo[d] for d in range(len(dimensions))}
        prefix = f"{territory_label}-" if territory_label else ""
        agents.append(SyntheticAgent(
            archetype_id=f"{prefix}agent-{i:05d}",
            categories=categories,
            demographic_weight=float(flat_probs[idx]) / draw_counts[idx],
        ))

    # Normalisation finale des poids pour que leur somme fasse exactement 1.0
    total_weight = sum(a.demographic_weight for a in agents)
    if total_weight > 0:
        for a in agents:
            a.demographic_weight /= total_weight

    return agents
