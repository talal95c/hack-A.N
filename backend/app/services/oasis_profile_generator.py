"""
Générateur de Profil d'Agent OASIS
Convertit les entités du graphe Zep au format Agent Profile requis par la plateforme de simulation OASIS

Améliorations :
1. Appel à la fonction de recherche Zep pour enrichir les informations du nœud
2. Prompts optimisés pour générer des personas très détaillées
3. Distinction entre entités individuelles et entités de groupe abstraites
"""

import json
import random
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

from openai import OpenAI
from zep_cloud.client import Zep

from ..config import Config
from ..utils.logger import get_logger
from ..utils.locale import get_language_instruction, get_locale, set_locale, t
from .zep_entity_reader import EntityNode, ZepEntityReader

logger = get_logger('mirofish.oasis_profile')


@dataclass
class OasisAgentProfile:
    """Structure de données du Profil d'Agent OASIS"""
    # Champs communs
    user_id: int
    user_name: str
    name: str
    bio: str
    persona: str

    # Champs optionnels - style Reddit
    karma: int = 1000

    # Champs optionnels - style Twitter
    friend_count: int = 100
    follower_count: int = 150
    statuses_count: int = 500

    # Informations de persona supplémentaires
    age: Optional[int] = None
    gender: Optional[str] = None
    mbti: Optional[str] = None
    country: Optional[str] = None
    profession: Optional[str] = None
    interested_topics: List[str] = field(default_factory=list)

    # Informations sur l'entité source
    source_entity_uuid: Optional[str] = None
    source_entity_type: Optional[str] = None

    created_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d"))

    def to_reddit_format(self) -> Dict[str, Any]:
        """Conversion au format de la plateforme Reddit"""
        profile = {
            "user_id": self.user_id,
            "username": self.user_name,  # La bibliothèque OASIS exige que le champ s'appelle username (sans underscore)
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "created_at": self.created_at,
        }

        # Ajout des informations de persona supplémentaires (si présentes)
        if self.age:
            profile["age"] = self.age
        if self.gender:
            profile["gender"] = self.gender
        if self.mbti:
            profile["mbti"] = self.mbti
        if self.country:
            profile["country"] = self.country
        if self.profession:
            profile["profession"] = self.profession
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics

        return profile

    def to_twitter_format(self) -> Dict[str, Any]:
        """Conversion au format de la plateforme Twitter"""
        profile = {
            "user_id": self.user_id,
            "username": self.user_name,  # La bibliothèque OASIS exige que le champ s'appelle username (sans underscore)
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "created_at": self.created_at,
        }

        # Ajout des informations de persona supplémentaires
        if self.age:
            profile["age"] = self.age
        if self.gender:
            profile["gender"] = self.gender
        if self.mbti:
            profile["mbti"] = self.mbti
        if self.country:
            profile["country"] = self.country
        if self.profession:
            profile["profession"] = self.profession
        if self.interested_topics:
            profile["interested_topics"] = self.interested_topics
        
        return profile
    
    def to_dict(self) -> Dict[str, Any]:
        """Conversion au format dictionnaire complet"""
        return {
            "user_id": self.user_id,
            "user_name": self.user_name,
            "name": self.name,
            "bio": self.bio,
            "persona": self.persona,
            "karma": self.karma,
            "friend_count": self.friend_count,
            "follower_count": self.follower_count,
            "statuses_count": self.statuses_count,
            "age": self.age,
            "gender": self.gender,
            "mbti": self.mbti,
            "country": self.country,
            "profession": self.profession,
            "interested_topics": self.interested_topics,
            "source_entity_uuid": self.source_entity_uuid,
            "source_entity_type": self.source_entity_type,
            "created_at": self.created_at,
        }


class OasisProfileGenerator:
    """
    Générateur de Profil OASIS

    Convertit les entités du graphe Zep en Agent Profile requis par la simulation OASIS

    Caractéristiques :
    1. Appel à la fonction de recherche du graphe Zep pour obtenir un contexte plus riche
    2. Génération de personas très détaillées (informations de base, parcours professionnel, traits de caractère, comportement sur les réseaux sociaux, etc.)
    3. Distinction entre entités individuelles et entités de groupe abstraites
    """

    # Liste des types MBTI
    MBTI_TYPES = [
        "INTJ", "INTP", "ENTJ", "ENTP",
        "INFJ", "INFP", "ENFJ", "ENFP",
        "ISTJ", "ISFJ", "ESTJ", "ESFJ",
        "ISTP", "ISFP", "ESTP", "ESFP"
    ]

    # Liste des pays courants
    COUNTRIES = [
        "China", "US", "UK", "Japan", "Germany", "France",
        "Canada", "Australia", "Brazil", "India", "South Korea"
    ]

    # Entités de type individuel (nécessitent la génération d'une persona concrète)
    # Hérité de l'ancien MiroFish (campus) -- conservé en repli pour compatibilité ascendante.
    INDIVIDUAL_ENTITY_TYPES = [
        "student", "alumni", "professor", "person", "publicfigure",
        "expert", "faculty", "official", "journalist", "activist"
    ]

    # Entités de type groupe/institution (nécessitent la génération d'une persona représentative du groupe)
    # Hérité de l'ancien MiroFish (campus) -- conservé en repli pour compatibilité ascendante.
    GROUP_ENTITY_TYPES = [
        "university", "governmentagency", "organization", "ngo",
        "mediaoutlet", "company", "institution", "group", "community"
    ]

    # Fragments de nom de type indiquant une institution/un groupe (ex: ParliamentaryGroup,
    # EnvironmentalNGO, IndustryAssociation, LocalAuthority) -- l'ontology generator invente ces
    # noms par document (CLAUDE.md §1/§5), donc on matche sur un motif plutôt qu'une liste figée.
    GROUP_TYPE_SUBSTRINGS = [
        "parliamentarygroup", "organization", "agency", "authority", "association", "ngo",
    ]
    
    def __init__(
        self, 
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        zep_api_key: Optional[str] = None,
        graph_id: Optional[str] = None
    ):
        self.api_key = api_key or Config.LLM_API_KEY
        self.base_url = base_url or Config.LLM_BASE_URL
        self.model_name = model_name or Config.LLM_MODEL_NAME
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY non configurée")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

        # Client Zep utilisé pour récupérer un contexte enrichi
        self.zep_api_key = zep_api_key or Config.ZEP_API_KEY
        self.zep_client = None
        self.graph_id = graph_id

        if self.zep_api_key:
            try:
                self.zep_client = Zep(api_key=self.zep_api_key)
            except Exception as e:
                logger.warning(f"Échec de l'initialisation du client Zep : {e}")
    
    def generate_profile_from_entity(
        self, 
        entity: EntityNode, 
        user_id: int,
        use_llm: bool = True
    ) -> OasisAgentProfile:
        """
        Génère un Agent Profile OASIS à partir d'une entité Zep

        Args:
            entity: Nœud d'entité Zep
            user_id: ID utilisateur (pour OASIS)
            use_llm: Utiliser ou non le LLM pour générer une persona détaillée

        Returns:
            OasisAgentProfile
        """
        entity_type = entity.get_entity_type() or "Entity"

        # Informations de base
        name = entity.name
        user_name = self._generate_username(name)

        # Construction des informations de contexte
        context = self._build_entity_context(entity)

        if use_llm:
            # Utilisation du LLM pour générer une persona détaillée
            profile_data = self._generate_profile_with_llm(
                entity_name=name,
                entity_type=entity_type,
                entity_summary=entity.summary,
                entity_attributes=entity.attributes,
                context=context
            )
        else:
            # Utilisation de règles pour générer une persona de base
            profile_data = self._generate_profile_rule_based(
                entity_name=name,
                entity_type=entity_type,
                entity_summary=entity.summary,
                entity_attributes=entity.attributes
            )
        
        return OasisAgentProfile(
            user_id=user_id,
            user_name=user_name,
            name=name,
            bio=profile_data.get("bio", f"{entity_type}: {name}"),
            persona=profile_data.get("persona", entity.summary or f"A {entity_type} named {name}."),
            karma=profile_data.get("karma", random.randint(500, 5000)),
            friend_count=profile_data.get("friend_count", random.randint(50, 500)),
            follower_count=profile_data.get("follower_count", random.randint(100, 1000)),
            statuses_count=profile_data.get("statuses_count", random.randint(100, 2000)),
            age=profile_data.get("age"),
            gender=profile_data.get("gender"),
            mbti=profile_data.get("mbti"),
            country=profile_data.get("country"),
            profession=profile_data.get("profession"),
            interested_topics=profile_data.get("interested_topics", []),
            source_entity_uuid=entity.uuid,
            source_entity_type=entity_type,
        )
    
    def _generate_username(self, name: str) -> str:
        """Génère un nom d'utilisateur"""
        # Suppression des caractères spéciaux, conversion en minuscules
        username = name.lower().replace(" ", "_")
        username = ''.join(c for c in username if c.isalnum() or c == '_')

        # Ajout d'un suffixe aléatoire pour éviter les doublons
        suffix = random.randint(100, 999)
        return f"{username}_{suffix}"

    def _search_zep_for_entity(self, entity: EntityNode) -> Dict[str, Any]:
        """
        Utilise la fonction de recherche hybride du graphe Zep pour obtenir des informations enrichies sur l'entité

        Zep n'a pas d'interface de recherche hybride intégrée : il faut chercher séparément
        dans les edges et les nodes, puis fusionner les résultats.
        Utilise des requêtes parallèles pour améliorer l'efficacité.

        Args:
            entity: Objet nœud d'entité

        Returns:
            Dictionnaire contenant facts, node_summaries, context
        """
        import concurrent.futures

        if not self.zep_client:
            return {"facts": [], "node_summaries": [], "context": ""}

        entity_name = entity.name

        results = {
            "facts": [],
            "node_summaries": [],
            "context": ""
        }

        # graph_id est requis pour effectuer la recherche
        if not self.graph_id:
            logger.debug(f"Recherche Zep ignorée : graph_id non défini")
            return results

        comprehensive_query = t('progress.zepSearchQuery', name=entity_name)

        def search_edges():
            """Recherche des edges (faits/relations) - avec mécanisme de nouvelle tentative"""
            max_retries = 3
            last_exception = None
            delay = 2.0

            for attempt in range(max_retries):
                try:
                    return self.zep_client.graph.search(
                        query=comprehensive_query,
                        graph_id=self.graph_id,
                        limit=30,
                        scope="edges",
                        reranker="rrf"
                    )
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.debug(f"Échec de la recherche d'edges Zep, tentative {attempt + 1} : {str(e)[:80]}, nouvelle tentative...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.debug(f"Échec de la recherche d'edges Zep après {max_retries} tentatives : {e}")
            return None

        def search_nodes():
            """Recherche des nodes (résumés d'entités) - avec mécanisme de nouvelle tentative"""
            max_retries = 3
            last_exception = None
            delay = 2.0

            for attempt in range(max_retries):
                try:
                    return self.zep_client.graph.search(
                        query=comprehensive_query,
                        graph_id=self.graph_id,
                        limit=20,
                        scope="nodes",
                        reranker="rrf"
                    )
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.debug(f"Échec de la recherche de nodes Zep, tentative {attempt + 1} : {str(e)[:80]}, nouvelle tentative...")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        logger.debug(f"Échec de la recherche de nodes Zep après {max_retries} tentatives : {e}")
            return None
        
        try:
            # Exécution en parallèle des recherches edges et nodes
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                edge_future = executor.submit(search_edges)
                node_future = executor.submit(search_nodes)

                # Récupération des résultats
                edge_result = edge_future.result(timeout=30)
                node_result = node_future.result(timeout=30)

            # Traitement des résultats de recherche des edges
            all_facts = set()
            if edge_result and hasattr(edge_result, 'edges') and edge_result.edges:
                for edge in edge_result.edges:
                    if hasattr(edge, 'fact') and edge.fact:
                        all_facts.add(edge.fact)
            results["facts"] = list(all_facts)

            # Traitement des résultats de recherche des nodes
            all_summaries = set()
            if node_result and hasattr(node_result, 'nodes') and node_result.nodes:
                for node in node_result.nodes:
                    if hasattr(node, 'summary') and node.summary:
                        all_summaries.add(node.summary)
                    if hasattr(node, 'name') and node.name and node.name != entity_name:
                        all_summaries.add(f"Entité liée : {node.name}")
            results["node_summaries"] = list(all_summaries)

            # Construction du contexte global
            context_parts = []
            if results["facts"]:
                context_parts.append("Informations factuelles :\n" + "\n".join(f"- {f}" for f in results["facts"][:20]))
            if results["node_summaries"]:
                context_parts.append("Entités liées :\n" + "\n".join(f"- {s}" for s in results["node_summaries"][:10]))
            results["context"] = "\n\n".join(context_parts)

            logger.info(f"Recherche hybride Zep terminée : {entity_name}, {len(results['facts'])} faits obtenus, {len(results['node_summaries'])} nœuds liés")

        except concurrent.futures.TimeoutError:
            logger.warning(f"Délai d'attente dépassé pour la recherche Zep ({entity_name})")
        except Exception as e:
            logger.warning(f"Échec de la recherche Zep ({entity_name}) : {e}")

        return results

    def _build_entity_context(self, entity: EntityNode) -> str:
        """
        Construit les informations de contexte complètes de l'entité

        Comprend :
        1. Les informations d'edges de l'entité elle-même (faits)
        2. Les informations détaillées des nœuds liés
        3. Les informations enrichies obtenues via la recherche hybride Zep
        """
        context_parts = []

        # 1. Ajout des informations d'attributs de l'entité
        if entity.attributes:
            attrs = []
            for key, value in entity.attributes.items():
                if value and str(value).strip():
                    attrs.append(f"- {key}: {value}")
            if attrs:
                context_parts.append("### Attributs de l'entité\n" + "\n".join(attrs))

        # 2. Ajout des informations d'edges liées (faits/relations)
        existing_facts = set()
        if entity.related_edges:
            relationships = []
            for edge in entity.related_edges:  # Aucune limite de nombre
                fact = edge.get("fact", "")
                edge_name = edge.get("edge_name", "")
                direction = edge.get("direction", "")

                if fact:
                    relationships.append(f"- {fact}")
                    existing_facts.add(fact)
                elif edge_name:
                    if direction == "outgoing":
                        relationships.append(f"- {entity.name} --[{edge_name}]--> (entité liée)")
                    else:
                        relationships.append(f"- (entité liée) --[{edge_name}]--> {entity.name}")

            if relationships:
                context_parts.append("### Faits et relations liés\n" + "\n".join(relationships))

        # 3. Ajout des informations détaillées des nœuds liés
        if entity.related_nodes:
            related_info = []
            for node in entity.related_nodes:  # Aucune limite de nombre
                node_name = node.get("name", "")
                node_labels = node.get("labels", [])
                node_summary = node.get("summary", "")

                # Filtrage des labels par défaut
                custom_labels = [l for l in node_labels if l not in ["Entity", "Node"]]
                label_str = f" ({', '.join(custom_labels)})" if custom_labels else ""

                if node_summary:
                    related_info.append(f"- **{node_name}**{label_str}: {node_summary}")
                else:
                    related_info.append(f"- **{node_name}**{label_str}")

            if related_info:
                context_parts.append("### Informations sur les entités liées\n" + "\n".join(related_info))

        # 4. Utilisation de la recherche hybride Zep pour obtenir des informations plus riches
        zep_results = self._search_zep_for_entity(entity)

        if zep_results.get("facts"):
            # Déduplication : exclusion des faits déjà existants
            new_facts = [f for f in zep_results["facts"] if f not in existing_facts]
            if new_facts:
                context_parts.append("### Informations factuelles obtenues via Zep\n" + "\n".join(f"- {f}" for f in new_facts[:15]))

        if zep_results.get("node_summaries"):
            context_parts.append("### Nœuds liés obtenus via Zep\n" + "\n".join(f"- {s}" for s in zep_results["node_summaries"][:10]))

        return "\n\n".join(context_parts)

    def _is_individual_entity(self, entity_type: str) -> bool:
        """Détermine s'il s'agit d'une entité de type individuel (archétype citoyen MiroPolis, ou
        type hérité de l'ancien MiroFish). Les archétypes citoyens sont nommés dynamiquement par
        document par l'ontology generator (TenantArchetype, RuralResidentArchetype, ...), d'où le
        suffixe "archetype" en plus de la liste figée héritée."""
        t = entity_type.lower()
        if t in self.INDIVIDUAL_ENTITY_TYPES:
            return True
        if t.endswith("archetype"):
            return True
        return not self._is_group_entity(entity_type)

    def _is_group_entity(self, entity_type: str) -> bool:
        """Détermine s'il s'agit d'une entité de type groupe/institution (groupe parlementaire
        MiroPolis, ou type hérité de l'ancien MiroFish)."""
        t = entity_type.lower()
        if t in self.GROUP_ENTITY_TYPES:
            return True
        return any(fragment in t for fragment in self.GROUP_TYPE_SUBSTRINGS)
    
    def _generate_profile_with_llm(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> Dict[str, Any]:
        """
        Utilise le LLM pour générer une persona très détaillée

        Distinction selon le type d'entité :
        - Entité individuelle : génère une persona de personnage concrète
        - Entité de groupe/institution : génère une persona de compte représentatif
        """

        is_individual = self._is_individual_entity(entity_type)
        
        if is_individual:
            prompt = self._build_individual_persona_prompt(
                entity_name, entity_type, entity_summary, entity_attributes, context
            )
        else:
            prompt = self._build_group_persona_prompt(
                entity_name, entity_type, entity_summary, entity_attributes, context
            )

        # Plusieurs tentatives de génération, jusqu'au succès ou au nombre maximal de tentatives
        max_attempts = 3
        last_error = None

        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": self._get_system_prompt(is_individual)},
                        {"role": "user", "content": prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.7 - (attempt * 0.1)  # Baisse de la température à chaque nouvelle tentative
                    # Pas de max_tokens défini, pour laisser le LLM s'exprimer librement
                )

                content = response.choices[0].message.content

                # Vérification d'une éventuelle troncature (finish_reason différent de 'stop')
                finish_reason = response.choices[0].finish_reason
                if finish_reason == 'length':
                    logger.warning(f"Sortie LLM tronquée (tentative {attempt+1}), tentative de réparation...")
                    content = self._fix_truncated_json(content)

                # Tentative de parsing du JSON
                try:
                    result = json.loads(content)

                    # Validation des champs requis
                    if "bio" not in result or not result["bio"]:
                        result["bio"] = entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}"
                    if "persona" not in result or not result["persona"]:
                        result["persona"] = entity_summary or f"{entity_name} est un(e) {entity_type}."

                    return result

                except json.JSONDecodeError as je:
                    logger.warning(f"Échec du parsing JSON (tentative {attempt+1}) : {str(je)[:80]}")

                    # Tentative de réparation du JSON
                    result = self._try_fix_json(content, entity_name, entity_type, entity_summary)
                    if result.get("_fixed"):
                        del result["_fixed"]
                        return result

                    last_error = je

            except Exception as e:
                logger.warning(f"Échec de l'appel LLM (tentative {attempt+1}) : {str(e)[:80]}")
                last_error = e
                import time
                time.sleep(1 * (attempt + 1))  # Backoff exponentiel

        logger.warning(f"Échec de la génération de persona par le LLM ({max_attempts} tentatives) : {last_error}, génération par règles utilisée")
        return self._generate_profile_rule_based(
            entity_name, entity_type, entity_summary, entity_attributes
        )

    def _fix_truncated_json(self, content: str) -> str:
        """Répare un JSON tronqué (sortie tronquée par la limite max_tokens)"""
        import re

        # Si le JSON est tronqué, tentative de le fermer
        content = content.strip()

        # Calcul des accolades non fermées
        open_braces = content.count('{') - content.count('}')
        open_brackets = content.count('[') - content.count(']')

        # Vérification d'une éventuelle chaîne non fermée
        # Vérification simple : si le dernier guillemet n'est suivi ni d'une virgule ni d'une accolade fermante, la chaîne a peut-être été tronquée
        if content and content[-1] not in '",}]':
            # Tentative de fermeture de la chaîne
            content += '"'

        # Fermeture des accolades/crochets
        content += ']' * open_brackets
        content += '}' * open_braces

        return content

    def _try_fix_json(self, content: str, entity_name: str, entity_type: str, entity_summary: str = "") -> Dict[str, Any]:
        """Tente de réparer un JSON corrompu"""
        import re

        # 1. Tentative de réparation du cas tronqué en premier
        content = self._fix_truncated_json(content)

        # 2. Tentative d'extraction de la partie JSON
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            json_str = json_match.group()

            # 3. Traitement des sauts de ligne dans les chaînes
            # Repère toutes les valeurs de chaîne et remplace les sauts de ligne qu'elles contiennent
            def fix_string_newlines(match):
                s = match.group(0)
                # Remplacement des sauts de ligne réels dans la chaîne par des espaces
                s = s.replace('\n', ' ').replace('\r', ' ')
                # Remplacement des espaces multiples
                s = re.sub(r'\s+', ' ', s)
                return s

            # Correspondance des valeurs de chaîne JSON
            json_str = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', fix_string_newlines, json_str)

            # 4. Tentative de parsing
            try:
                result = json.loads(json_str)
                result["_fixed"] = True
                return result
            except json.JSONDecodeError as e:
                # 5. Si l'échec persiste, tentative de réparation plus agressive
                try:
                    # Suppression de tous les caractères de contrôle
                    json_str = re.sub(r'[\x00-\x1f\x7f-\x9f]', ' ', json_str)
                    # Remplacement de tous les espaces multiples
                    json_str = re.sub(r'\s+', ' ', json_str)
                    result = json.loads(json_str)
                    result["_fixed"] = True
                    return result
                except:
                    pass

        # 6. Tentative d'extraction d'informations partielles du contenu
        bio_match = re.search(r'"bio"\s*:\s*"([^"]*)"', content)
        persona_match = re.search(r'"persona"\s*:\s*"([^"]*)', content)  # Peut être tronqué

        bio = bio_match.group(1) if bio_match else (entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}")
        persona = persona_match.group(1) if persona_match else (entity_summary or f"{entity_name} est un(e) {entity_type}.")

        # Si des informations significatives ont été extraites, marquer comme réparé
        if bio_match or persona_match:
            logger.info(f"Informations partielles extraites d'un JSON corrompu")
            return {
                "bio": bio,
                "persona": persona,
                "_fixed": True
            }

        # 7. Échec complet, retour d'une structure de base
        logger.warning(f"Échec de la réparation du JSON, retour d'une structure de base")
        return {
            "bio": entity_summary[:200] if entity_summary else f"{entity_type}: {entity_name}",
            "persona": entity_summary or f"{entity_name} est un(e) {entity_type}."
        }
    
    def _get_system_prompt(self, is_individual: bool) -> str:
        """Récupère le prompt système
        MiroPolis (CLAUDE.md §5.2) : deux types de profils -- archétype citoyen (pondéré sur les données
        démographiques INSEE, persona non fictive) et groupe parlementaire (modélisé par groupe,
        ne représente jamais un député nommé)."""
        if is_individual:
            base_prompt = (
                "Tu es un expert en génération d'archétypes citoyens (archetype citoyen). Ta tâche est de générer, "
                "à partir de données démographiques INSEE (âge, catégorie socioprofessionnelle CSP, région, revenu), "
                "un archétype citoyen représentatif, destiné à la simulation d'impact législatif. "
                "Il ne s'agit pas d'une 'persona d'influenceur' fictive, mais d'un archétype démographique statistiquement "
                "plausible, dont les attitudes et réactions doivent refléter les enjeux réels du texte de loi pour sa "
                "situation socio-économique. Cet archétype réagit au débat porté par les groupes parlementaires -- il "
                "commente/évalue, il n'ouvre pas le débat -- et ses réactions portent toujours sur l'impact concret sur "
                "son pouvoir d'achat, l'environnement, ou les services publics. Tu dois impérativement renvoyer un JSON "
                "valide, aucune valeur de chaîne ne doit contenir de saut de ligne non échappé."
            )
        else:
            base_prompt = (
                "Tu es un expert en génération de profils de groupes parlementaires (groupe parlementaire). Ta tâche est "
                "de générer, à partir de la composition réelle de ce groupe à l'Assemblée nationale, de son nombre de "
                "sièges et de sa ligne politique (contextualisés par les données ouvertes Tricoteuses), un profil destiné "
                "à la simulation de débat législatif. Ce groupe débat, propose des amendements et s'oppose à ceux des "
                "autres groupes sur le texte soumis. **Il ne doit en aucun cas représenter ou faire allusion à un député "
                "nommé individuellement** — seule la ligne politique du groupe dans son ensemble est concernée. Tu dois "
                "impérativement renvoyer un JSON valide, aucune valeur de chaîne ne doit contenir de saut de ligne non échappé."
            )
        return f"{base_prompt}\n\n{get_language_instruction()}"
    
    def _build_individual_persona_prompt(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> str:
        """Construit le prompt de persona détaillée pour une entité individuelle"""

        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "aucun"
        context_str = context[:3000] if context else "aucun contexte supplémentaire"

        return f"""Génère une persona détaillée d'archétype citoyen (archetype citoyen), pondérée sur des données
démographiques INSEE, destinée à la simulation d'impact législatif — ce n'est pas une persona fictive
d'influenceur des réseaux sociaux, mais un archétype démographique statistiquement plausible.

Nom de l'entité : {entity_name}
Type d'entité : {entity_type}
Résumé de l'entité : {entity_summary}
Attributs de l'entité : {attrs_str}

Informations de contexte (pouvant inclure des données démographiques INSEE : tranche d'âge / catégorie
socioprofessionnelle CSP / région / distribution de revenus) :
{context_str}

Génère un JSON contenant les champs suivants :

1. bio : biographie pour réseau social, 200 caractères
2. persona : description détaillée de la persona (texte brut de 2000 caractères), devant inclure :
   - Informations de base (âge, profession, formation, lieu de résidence)
   - Contexte du personnage (expériences importantes, lien avec l'événement, relations sociales)
   - Traits de caractère (type MBTI, personnalité principale, mode d'expression émotionnelle)
   - Comportement sur les réseaux sociaux : cet archétype **réagit** aux publications des groupes
     parlementaires (commente/répond sous leurs posts) plutôt que d'ouvrir de nouveaux sujets de son
     propre chef -- son rôle est de réagir au débat, pas de l'initier
   - Positions et opinions : ses réactions doivent systématiquement porter sur l'impact concret du
     texte de loi sur **son pouvoir d'achat, l'environnement, et les services publics dont il dépend**
     (les 3 axes d'évaluation de cet archétype) -- pas une réaction générique "content/pas content"
   - Traits particuliers (expressions favorites, expériences singulières, loisirs personnels)
   - Mémoire personnelle (partie importante de la persona : décrire le lien de cet individu avec l'événement, ainsi que ses actions et réactions déjà observées dans l'événement)
3. age : nombre correspondant à l'âge (doit être un entier)
4. gender : genre, doit être en anglais : "male" ou "female"
5. mbti : type MBTI (ex. INTJ, ENFP, etc.)
6. country : pays (utiliser le français, ex. « France »)
7. profession : profession
8. interested_topics : tableau des sujets d'intérêt

Important :
- Toutes les valeurs de champs doivent être des chaînes ou des nombres, sans sauts de ligne
- persona doit être un texte cohérent et continu
- {get_language_instruction()} (le champ gender doit rester en anglais male/female)
- Le contenu doit rester cohérent avec les informations de l'entité
- age doit être un entier valide, gender doit être "male" ou "female"
"""

    def _build_group_persona_prompt(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any],
        context: str
    ) -> str:
        """Construit le prompt de persona détaillée pour une entité de groupe/institution"""

        attrs_str = json.dumps(entity_attributes, ensure_ascii=False) if entity_attributes else "aucun"
        context_str = context[:3000] if context else "aucun contexte supplémentaire"

        return f"""Génère un profil détaillé pour un groupe parlementaire ou une entité institutionnelle, destiné à
la simulation de débat législatif. S'il s'agit d'un groupe parlementaire (ParliamentaryGroup), il doit être
modélisé à partir de son nombre de sièges réel à l'Assemblée nationale et de sa ligne politique, **et ne doit
en aucun cas représenter ou faire allusion à un député nommé individuellement** — seule la ligne politique du
groupe dans son ensemble est concernée (calibrée à partir des données ouvertes Tricoteuses).

Nom de l'entité : {entity_name}
Type d'entité : {entity_type}
Résumé de l'entité : {entity_summary}
Attributs de l'entité : {attrs_str}

Informations de contexte (pouvant inclure des données ouvertes Tricoteuses : composition du groupe,
tendances de vote historiques, amendements précédents) :
{context_str}

Génère un JSON contenant les champs suivants :

1. bio : biographie du compte officiel, 200 caractères, professionnelle et appropriée
2. persona : description détaillée du compte (texte brut de 2000 caractères), devant inclure :
   - Informations institutionnelles de base (nom officiel, nature de l'institution, contexte de création, fonctions principales)
   - Positionnement du compte (type de compte, public cible, fonction principale)
   - Style d'expression (particularités de langage, expressions courantes, sujets tabous)
   - Caractéristiques du contenu publié : s'il s'agit d'un groupe parlementaire, son rôle est de
     **proposer, débattre et s'opposer aux amendements** du texte soumis, et d'argumenter en réponse
     aux positions publiées par les autres groupes -- pas de publier du contenu social générique
   - Positions et attitude (position officielle sur les sujets centraux, gestion des controverses)
   - Remarques particulières (profil du groupe représenté, habitudes de gestion du compte)
   - Mémoire institutionnelle (partie importante de la persona institutionnelle : décrire le lien de cette institution avec l'événement, ainsi que ses actions et réactions déjà observées dans l'événement)
3. age : fixé à 30 (âge fictif du compte institutionnel)
4. gender : fixé à "other" (les comptes institutionnels utilisent other pour indiquer qu'il ne s'agit pas d'une personne)
5. mbti : type MBTI, utilisé pour décrire le style du compte, ex. ISTJ pour un style rigoureux et conservateur
6. country : pays (utiliser le français, ex. « France »)
7. profession : description de la fonction institutionnelle
8. interested_topics : tableau des domaines d'intérêt

Important :
- Toutes les valeurs de champs doivent être des chaînes ou des nombres, aucune valeur null n'est autorisée
- persona doit être un texte cohérent et continu, sans sauts de ligne
- {get_language_instruction()} (le champ gender doit rester en anglais "other")
- age doit être l'entier 30, gender doit être la chaîne "other"
- Le discours du compte institutionnel doit correspondre à son positionnement identitaire"""
    
    def _generate_profile_rule_based(
        self,
        entity_name: str,
        entity_type: str,
        entity_summary: str,
        entity_attributes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Utilise des règles pour générer une persona de base"""

        # Génère différentes personas selon le type d'entité
        entity_type_lower = entity_type.lower()
        
        if entity_type_lower in ["student", "alumni"]:
            return {
                "bio": f"{entity_type} with interests in academics and social issues.",
                "persona": f"{entity_name} is a {entity_type.lower()} who is actively engaged in academic and social discussions. They enjoy sharing perspectives and connecting with peers.",
                "age": random.randint(18, 30),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(self.MBTI_TYPES),
                "country": random.choice(self.COUNTRIES),
                "profession": "Student",
                "interested_topics": ["Education", "Social Issues", "Technology"],
            }
        
        elif entity_type_lower in ["publicfigure", "expert", "faculty"]:
            return {
                "bio": f"Expert and thought leader in their field.",
                "persona": f"{entity_name} is a recognized {entity_type.lower()} who shares insights and opinions on important matters. They are known for their expertise and influence in public discourse.",
                "age": random.randint(35, 60),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(["ENTJ", "INTJ", "ENTP", "INTP"]),
                "country": random.choice(self.COUNTRIES),
                "profession": entity_attributes.get("occupation", "Expert"),
                "interested_topics": ["Politics", "Economics", "Culture & Society"],
            }
        
        elif entity_type_lower in ["mediaoutlet", "socialmediaplatform"]:
            return {
                "bio": f"Official account for {entity_name}. News and updates.",
                "persona": f"{entity_name} is a media entity that reports news and facilitates public discourse. The account shares timely updates and engages with the audience on current events.",
                "age": 30,  # Âge fictif de l'institution
                "gender": "other",  # Les institutions utilisent other
                "mbti": "ISTJ",  # Style institutionnel : rigoureux et conservateur
                "country": "China",
                "profession": "Media",
                "interested_topics": ["General News", "Current Events", "Public Affairs"],
            }
        
        elif entity_type_lower in ["university", "governmentagency", "ngo", "organization"]:
            return {
                "bio": f"Official account of {entity_name}.",
                "persona": f"{entity_name} is an institutional entity that communicates official positions, announcements, and engages with stakeholders on relevant matters.",
                "age": 30,  # Âge fictif de l'institution
                "gender": "other",  # Les institutions utilisent other
                "mbti": "ISTJ",  # Style institutionnel : rigoureux et conservateur
                "country": "China",
                "profession": entity_type,
                "interested_topics": ["Public Policy", "Community", "Official Announcements"],
            }

        else:
            # Persona par défaut
            return {
                "bio": entity_summary[:150] if entity_summary else f"{entity_type}: {entity_name}",
                "persona": entity_summary or f"{entity_name} is a {entity_type.lower()} participating in social discussions.",
                "age": random.randint(25, 50),
                "gender": random.choice(["male", "female"]),
                "mbti": random.choice(self.MBTI_TYPES),
                "country": random.choice(self.COUNTRIES),
                "profession": entity_type,
                "interested_topics": ["General", "Social Issues"],
            }
    
    def set_graph_id(self, graph_id: str):
        """Définit l'ID du graphe utilisé pour la recherche Zep"""
        self.graph_id = graph_id

    def generate_profiles_from_entities(
        self,
        entities: List[EntityNode],
        use_llm: bool = True,
        progress_callback: Optional[callable] = None,
        graph_id: Optional[str] = None,
        parallel_count: int = 5,
        realtime_output_path: Optional[str] = None,
        output_platform: str = "reddit"
    ) -> List[OasisAgentProfile]:
        """
        Génère des Agent Profile en lot à partir d'entités (génération parallèle prise en charge)

        Args:
            entities: Liste des entités
            use_llm: Utiliser ou non le LLM pour générer une persona détaillée
            progress_callback: Fonction de rappel de progression (current, total, message)
            graph_id: ID du graphe, utilisé pour la recherche Zep afin d'obtenir un contexte plus riche
            parallel_count: Nombre de générations en parallèle, 5 par défaut
            realtime_output_path: Chemin du fichier d'écriture en temps réel (si fourni, écriture à chaque génération)
            output_platform: Format de la plateforme de sortie ("reddit" ou "twitter")

        Returns:
            Liste des Agent Profile
        """
        import concurrent.futures
        from threading import Lock

        # Définition du graph_id pour la recherche Zep
        if graph_id:
            self.graph_id = graph_id

        total = len(entities)
        profiles = [None] * total  # Liste préallouée pour conserver l'ordre
        completed_count = [0]  # Utilisation d'une liste pour permettre la modification dans la closure
        lock = Lock()

        # Fonction d'aide pour l'écriture en temps réel dans le fichier
        def save_profiles_realtime():
            """Sauvegarde en temps réel les profiles déjà générés dans le fichier"""
            if not realtime_output_path:
                return

            with lock:
                # Filtrage des profiles déjà générés
                existing_profiles = [p for p in profiles if p is not None]
                if not existing_profiles:
                    return

                try:
                    if output_platform == "reddit":
                        # Format JSON Reddit
                        profiles_data = [p.to_reddit_format() for p in existing_profiles]
                        with open(realtime_output_path, 'w', encoding='utf-8') as f:
                            json.dump(profiles_data, f, ensure_ascii=False, indent=2)
                    else:
                        # Format CSV Twitter
                        import csv
                        profiles_data = [p.to_twitter_format() for p in existing_profiles]
                        if profiles_data:
                            fieldnames = list(profiles_data[0].keys())
                            with open(realtime_output_path, 'w', encoding='utf-8', newline='') as f:
                                writer = csv.DictWriter(f, fieldnames=fieldnames)
                                writer.writeheader()
                                writer.writerows(profiles_data)
                except Exception as e:
                    logger.warning(f"Échec de la sauvegarde en temps réel des profiles : {e}")
        
        # Capture locale before spawning thread pool workers
        current_locale = get_locale()

        def generate_single_profile(idx: int, entity: EntityNode) -> tuple:
            """Fonction de travail pour générer un seul profile"""
            set_locale(current_locale)
            entity_type = entity.get_entity_type() or "Entity"

            try:
                profile = self.generate_profile_from_entity(
                    entity=entity,
                    user_id=idx,
                    use_llm=use_llm
                )

                # Affichage en temps réel de la persona générée dans la console et le log
                self._print_generated_profile(entity.name, entity_type, profile)

                return idx, profile, None

            except Exception as e:
                logger.error(f"Échec de la génération de la persona de l'entité {entity.name} : {str(e)}")
                # Création d'un profile de base
                fallback_profile = OasisAgentProfile(
                    user_id=idx,
                    user_name=self._generate_username(entity.name),
                    name=entity.name,
                    bio=f"{entity_type}: {entity.name}",
                    persona=entity.summary or f"A participant in social discussions.",
                    source_entity_uuid=entity.uuid,
                    source_entity_type=entity_type,
                )
                return idx, fallback_profile, str(e)

        logger.info(f"Début de la génération parallèle de {total} personas d'Agent (parallélisme : {parallel_count})...")
        print(f"\n{'='*60}")
        print(f"Début de la génération des personas d'Agent - {total} entités au total, parallélisme : {parallel_count}")
        print(f"{'='*60}\n")

        # Exécution parallèle via un pool de threads
        with concurrent.futures.ThreadPoolExecutor(max_workers=parallel_count) as executor:
            # Soumission de toutes les tâches
            future_to_entity = {
                executor.submit(generate_single_profile, idx, entity): (idx, entity)
                for idx, entity in enumerate(entities)
            }

            # Collecte des résultats
            for future in concurrent.futures.as_completed(future_to_entity):
                idx, entity = future_to_entity[future]
                entity_type = entity.get_entity_type() or "Entity"

                try:
                    result_idx, profile, error = future.result()
                    profiles[result_idx] = profile

                    with lock:
                        completed_count[0] += 1
                        current = completed_count[0]

                    # Écriture en temps réel dans le fichier
                    save_profiles_realtime()

                    if progress_callback:
                        progress_callback(
                            current,
                            total,
                            f"Terminé {current}/{total} : {entity.name} ({entity_type})"
                        )

                    if error:
                        logger.warning(f"[{current}/{total}] {entity.name} utilise la persona de secours : {error}")
                    else:
                        logger.info(f"[{current}/{total}] Persona générée avec succès : {entity.name} ({entity_type})")

                except Exception as e:
                    logger.error(f"Exception lors du traitement de l'entité {entity.name} : {str(e)}")
                    with lock:
                        completed_count[0] += 1
                    profiles[idx] = OasisAgentProfile(
                        user_id=idx,
                        user_name=self._generate_username(entity.name),
                        name=entity.name,
                        bio=f"{entity_type}: {entity.name}",
                        persona=entity.summary or "A participant in social discussions.",
                        source_entity_uuid=entity.uuid,
                        source_entity_type=entity_type,
                    )
                    # Écriture en temps réel dans le fichier (même pour la persona de secours)
                    save_profiles_realtime()

        print(f"\n{'='*60}")
        print(f"Génération des personas terminée ! {len([p for p in profiles if p])} Agents générés au total")
        print(f"{'='*60}\n")

        return profiles

    def _print_generated_profile(self, entity_name: str, entity_type: str, profile: OasisAgentProfile):
        """Affiche en temps réel la persona générée dans la console (contenu complet, sans troncature)"""
        separator = "-" * 70

        # Construction du contenu de sortie complet (sans troncature)
        topics_str = ', '.join(profile.interested_topics) if profile.interested_topics else 'aucun'
        
        output_lines = [
            f"\n{separator}",
            t('progress.profileGenerated', name=entity_name, type=entity_type),
            f"{separator}",
            f"Nom d'utilisateur : {profile.user_name}",
            f"",
            f"[Biographie]",
            f"{profile.bio}",
            f"",
            f"[Persona détaillée]",
            f"{profile.persona}",
            f"",
            f"[Attributs de base]",
            f"Âge : {profile.age} | Genre : {profile.gender} | MBTI : {profile.mbti}",
            f"Profession : {profile.profession} | Pays : {profile.country}",
            f"Sujets d'intérêt : {topics_str}",
            separator
        ]

        output = "\n".join(output_lines)

        # Sortie uniquement dans la console (pour éviter la duplication, le logger n'affiche plus le contenu complet)
        print(output)

    def save_profiles(
        self,
        profiles: List[OasisAgentProfile],
        file_path: str,
        platform: str = "reddit"
    ):
        """
        Sauvegarde les Profile dans un fichier (choix du format correct selon la plateforme)

        Format requis par la plateforme OASIS :
        - Twitter : format CSV
        - Reddit : format JSON

        Args:
            profiles: Liste des Profile
            file_path: Chemin du fichier
            platform: Type de plateforme ("reddit" ou "twitter")
        """
        if platform == "twitter":
            self._save_twitter_csv(profiles, file_path)
        else:
            self._save_reddit_json(profiles, file_path)

    def _save_twitter_csv(self, profiles: List[OasisAgentProfile], file_path: str):
        """
        Sauvegarde les Profile Twitter au format CSV (conforme aux exigences officielles OASIS)

        Champs CSV requis par OASIS Twitter :
        - user_id : ID utilisateur (commence à 0 selon l'ordre du CSV)
        - name : nom réel de l'utilisateur
        - username : nom d'utilisateur dans le système
        - user_char : description détaillée de la persona (injectée dans le prompt système du LLM, guide le comportement de l'Agent)
        - description : biographie publique courte (affichée sur la page de profil de l'utilisateur)

        Différence entre user_char et description :
        - user_char : usage interne, prompt système du LLM, détermine comment l'Agent pense et agit
        - description : affichage externe, biographie visible par les autres utilisateurs
        """
        import csv

        # S'assure que l'extension du fichier est .csv
        if not file_path.endswith('.csv'):
            file_path = file_path.replace('.json', '.csv')

        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Écriture de l'en-tête requis par OASIS
            headers = ['user_id', 'name', 'username', 'user_char', 'description']
            writer.writerow(headers)

            # Écriture des lignes de données
            for idx, profile in enumerate(profiles):
                # user_char : persona complète (bio + persona), utilisée pour le prompt système du LLM
                user_char = profile.bio
                if profile.persona and profile.persona != profile.bio:
                    user_char = f"{profile.bio} {profile.persona}"
                # Traitement des sauts de ligne (remplacés par des espaces dans le CSV)
                user_char = user_char.replace('\n', ' ').replace('\r', ' ')

                # description : biographie courte, pour affichage externe
                description = profile.bio.replace('\n', ' ').replace('\r', ' ')

                row = [
                    idx,                    # user_id : ID séquentiel commençant à 0
                    profile.name,           # name : nom réel
                    profile.user_name,      # username : nom d'utilisateur
                    user_char,              # user_char : persona complète (usage interne LLM)
                    description             # description : biographie courte (affichage externe)
                ]
                writer.writerow(row)

        logger.info(f"{len(profiles)} Profile Twitter sauvegardés dans {file_path} (format CSV OASIS)")

    def _normalize_gender(self, gender: Optional[str]) -> str:
        """
        Normalise le champ gender au format anglais requis par OASIS

        OASIS exige : male, female, other
        """
        if not gender:
            return "other"

        gender_lower = gender.lower().strip()

        # Mapping des valeurs françaises éventuellement présentes dans les données
        gender_map = {
            "homme": "male",
            "femme": "female",
            "institution": "other",
            "autre": "other",
            # Valeurs anglaises déjà prises en charge
            "male": "male",
            "female": "female",
            "other": "other",
        }

        return gender_map.get(gender_lower, "other")

    def _save_reddit_json(self, profiles: List[OasisAgentProfile], file_path: str):
        """
        Sauvegarde les Profile Reddit au format JSON

        Utilise un format cohérent avec to_reddit_format() pour garantir une lecture correcte par OASIS.
        Doit impérativement contenir le champ user_id, élément clé pour le matching de
        OASIS agent_graph.get_agent() !

        Champs requis :
        - user_id : ID utilisateur (entier, utilisé pour faire correspondre poster_agent_id dans initial_posts)
        - username : nom d'utilisateur
        - name : nom affiché
        - bio : biographie
        - persona : persona détaillée
        - age : âge (entier)
        - gender : "male", "female", ou "other"
        - mbti : type MBTI
        - country : pays
        """
        data = []
        for idx, profile in enumerate(profiles):
            # Utilise un format cohérent avec to_reddit_format()
            item = {
                "user_id": profile.user_id if profile.user_id is not None else idx,  # Essentiel : le champ user_id doit être présent
                "username": profile.user_name,
                "name": profile.name,
                "bio": profile.bio[:150] if profile.bio else f"{profile.name}",
                "persona": profile.persona or f"{profile.name} is a participant in social discussions.",
                "karma": profile.karma if profile.karma else 1000,
                "created_at": profile.created_at,
                # Champs requis par OASIS - s'assurer que tous ont une valeur par défaut
                "age": profile.age if profile.age else 30,
                "gender": self._normalize_gender(profile.gender),
                "mbti": profile.mbti if profile.mbti else "ISTJ",
                "country": profile.country if profile.country else "China",
            }

            # Champs optionnels
            if profile.profession:
                item["profession"] = profile.profession
            if profile.interested_topics:
                item["interested_topics"] = profile.interested_topics

            data.append(item)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"{len(profiles)} Profile Reddit sauvegardés dans {file_path} (format JSON, champ user_id inclus)")

    # Conserve l'ancien nom de méthode comme alias, pour la rétrocompatibilité
    def save_profiles_to_json(
        self,
        profiles: List[OasisAgentProfile],
        file_path: str,
        platform: str = "reddit"
    ):
        """[Obsolète] Utiliser la méthode save_profiles()"""
        logger.warning("save_profiles_to_json est obsolète, veuillez utiliser la méthode save_profiles")
        self.save_profiles(profiles, file_path, platform)

