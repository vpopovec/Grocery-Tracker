import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login = LoginManager()
login.login_view = 'auth.login'


def create_app(config_class=Config):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)
    login.init_app(app)

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    from . import welcome, receipts, item_table, auth_routes, insight
    app.register_blueprint(receipts.bp)
    app.register_blueprint(welcome.bp)
    app.register_blueprint(item_table.bp)
    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(insight.bp)

    return app


from g_tracker import models
