import os
base_dir = os.path.abspath(os.path.dirname(__file__))


class Config(object):
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(base_dir, 'receipts')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))  # 10MB default
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '').replace(
        'postgres://', 'postgresql://') or \
        'sqlite:///' + os.path.join(base_dir, 'receipts.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
