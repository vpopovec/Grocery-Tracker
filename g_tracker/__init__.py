import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login = LoginManager()
login.login_view = 'auth.login'


def _ensure_sqlite_receipt_columns(app):
    """Keep SQLite schema in sync when the app runs without importing main/sqlite_db.Database."""
    try:
        from sqlalchemy.engine.url import make_url
        u = make_url(app.config['SQLALCHEMY_DATABASE_URI'])
    except Exception:
        return
    if u.drivername != 'sqlite' or not u.database:
        return
    import sqlite3
    from sqlite_db import ensure_receipt_llm_elapsed_column

    conn = sqlite3.connect(u.database)
    try:
        ensure_receipt_llm_elapsed_column(conn)
    finally:
        conn.close()


def create_app(config_class=Config):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)
    login.init_app(app)

    @app.context_processor
    def inject_dev_password_reset():
        return {
            'dev_password_reset_enabled': bool(
                app.config.get('ENABLE_DEV_PASSWORD_RESET')),
        }

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

    _ensure_sqlite_receipt_columns(app)

    return app


from g_tracker import models
