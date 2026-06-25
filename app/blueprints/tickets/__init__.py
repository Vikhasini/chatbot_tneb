from flask import Blueprint

tickets = Blueprint('tickets', __name__)

from app.blueprints.tickets import routes
