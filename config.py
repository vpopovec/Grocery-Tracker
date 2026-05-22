import os
base_dir = os.path.abspath(os.path.dirname(__file__))


def _env_bool(name: str, default: str = '') -> bool:
    return os.environ.get(name, default).lower() in ('1', 'true', 'yes')


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == '':
        return default
    return int(raw)


class Config(object):
    GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
    GROQ_API_KEY = os.environ.get('GROQ_API_KEY')
    OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-change-in-production'
    ENABLE_DEV_PASSWORD_RESET = _env_bool('ENABLE_DEV_PASSWORD_RESET')

    # Public deployment: registration off unless explicitly enabled.
    REGISTRATION_ENABLED = _env_bool('REGISTRATION_ENABLED')
    REGISTRATION_INVITE_CODE = os.environ.get('REGISTRATION_INVITE_CODE', '').strip()

    # OpenRouter receipt scans (/scan).
    LLM_SCANS_PER_USER_PER_DAY = _env_int('LLM_SCANS_PER_USER_PER_DAY', 10)
    LLM_SCANS_GLOBAL_PER_DAY = _env_int('LLM_SCANS_GLOBAL_PER_DAY', 50)
    SCAN_RATE_LIMIT = os.environ.get('SCAN_RATE_LIMIT', '5 per minute')

    # Groq insight chat (/ask-ai).
    INSIGHT_AI_PER_USER_PER_DAY = _env_int('INSIGHT_AI_PER_USER_PER_DAY', 20)
    INSIGHT_AI_GLOBAL_PER_DAY = _env_int('INSIGHT_AI_GLOBAL_PER_DAY', 100)
    ASK_AI_RATE_LIMIT = os.environ.get('ASK_AI_RATE_LIMIT', '10 per minute')

    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER') or os.path.join(base_dir, 'receipts')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 10 * 1024 * 1024))  # 10MB default
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', '').replace(
        'postgres://', 'postgresql://') or \
        'sqlite:///' + os.path.join(base_dir, 'receipts.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = _env_bool('SESSION_COOKIE_SECURE')
