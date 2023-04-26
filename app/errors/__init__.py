from flask import Blueprint

# The Blueprint class takes the name of the blueprint, the name of the base
# module (typically set to __name__), and optional arguments.
bp = Blueprint('errors', __name__)

# register handlers in this blueprint
from app.errors import handlers
