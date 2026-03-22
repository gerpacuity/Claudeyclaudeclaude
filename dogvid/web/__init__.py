"""Flask web application for DogVid."""

import os
import secrets
from pathlib import Path

from flask import Flask
from flask_login import LoginManager

from .models import db, User


def create_app():
    app = Flask(__name__)

    # Config
    app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
    db_path = os.environ.get("DATABASE_URL", f"sqlite:///{Path.home() / '.dogvid' / 'dogvid.db'}")
    app.config["SQLALCHEMY_DATABASE_URI"] = db_path
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Google OAuth config
    app.config["GOOGLE_CLIENT_ID"] = os.environ.get("GOOGLE_CLIENT_ID", "")
    app.config["GOOGLE_CLIENT_SECRET"] = os.environ.get("GOOGLE_CLIENT_SECRET", "")

    # Media storage
    media_dir = os.environ.get("DOGVID_MEDIA_DIR", str(Path.home() / ".dogvid" / "media"))
    app.config["MEDIA_DIR"] = media_dir
    os.makedirs(os.path.join(media_dir, "elements", "scenes"), exist_ok=True)
    os.makedirs(os.path.join(media_dir, "elements", "audio"), exist_ok=True)
    os.makedirs(os.path.join(media_dir, "compositions"), exist_ok=True)
    os.makedirs(os.path.join(media_dir, "thumbnails"), exist_ok=True)

    # Ensure DB directory exists
    if db_path.startswith("sqlite:///"):
        os.makedirs(os.path.dirname(db_path.replace("sqlite:///", "")), exist_ok=True)

    # Init extensions
    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from .auth import auth_bp
    from .views import views_bp
    from .elements import elements_bp
    from .compositions import compositions_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(views_bp)
    app.register_blueprint(elements_bp, url_prefix="/elements")
    app.register_blueprint(compositions_bp, url_prefix="/compositions")

    # Create tables
    with app.app_context():
        db.create_all()

    return app
