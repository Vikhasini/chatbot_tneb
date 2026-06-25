from flask import Blueprint
notifications = Blueprint('notifications', __name__)
from app.blueprints.notifications import routes
