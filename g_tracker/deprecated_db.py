import sqlite3
from flask_sqlalchemy import SQLAlchemy
import click
from flask import current_app, g


def get_db():

    # if 'db' not in g:
    #     # g.db = sqlite3.connect(
    #     #     current_app.config['DATABASE'],
    #     #     detect_types=sqlite3.PARSE_DECLTYPES
    #     # )
    #     # g.db.row_factory = sqlite3.Row
    #     g.db = SQLAlchemy(current_app)

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()


def init_db():
    db = get_db()
    with current_app.app_context():
        db.create_all()
    # with current_app.open_resource('../schema.sql') as f:
    #     db.executescript(f.read().decode('utf8'))


# Run flask --app reuploader init-db to initialize DB
@click.command('init-db')
def init_db_command():
    """ Clear the existing data and create new tables """
    init_db()
    click.echo('Initialized the database.')


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

    # if 'db' not in g:
    #     g.db = SQLAlchemy(app)
