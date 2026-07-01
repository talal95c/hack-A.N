"""
API路由模块
"""

from flask import Blueprint

graph_bp = Blueprint('graph', __name__)
simulation_bp = Blueprint('simulation', __name__)
report_bp = Blueprint('report', __name__)
# MiroPolis (CLAUDE.md §6) : agent de scénario tendanciel, en plus du ReportAgent habituel.
scenario_bp = Blueprint('scenario', __name__)

from . import graph  # noqa: E402, F401
from . import simulation  # noqa: E402, F401
from . import report  # noqa: E402, F401
from . import scenario  # noqa: E402, F401
