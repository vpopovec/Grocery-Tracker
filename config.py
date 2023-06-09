import os
base_dir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    SECRET_KEY = 'dev'
    UPLOAD_FOLDER = os.path.join(base_dir, 'receipts')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '').replace(
        'postgres://', 'postgresql://') or \
        'sqlite:///' + os.path.join(base_dir, 'receipts.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
