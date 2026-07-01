"""
配置管理
统一从项目根目录的 .env 文件加载配置
"""

import os
from dotenv import load_dotenv

# 加载项目根目录的 .env 文件
# 路径: MiroFish/.env (相对于 backend/app/config.py)
project_root_env = os.path.join(os.path.dirname(__file__), '../../.env')

if os.path.exists(project_root_env):
    load_dotenv(project_root_env, override=True)
else:
    # 如果根目录没有 .env，尝试加载环境变量（用于生产环境）
    load_dotenv(override=True)


class Config:
    """Flask配置类"""
    
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY', 'mirofish-secret-key')
    DEBUG = os.environ.get('FLASK_DEBUG', 'True').lower() == 'true'
    
    # JSON配置 - 禁用ASCII转义，让中文直接显示（而不是 \uXXXX 格式）
    JSON_AS_ASCII = False
    
    # LLM配置（统一使用OpenAI格式）
    LLM_API_KEY = os.environ.get('LLM_API_KEY')
    LLM_BASE_URL = os.environ.get('LLM_BASE_URL', 'https://api.openai.com/v1')
    LLM_MODEL_NAME = os.environ.get('LLM_MODEL_NAME', 'gpt-4o-mini')
    
    # Zep配置
    ZEP_API_KEY = os.environ.get('ZEP_API_KEY')
    
    # 文件上传配置
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../uploads')
    ALLOWED_EXTENSIONS = {'pdf', 'md', 'txt', 'markdown'}
    
    # 文本处理配置
    DEFAULT_CHUNK_SIZE = 500  # 默认切块大小
    DEFAULT_CHUNK_OVERLAP = 50  # 默认重叠大小
    
    # OASIS模拟配置
    OASIS_DEFAULT_MAX_ROUNDS = int(os.environ.get('OASIS_DEFAULT_MAX_ROUNDS', '10'))
    OASIS_SIMULATION_DATA_DIR = os.path.join(os.path.dirname(__file__), '../uploads/simulations')

    # MiroPolis : interpréteur Python dédié au sous-processus OASIS.
    # ⚠️ Vérifié à l'implémentation : camel-oasis==0.2.5 n'a pas de distribution compatible avec
    # Python 3.12 (le serveur Flask principal peut tourner en 3.12+, mais PAS le sous-processus de
    # simulation OASIS). Solution retenue : un venv Python 3.11 dédié (backend/.venv311), détecté
    # automatiquement s'il existe, sinon repli sur l'interpréteur courant (sys.executable) pour les
    # déploiements qui font tourner tout le backend en Python <3.12.
    _oasis_venv_python = os.path.join(
        os.path.dirname(__file__), '..', '.venv311',
        'Scripts' if os.name == 'nt' else 'bin',
        'python.exe' if os.name == 'nt' else 'python',
    )
    OASIS_PYTHON_EXECUTABLE = os.environ.get(
        'OASIS_PYTHON_EXECUTABLE',
        _oasis_venv_python if os.path.exists(_oasis_venv_python) else None,  # None -> repli sys.executable
    )
    
    # OASIS平台可用动作配置
    OASIS_TWITTER_ACTIONS = [
        'CREATE_POST', 'LIKE_POST', 'REPOST', 'FOLLOW', 'DO_NOTHING', 'QUOTE_POST'
    ]
    OASIS_REDDIT_ACTIONS = [
        'LIKE_POST', 'DISLIKE_POST', 'CREATE_POST', 'CREATE_COMMENT',
        'LIKE_COMMENT', 'DISLIKE_COMMENT', 'SEARCH_POSTS', 'SEARCH_USER',
        'TREND', 'REFRESH', 'DO_NOTHING', 'FOLLOW', 'MUTE'
    ]
    
    # Report Agent配置
    REPORT_AGENT_MAX_TOOL_CALLS = int(os.environ.get('REPORT_AGENT_MAX_TOOL_CALLS', '5'))
    REPORT_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('REPORT_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    REPORT_AGENT_TEMPERATURE = float(os.environ.get('REPORT_AGENT_TEMPERATURE', '0.5'))

    # ============= MiroPolis : sources de données réelles (CLAUDE.md §5) =============
    TRICOTEUSES_GRAPHQL_URL = os.environ.get(
        'TRICOTEUSES_GRAPHQL_URL', 'https://assemblee.tricoteuses.fr/graphql'
    )
    DATAGOUV_API_URL = os.environ.get('DATAGOUV_API_URL', 'https://www.data.gouv.fr/api/1')
    # Composition des groupes parlementaires : source vérifiée fonctionnelle (2026-07) --
    # dataset officiel "Groupes politiques actifs de l'Assemblée nationale" sur data.gouv.fr,
    # ressource CSV mise à jour automatiquement (colonne dateMaj). Remplace l'endpoint GraphQL
    # Tricoteuses dont l'URL publique exacte n'a pas pu être confirmée -- voir tricoteuses_client.py.
    DATAGOUV_GROUPES_DATASET_ID = os.environ.get(
        'DATAGOUV_GROUPES_DATASET_ID', '60ed57a9f0c7c3a1eb29733f'
    )
    # Dossier de cache local pour les données réglementaires (CLAUDE.md §2 : jamais d'appel réseau
    # live à ces sources pendant une démo/présentation).
    TERRITORIAL_CACHE_DIR = os.path.join(os.path.dirname(__file__), '../uploads/territorial_cache')
    HTTP_CLIENT_TIMEOUT_SECONDS = int(os.environ.get('HTTP_CLIENT_TIMEOUT_SECONDS', '10'))

    # ============= Scenario Agent配置（trajectoire tendancielle） =============
    SCENARIO_AGENT_MAX_TOOL_CALLS = int(os.environ.get('SCENARIO_AGENT_MAX_TOOL_CALLS', '5'))
    SCENARIO_AGENT_MAX_REFLECTION_ROUNDS = int(os.environ.get('SCENARIO_AGENT_MAX_REFLECTION_ROUNDS', '2'))
    SCENARIO_AGENT_TEMPERATURE = float(os.environ.get('SCENARIO_AGENT_TEMPERATURE', '0.6'))

    @classmethod
    def validate(cls) -> list[str]:
        """验证必要配置"""
        errors: list[str] = []
        if not cls.LLM_API_KEY:
            errors.append("LLM_API_KEY 未配置")
        if not cls.ZEP_API_KEY:
            errors.append("ZEP_API_KEY 未配置")
        return errors

