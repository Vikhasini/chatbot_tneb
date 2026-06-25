from flask import Blueprint

chatbot = Blueprint('chatbot', __name__)

from app.blueprints.chatbot import routes
