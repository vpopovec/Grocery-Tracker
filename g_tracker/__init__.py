import os
from g_tracker.helpers import ROOT_DIR
from flask import Flask
from flask_session import Session
UPLOAD_FOLDER = f'{ROOT_DIR}/receipts'


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'grocery_tracker.sqlite'),
        SESSION_PERMANENT=False,
        SESSION_TYPE='filesystem',
        UPLOAD_FOLDER=UPLOAD_FOLDER
    )
    Session(app)

    if test_config is None:
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # a simple page that says hello
    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    from . import db
    db.init_app(app)

    from . import welcome, receipts
    app.register_blueprint(receipts.bp)
    app.register_blueprint(welcome.bp)
    # app.register_blueprint(ads.bp)

    return app
