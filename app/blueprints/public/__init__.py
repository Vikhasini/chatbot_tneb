from flask import Blueprint
public = Blueprint('public', __name__)
from app.blueprints.public import routes
