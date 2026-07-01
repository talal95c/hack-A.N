"""
API路由模块
"""

from flask import Blueprint

graph_bp = Blueprint('graph', __name__)
simulation_bp = Blueprint('simulation', __name__)
report_bp = Blueprint('report', __name__)

# MiroPolis (CLAUDE.md §6) : nouveaux blueprints pour la comparaison de lois, le moteur temporel,
# le backtesting, le cycle de vie des scénarios (publication) et l'authentification.
backtesting_bp = Blueprint('backtesting', __name__)
temporal_bp = Blueprint('temporal', __name__)
comparison_bp = Blueprint('comparison', __name__)
scenarios_bp = Blueprint('scenarios', __name__)
auth_bp = Blueprint('auth', __name__)

from . import graph  # noqa: E402, F401
from . import simulation  # noqa: E402, F401
from . import report  # noqa: E402, F401
from . import backtesting  # noqa: E402, F401
from . import temporal  # noqa: E402, F401
from . import comparison  # noqa: E402, F401
from . import scenarios  # noqa: E402, F401
from . import auth  # noqa: E402, F401

