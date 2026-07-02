"""
Service de génération d'ontologie
Interface 1 : analyse le contenu du texte et génère des définitions de types d'entités et de
relations adaptées à la simulation sociale
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from ..utils.llm_client import LLMClient
from ..utils.locale import get_language_instruction

logger = logging.getLogger(__name__)


def _to_pascal_case(name: str) -> str:
    """Convertit un nom dans n'importe quel format en PascalCase (ex. 'works_for' -> 'WorksFor', 'person' -> 'Person')"""
    # Découpage sur les caractères non alphanumériques
    parts = re.split(r'[^a-zA-Z0-9]+', name)
    # Puis découpage sur les frontières camelCase (ex. 'camelCase' -> ['camel', 'Case'])
    words = []
    for part in parts:
        words.extend(re.sub(r'([a-z])([A-Z])', r'\1_\2', part).split('_'))
    # Première lettre de chaque mot en majuscule, on filtre les chaînes vides
    result = ''.join(word.capitalize() for word in words if word)
    return result if result else 'Unknown'


# Prompt système pour la génération d'ontologie
# MiroPolis (CLAUDE.md §5.1) : adapté au domaine législatif -- entités = groupes parlementaires,
# segments citoyens (calqués INSEE), institutions publiques, collectivités territoriales, secteurs
# économiques -- au lieu du cadrage "réseaux sociaux" générique de MiroFish.
ONTOLOGY_SYSTEM_PROMPT = """Tu es un expert professionnel en conception d'ontologies pour graphes de connaissances. Ta tâche est d'analyser le contenu du texte législatif fourni et les besoins de simulation, afin de concevoir des types d'entités et de relations adaptés à la **simulation du processus législatif de l'Assemblée Nationale française (MiroPolis)**.

**Important : tu dois produire des données au format JSON valide, sans aucun autre contenu.**

## Contexte central de la tâche

Nous construisons un **système de simulation d'impact législatif (jumeau numérique de l'Assemblée Nationale)**. Dans ce système :
- Chaque entité est soit un **groupe parlementaire** (groupe parlementaire, jamais un député nommé
  individuellement — pour des raisons éthiques et méthodologiques, les données de vote individuelles
  ne servent qu'au calage de backtesting interne et ne sont jamais exposées publiquement), soit un
  **archétype citoyen** (archetype citoyen, pondéré à partir des données démographiques INSEE, et non
  un persona fictif), soit une institution publique / collectivité territoriale / secteur économique
  pertinent
- Les entités débattent entre elles, proposent des amendements, soutiennent ou s'opposent aux articles du texte
- Nous devons simuler les réactions et les points de blocage potentiels que le texte législatif suscite parmi les différentes parties prenantes

Par conséquent, **les entités doivent être des types d'acteurs réellement existants et pertinents pour le processus législatif** :

**Peuvent être retenus** :
- Groupes parlementaires (groupe parlementaire, modélisés par groupe et jamais par député nommé)
- Archétypes citoyens (archétypes démographiques pondérés par âge/catégorie professionnelle/région, comme "jeune actif locataire", "retraité rural")
- Ministères, autorités de régulation
- Collectivités territoriales (régions, départements, communes)
- Représentants de secteurs économiques concernés (ex. secteur du logement, secteur agricole)
- Syndicats, associations professionnelles, ONG
- Organes de presse (médias couvrant les débats législatifs)

**Ne peuvent pas être retenus** :
- Un député ou une personnalité publique nommé individuellement (la modélisation au niveau individuel est réservée au backtesting interne, elle n'apparaît jamais dans l'ontologie)
- Des concepts abstraits (comme "opinion publique", "sentiment", "tendance")
- Le sujet/thème lui-même (comme "réforme du logement", "transition environnementale")
- Une opinion/position (comme "camp favorable", "camp opposé")

## Format de sortie

Merci de produire un JSON avec la structure suivante :

```json
{
    "entity_types": [
        {
            "name": "nom du type d'entité (en anglais, PascalCase)",
            "description": "description courte (en anglais, 100 caractères maximum)",
            "attributes": [
                {
                    "name": "nom de l'attribut (en anglais, snake_case)",
                    "type": "text",
                    "description": "description de l'attribut"
                }
            ],
            "examples": ["exemple d'entité 1", "exemple d'entité 2"]
        }
    ],
    "edge_types": [
        {
            "name": "nom du type de relation (en anglais, UPPER_SNAKE_CASE)",
            "description": "description courte (en anglais, 100 caractères maximum)",
            "source_targets": [
                {"source": "type d'entité source", "target": "type d'entité cible"}
            ],
            "attributes": []
        }
    ],
    "analysis_summary": "brève analyse du contenu du texte"
}
```

## Consignes de conception (extrêmement importantes !)

### 1. Conception des types d'entités - à respecter strictement

**Exigence de quantité : exactement 10 types d'entités**

**Exigence de hiérarchie (types spécifiques et types de repli obligatoires)** :

Tes 10 types d'entités doivent inclure les niveaux suivants :

A. **Types de repli (obligatoires, placés en dernier dans la liste, 2 au total)** :
   - `Person` : type de repli pour les archétypes citoyens (archetype citoyen générique). Lorsqu'un
     archétype démographique n'appartient à aucun autre type plus spécifique, il est classé ici.
     **Ne représente jamais un député nommé individuellement** — la modélisation au niveau des
     groupes parlementaires relève des sous-types spécifiques d'Organization.
   - `Organization` : type de repli pour toute institution/groupe/collectivité. Lorsqu'une
     organisation n'appartient à aucun autre type d'organisation plus spécifique, elle est classée ici.

B. **Types spécifiques (8, à concevoir selon le contenu du texte)** :
   - Concevoir des types plus spécifiques pour les principales parties prenantes évoquées dans le texte du projet de loi
   - Exemple : si le texte porte sur un projet de loi sur le logement, on peut avoir `TenantArchetype`, `LandlordArchetype`, `HousingAgency`
   - Exemple : si le texte porte sur un projet de loi environnemental, on peut avoir `FarmerArchetype`, `EnvironmentalNGO`, `LocalAuthority`
   - **Les groupes parlementaires apparaissent toujours comme un type spécifique** (ex. `ParliamentaryGroup`), jamais modélisés par député nommé

**Pourquoi des types de repli sont nécessaires** :
- Le texte fera apparaître divers archétypes démographiques, comme "travailleur indépendant", "travailleur saisonnier"
- S'il n'existe pas de type spécifique correspondant, ils doivent être classés dans `Person`
- De même, les petites institutions, comités temporaires, etc. doivent être classés dans `Organization`

**Principes de conception des types spécifiques** :
- Identifier dans le texte du projet de loi les types de parties prenantes qui apparaissent fréquemment ou qui sont essentiels
- Chaque type spécifique doit avoir des limites claires, en évitant les chevauchements
- La description doit indiquer clairement la différence entre ce type et le type de repli

### 2. Conception des types de relations

- Quantité : 6 à 10
- Les relations doivent refléter les liens réels du débat législatif (proposer un amendement, soutenir/s'opposer, réguler, représenter des électeurs, etc.)
- S'assurer que les source_targets des relations couvrent les types d'entités définis

### 3. Conception des attributs

- 1 à 3 attributs clés par type d'entité
- **Attention** : les noms d'attributs ne peuvent pas être `name`, `uuid`, `group_id`, `created_at`, `summary` (ce sont des mots réservés du système)
- Utiliser de préférence : `full_name`, `title`, `role`, `position`, `location`, `description`, etc.

## Référence des types d'entités

**Archétypes citoyens (spécifiques, basés sur les dimensions démographiques INSEE)** :
- TenantArchetype : archétype locataire
- LandlordArchetype : archétype propriétaire bailleur
- RuralResidentArchetype : archétype résident rural
- YoungActiveArchetype : archétype jeune actif
- RetireeArchetype : archétype retraité

**Archétypes citoyens (repli)** :
- Person : tout archétype citoyen n'appartenant à aucun des types spécifiques ci-dessus

**Institutions/groupes (spécifiques)** :
- ParliamentaryGroup : groupe parlementaire (ne représente jamais un député nommé)
- LocalAuthority : collectivité territoriale (région/département/commune)
- GovernmentAgency : ministère/autorité de régulation
- EnvironmentalNGO : ONG environnementale
- IndustryAssociation : association professionnelle/syndicat
- MediaOutlet : organe de presse couvrant les débats législatifs

**Institutions/groupes (repli)** :
- Organization : toute institution n'appartenant à aucun des types spécifiques ci-dessus

## Référence des types de relations

- AFFILIATED_WITH : affilié à (un groupe/une institution)
- REPRESENTS : représente (un groupe d'électeurs/un territoire)
- REGULATES : régule
- PROPOSES_AMENDMENT_TO : propose un amendement à...
- SUPPORTS : soutient
- OPPOSES : s'oppose
- REPORTS_ON : couvre médiatiquement
- IMPACTS : impacte (l'effet du texte sur un archétype)
- COLLABORATES_WITH : collabore avec
- ADVOCATES_FOR : défend/fait pression pour
"""


class OntologyGenerator:
    """
    Générateur d'ontologie
    Analyse le contenu du texte et génère les définitions de types d'entités et de relations
    """

    def __init__(self, llm_client: Optional[LLMClient] = None):
        self.llm_client = llm_client or LLMClient()

    def generate(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Génère la définition de l'ontologie

        Args:
            document_texts: liste des textes des documents
            simulation_requirement: description du besoin de simulation
            additional_context: contexte supplémentaire

        Returns:
            Définition de l'ontologie (entity_types, edge_types, etc.)
        """
        # Construction du message utilisateur
        user_message = self._build_user_message(
            document_texts,
            simulation_requirement,
            additional_context
        )
        
        lang_instruction = get_language_instruction()
        system_prompt = f"{ONTOLOGY_SYSTEM_PROMPT}\n\n{lang_instruction}\nIMPORTANT: Entity type names MUST be in English PascalCase (e.g., 'PersonEntity', 'MediaOrganization'). Relationship type names MUST be in English UPPER_SNAKE_CASE (e.g., 'WORKS_FOR'). Attribute names MUST be in English snake_case. Only description fields and analysis_summary should use the specified language above."
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Appel du LLM
        result = self.llm_client.chat_json(
            messages=messages,
            temperature=0.3,
            max_tokens=4096
        )

        # Validation et post-traitement
        result = self._validate_and_process(result)

        return result

    # Longueur maximale du texte envoyé au LLM (50 000 caractères)
    MAX_TEXT_LENGTH_FOR_LLM = 50000

    def _build_user_message(
        self,
        document_texts: List[str],
        simulation_requirement: str,
        additional_context: Optional[str]
    ) -> str:
        """Construit le message utilisateur"""

        # Fusion des textes
        combined_text = "\n\n---\n\n".join(document_texts)
        original_length = len(combined_text)

        # Si le texte dépasse 50 000 caractères, on le tronque (n'affecte que le contenu envoyé au LLM, pas la construction du graphe)
        if len(combined_text) > self.MAX_TEXT_LENGTH_FOR_LLM:
            combined_text = combined_text[:self.MAX_TEXT_LENGTH_FOR_LLM]
            combined_text += f"\n\n...(le texte original comporte {original_length} caractères, seuls les {self.MAX_TEXT_LENGTH_FOR_LLM} premiers ont été retenus pour l'analyse ontologique)..."

        message = f"""## Besoin de simulation

{simulation_requirement}

## Contenu du document

{combined_text}
"""

        if additional_context:
            message += f"""
## Précisions supplémentaires

{additional_context}
"""

        message += """
Merci de concevoir, à partir du contenu ci-dessus, les types d'entités et de relations adaptés à une simulation de l'opinion sociale.

**Règles à respecter impérativement** :
1. Produire exactement 10 types d'entités
2. Les 2 derniers doivent être les types de repli : Person (repli individuel) et Organization (repli organisationnel)
3. Les 8 premiers sont des types spécifiques conçus à partir du contenu du texte
4. Tous les types d'entités doivent être des acteurs pouvant réellement s'exprimer, jamais des concepts abstraits
5. Les noms d'attributs ne peuvent pas utiliser les mots réservés name, uuid, group_id, etc. ; utiliser plutôt full_name, org_name, etc.
"""

        return message

    def _validate_and_process(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Valide et post-traite le résultat"""

        # S'assurer que les champs nécessaires existent
        if "entity_types" not in result:
            result["entity_types"] = []
        if "edge_types" not in result:
            result["edge_types"] = []
        if "analysis_summary" not in result:
            result["analysis_summary"] = ""

        # Validation des types d'entités
        # Enregistre la correspondance entre nom original et PascalCase, pour corriger ensuite les références source_targets des edges
        entity_name_map = {}
        for entity in result["entity_types"]:
            # Force la conversion du nom de l'entité en PascalCase (exigence de l'API Zep)
            if "name" in entity:
                original_name = entity["name"]
                entity["name"] = _to_pascal_case(original_name)
                if entity["name"] != original_name:
                    logger.warning(f"Entity type name '{original_name}' auto-converted to '{entity['name']}'")
                entity_name_map[original_name] = entity["name"]
            if "attributes" not in entity:
                entity["attributes"] = []
            if "examples" not in entity:
                entity["examples"] = []
            # S'assurer que la description ne dépasse pas 100 caractères
            if len(entity.get("description", "")) > 100:
                entity["description"] = entity["description"][:97] + "..."

        # Validation des types de relations
        for edge in result["edge_types"]:
            # Force la conversion du nom de l'edge en SCREAMING_SNAKE_CASE (exigence de l'API Zep)
            if "name" in edge:
                original_name = edge["name"]
                edge["name"] = original_name.upper()
                if edge["name"] != original_name:
                    logger.warning(f"Edge type name '{original_name}' auto-converted to '{edge['name']}'")
            # Corrige les références de noms d'entités dans source_targets pour rester cohérent avec le PascalCase converti
            for st in edge.get("source_targets", []):
                if st.get("source") in entity_name_map:
                    st["source"] = entity_name_map[st["source"]]
                if st.get("target") in entity_name_map:
                    st["target"] = entity_name_map[st["target"]]
            if "source_targets" not in edge:
                edge["source_targets"] = []
            if "attributes" not in edge:
                edge["attributes"] = []
            if len(edge.get("description", "")) > 100:
                edge["description"] = edge["description"][:97] + "..."

        # Limite de l'API Zep : 10 types d'entités personnalisés maximum, 10 types d'edges personnalisés maximum
        MAX_ENTITY_TYPES = 10
        MAX_EDGE_TYPES = 10

        # Déduplication : par name, en conservant la première occurrence
        seen_names = set()
        deduped = []
        for entity in result["entity_types"]:
            name = entity.get("name", "")
            if name and name not in seen_names:
                seen_names.add(name)
                deduped.append(entity)
            elif name in seen_names:
                logger.warning(f"Duplicate entity type '{name}' removed during validation")
        result["entity_types"] = deduped

        # Définition des types de repli
        person_fallback = {
            "name": "Person",
            "description": "Any individual person not fitting other specific person types.",
            "attributes": [
                {"name": "full_name", "type": "text", "description": "Full name of the person"},
                {"name": "role", "type": "text", "description": "Role or occupation"}
            ],
            "examples": ["ordinary citizen", "anonymous netizen"]
        }
        
        organization_fallback = {
            "name": "Organization",
            "description": "Any organization not fitting other specific organization types.",
            "attributes": [
                {"name": "org_name", "type": "text", "description": "Name of the organization"},
                {"name": "org_type", "type": "text", "description": "Type of organization"}
            ],
            "examples": ["small business", "community group"]
        }

        # Vérifie si les types de repli sont déjà présents
        entity_names = {e["name"] for e in result["entity_types"]}
        has_person = "Person" in entity_names
        has_organization = "Organization" in entity_names

        # Types de repli à ajouter
        fallbacks_to_add = []
        if not has_person:
            fallbacks_to_add.append(person_fallback)
        if not has_organization:
            fallbacks_to_add.append(organization_fallback)

        if fallbacks_to_add:
            current_count = len(result["entity_types"])
            needed_slots = len(fallbacks_to_add)

            # Si l'ajout dépasse 10 types, il faut retirer certains types existants
            if current_count + needed_slots > MAX_ENTITY_TYPES:
                # Calcule le nombre à retirer
                to_remove = current_count + needed_slots - MAX_ENTITY_TYPES
                # Retire à partir de la fin (conserve les types spécifiques les plus importants en début de liste)
                result["entity_types"] = result["entity_types"][:-to_remove]

            # Ajout des types de repli
            result["entity_types"].extend(fallbacks_to_add)

        # Vérification finale de la limite (programmation défensive)
        if len(result["entity_types"]) > MAX_ENTITY_TYPES:
            result["entity_types"] = result["entity_types"][:MAX_ENTITY_TYPES]

        if len(result["edge_types"]) > MAX_EDGE_TYPES:
            result["edge_types"] = result["edge_types"][:MAX_EDGE_TYPES]

        return result

    def generate_python_code(self, ontology: Dict[str, Any]) -> str:
        """
        Convertit la définition de l'ontologie en code Python (similaire à ontology.py)

        Args:
            ontology: définition de l'ontologie

        Returns:
            Chaîne de code Python
        """
        code_lines = [
            '"""',
            'Définition des types d\'entités personnalisés',
            'Généré automatiquement par MiroFish, pour la simulation de l\'opinion sociale',
            '"""',
            '',
            'from pydantic import Field',
            'from zep_cloud.external_clients.ontology import EntityModel, EntityText, EdgeModel',
            '',
            '',
            '# ============== Définition des types d\'entités ==============',
            '',
        ]

        # Génération des types d'entités
        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            desc = entity.get("description", f"A {name} entity.")
            
            code_lines.append(f'class {name}(EntityModel):')
            code_lines.append(f'    """{desc}"""')
            
            attrs = entity.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: EntityText = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            
            code_lines.append('')
            code_lines.append('')
        
        code_lines.append('# ============== Définition des types de relations ==============')
        code_lines.append('')

        # Génération des types de relations
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            # Conversion en nom de classe PascalCase
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            desc = edge.get("description", f"A {name} relationship.")
            
            code_lines.append(f'class {class_name}(EdgeModel):')
            code_lines.append(f'    """{desc}"""')
            
            attrs = edge.get("attributes", [])
            if attrs:
                for attr in attrs:
                    attr_name = attr["name"]
                    attr_desc = attr.get("description", attr_name)
                    code_lines.append(f'    {attr_name}: EntityText = Field(')
                    code_lines.append(f'        description="{attr_desc}",')
                    code_lines.append(f'        default=None')
                    code_lines.append(f'    )')
            else:
                code_lines.append('    pass')
            
            code_lines.append('')
            code_lines.append('')
        
        # Génération du dictionnaire des types
        code_lines.append('# ============== Configuration des types ==============')
        code_lines.append('')
        code_lines.append('ENTITY_TYPES = {')
        for entity in ontology.get("entity_types", []):
            name = entity["name"]
            code_lines.append(f'    "{name}": {name},')
        code_lines.append('}')
        code_lines.append('')
        code_lines.append('EDGE_TYPES = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            class_name = ''.join(word.capitalize() for word in name.split('_'))
            code_lines.append(f'    "{name}": {class_name},')
        code_lines.append('}')
        code_lines.append('')
        
        # Génération du mapping source_targets des edges
        code_lines.append('EDGE_SOURCE_TARGETS = {')
        for edge in ontology.get("edge_types", []):
            name = edge["name"]
            source_targets = edge.get("source_targets", [])
            if source_targets:
                st_list = ', '.join([
                    f'{{"source": "{st.get("source", "Entity")}", "target": "{st.get("target", "Entity")}"}}'
                    for st in source_targets
                ])
                code_lines.append(f'    "{name}": [{st_list}],')
        code_lines.append('}')
        
        return '\n'.join(code_lines)

