from flask import Flask
from .extensions import db

def create_app(test_config=None):
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev_secret_key_123' # Change for production
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///parcel_system.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    with app.app_context():
        # Import models here to ensure they are registered with SQLAlchemy
        from . import models
        db.create_all()
        
        # Seed data logic removed to prevent conflicts. Use reinit_users.py instead.

    from .routes import main as main_blueprint
    app.register_blueprint(main_blueprint)

    return app
