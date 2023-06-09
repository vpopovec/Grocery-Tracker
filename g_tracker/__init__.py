import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from config import Config

db = SQLAlchemy()


def create_app(config_class=Config):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    from . import welcome, receipts, item_table
    app.register_blueprint(receipts.bp)
    app.register_blueprint(welcome.bp)
    app.register_blueprint(item_table.bp)

    return app


from g_tracker import models
