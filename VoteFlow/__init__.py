from flask import Flask
from flask_sqlalchemy import SQLAlchemy


# from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from VoteFlow.config import Config

# Initialize Modules
db = SQLAlchemy()
# bcrypt = Bcrypt()

# Login Manager for the School
login_manager = LoginManager()
login_manager.login_view = "auth.auth_home"
login_manager.login_message_category = "info"


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    # bcrypt.init_app(app)
    login_manager.init_app(app)
    from VoteFlow.main.routes import main
    from VoteFlow.auth.routes import auth
    from VoteFlow.polls.routes import polls
    from VoteFlow.election.routes import election

    app.register_blueprint(main, url_prefix="/")
    app.register_blueprint(auth, url_prefix="/auth")
    app.register_blueprint(polls, url_prefix="/polls")
    app.register_blueprint(election, url_prefix="/election/<school_id>/<poll_id>")

    from .models import (
        School,
        Student,
        CandidateResult,
        Candidate,
        FlaggedStudent,
        Poll,
    )

    with app.app_context():
        db.create_all()

    return app
