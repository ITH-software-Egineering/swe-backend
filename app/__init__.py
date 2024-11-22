import os
from datetime import timedelta

from flask import Flask
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager

def create_app(testing=False):
    app = Flask(__name__)
    load_dotenv()
    os.environ["TESTING"] = str(testing)

    app.config.update(
        TESTING=testing,
        SECRET_KEY=os.getenv("SECRET_KEY"),
        JWT_ACCESS_TOKEN_EXPIRES=timedelta(days=7)
    )
    jwt = JWTManager(app)

    from app.blueprints import register_blueprints
    from app.models.user import Admin, Student
    
    @jwt.user_lookup_loader
    def user_loader_callback(_jwt_header, jwt_data):
        identity = jwt_data["sub"]
        if identity['role'] == 'admin':
            return Admin.search(id=identity['id'])
        elif identity['role'] == 'student':
            return Student.search(id=identity['id'])
        return None

    register_blueprints(app)
    return app