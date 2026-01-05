# Grocery Tracker - Repository Analysis & Improvement Suggestions

## Executive Summary

This is a Flask-based web application for tracking grocery receipts using OCR technology. The project has a solid foundation but needs improvements in security, code quality, documentation, and project structure.

---

## 🔴 Critical Security Issues

### 1. **Hardcoded Secret Key**
**Location:** `config.py:6`
```python
SECRET_KEY = 'dev'
```
**Issue:** Using a hardcoded development secret key in production is a major security risk.
**Fix:** 
- Use environment variables: `SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(32)`
- Create `.env.example` file
- Add `.env` to `.gitignore`

### 2. **Missing Authorization Checks**
**Location:** `g_tracker/item_table.py:159`
```python
# TODO: Only allow user to see his own photos
```
**Issue:** Users can potentially access other users' receipt photos by manipulating URLs.
**Fix:** Add user ownership verification:
```python
scan = db.session.execute(
    select(Scan).where(Scan.scan_id == scan_id, Scan.person_id == current_user.get_id())
).first()
if not scan:
    abort(403)
```

### 3. **File Upload Security**
**Location:** `g_tracker/receipts.py:60-102`
**Issues:**
- No file size limits
- No MIME type validation (only extension check)
- Files saved with predictable UUID names (though UUID helps)
**Fix:**
- Add `MAX_CONTENT_LENGTH` to config
- Validate file content, not just extension
- Consider storing files outside web root or using object storage

### 4. **SQL Injection Risk (Low Priority)**
**Location:** `sqlite_db.py` - Using parameterized queries correctly, but some raw SQL exists
**Status:** Mostly safe due to parameterized queries, but review all SQL statements

---

## 🟡 Code Quality Issues

### 1. **Missing Dependency Management**
**Issue:** No `requirements.txt` or `setup.py` file found
**Fix:** Create `requirements.txt` with all dependencies:
```
Flask>=2.3.0
Flask-SQLAlchemy>=3.0.0
Flask-Login>=0.6.0
Flask-WTF>=1.1.0
WTForms>=3.0.0
easyocr>=1.7.0
opencv-python>=4.8.0
Pillow>=10.0.0
scikit-image>=0.21.0
deskew>=0.10.0
pandas>=2.0.0
altair>=5.0.0
unidecode>=1.3.0
pytz>=2023.3
pytest>=7.4.0
```

### 2. **Wildcard Imports**
**Locations:** 
- `main.py:6` - `from helpers import *`
- `g_tracker/receipts.py:3` - `from g_tracker.helpers import *`
- `g_tracker/insight.py:5` - `from g_tracker.helpers import *`
**Issue:** Makes code harder to understand and maintain
**Fix:** Use explicit imports: `from helpers import get_shop, get_shopping_date, ...`

### 3. **Inconsistent Error Handling**
**Location:** Multiple files
**Issue:** Some functions use bare `except:` clauses, others don't handle errors at all
**Fix:** 
- Use specific exception types
- Add proper logging
- Return meaningful error messages to users

### 4. **Code Duplication**
**Issue:** Database logic exists in both `sqlite_db.py` (old) and SQLAlchemy models (new)
**Fix:** Remove deprecated database code or clearly mark it as legacy

### 5. **Missing Type Hints**
**Issue:** Most functions lack type hints, making code harder to understand
**Fix:** Add type hints throughout, especially in public APIs

### 6. **Deprecated/Unused Files**
**Files:**
- `g_tracker/deprecated_db.py`
- `sqlite_db.py` (if not used)
- `person.py` (if not used)
- `sample_db.py`
- `test_db.py`
**Fix:** Remove or clearly document which files are deprecated

---

## 🟢 Project Structure Improvements

### 1. **Repository Cleanup**
**Issues:**
- Database files (`receipts.db`, `instance/db.sqlite`) should not be in repo
- Session files (`flask_session/`) should not be in repo
- `__pycache__/` directories should be ignored
- Receipt images should not be in repo (426 files!)

**Fix:** Update `.gitignore`:
```
# Database
*.db
*.sqlite
*.sqlite3
instance/

# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
ENV/

# Flask
flask_session/

# Receipts (user data)
receipts/*.jpg
receipts/*.jpeg
receipts/*.png
receipts/*.gif
receipts/*.json
!receipts/cache/.gitkeep

# IDE
.idea/
.vscode/
*.swp
*.swo

# Environment
.env
.env.local

# OS
.DS_Store
Thumbs.db
```

### 2. **Configuration Management**
**Issue:** Hardcoded paths and configuration values
**Fix:**
- Use environment variables for all configuration
- Create `config.py` with different config classes (Development, Production, Testing)
- Add `.env.example` template

### 3. **Project Organization**
**Suggestion:** Consider this structure:
```
grocery_tracker/
├── app/                    # Rename g_tracker to app
│   ├── __init__.py
│   ├── models.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── receipts.py
│   │   ├── items.py
│   │   └── insights.py
│   ├── services/
│   │   ├── ocr_service.py
│   │   └── receipt_processor.py
│   ├── utils/
│   │   └── helpers.py
│   ├── static/
│   └── templates/
├── tests/
├── migrations/             # Flask-Migrate
├── instance/               # Instance-specific files
├── config.py
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 📝 Documentation Issues

### 1. **Incomplete README**
**Current:** Basic description, missing installation/usage instructions
**Fix:** Add:
- Installation instructions
- Setup guide (database, environment variables)
- Usage examples
- API documentation
- Development setup
- Contributing guidelines

### 2. **Missing Docstrings**
**Issue:** Most functions lack docstrings
**Fix:** Add docstrings following Google or NumPy style:
```python
def process_receipt_from_fpath(f_name: str) -> Receipt:
    """Process a receipt image file and extract grocery items.
    
    Args:
        f_name: Path to the receipt image file
        
    Returns:
        Receipt object with extracted items and metadata
        
    Raises:
        FileNotFoundError: If the receipt file doesn't exist
        OCRException: If OCR processing fails
    """
```

### 3. **Missing API Documentation**
**Issue:** No documentation for Flask routes
**Fix:** Consider using Flask-RESTX or add OpenAPI/Swagger documentation

---

## 🧪 Testing Improvements

### 1. **Limited Test Coverage**
**Current:** Only `test_receipts.py` with OCR tests
**Missing:**
- Unit tests for helpers
- Integration tests for routes
- Database tests
- Authentication tests

### 2. **Test Dependencies**
**Issue:** Tests depend on specific receipt files that may not exist
**Fix:** 
- Use fixtures or mock OCR results
- Add test data directory
- Use pytest fixtures properly

### 3. **No CI/CD**
**Fix:** Add GitHub Actions or similar for:
- Running tests
- Code quality checks (linting, formatting)
- Security scanning

---

## 🔧 Configuration & Environment

### 1. **Environment Variables**
**Missing:** No `.env` file or environment variable management
**Fix:**
- Use `python-dotenv` package
- Create `.env.example`:
```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///receipts.db
UPLOAD_FOLDER=./receipts
MAX_UPLOAD_SIZE=10485760
DEBUG=False
```

### 2. **Logging**
**Issue:** Using `print()` statements instead of proper logging
**Fix:** 
- Set up Python logging
- Use different log levels
- Log to file in production

### 3. **Database Migrations**
**Issue:** No migration system
**Fix:** Use Flask-Migrate for database version control

---

## 🚀 Performance & Best Practices

### 1. **Database Queries**
**Issue:** Some N+1 query problems possible
**Fix:** Use eager loading where appropriate:
```python
Receipt.query.options(db.joinedload(Receipt.items)).all()
```

### 2. **Image Processing**
**Issue:** Images processed synchronously, blocking requests
**Fix:** Consider using Celery or background tasks for OCR processing

### 3. **Caching**
**Issue:** OCR results cached, but could improve caching strategy
**Fix:** 
- Use Redis or Memcached for distributed caching
- Cache user-specific queries

### 4. **Code Formatting**
**Fix:** Add:
- `black` for code formatting
- `flake8` or `pylint` for linting
- `mypy` for type checking
- Pre-commit hooks

---

## 📋 Specific Code Issues

### 1. **Typo in receipts.py:45**
```python
nparr = np.frombuffer(data, np.uint8)  # Should be frombuffer
```

### 2. **Validation Error Return**
**Location:** `g_tracker/forms.py:26`
```python
return ValidationError('Please use a different username')
```
**Issue:** Should `raise` not `return`

### 3. **Bare Except Clause**
**Location:** `g_tracker/item_table.py:82`
```python
except:
    receipt_total = 0
```
**Fix:** Use specific exception type

### 4. **Unused Code**
- Commented code in multiple files
- Unused imports
- Dead code paths

---

## 🎯 Priority Recommendations

### High Priority (Security & Stability)
1. ✅ Fix hardcoded SECRET_KEY
2. ✅ Add authorization checks for file access
3. ✅ Create requirements.txt
4. ✅ Update .gitignore
5. ✅ Fix typo in receipts.py

### Medium Priority (Code Quality)
1. Replace wildcard imports
2. Add proper error handling
3. Remove deprecated files
4. Add type hints
5. Fix validation error in forms.py

### Low Priority (Nice to Have)
1. Restructure project
2. Add comprehensive tests
3. Improve documentation
4. Add CI/CD
5. Implement proper logging

---

## 📚 Additional Suggestions

1. **Add Rate Limiting:** Use Flask-Limiter to prevent abuse
2. **Add CSRF Protection:** Ensure all forms have CSRF tokens (Flask-WTF should handle this)
3. **Add Input Validation:** Validate all user inputs more thoroughly
4. **Add Monitoring:** Consider adding error tracking (Sentry, etc.)
5. **Add Backup Strategy:** For user data and database
6. **Consider Docker:** For easier deployment and development
7. **Add Health Check Endpoint:** For monitoring
8. **Consider API Versioning:** If planning to expand API

---

## Summary

The project shows good understanding of Flask and OCR integration, but needs attention to:
- **Security** (critical)
- **Code organization** (important)
- **Documentation** (important)
- **Testing** (important)

With these improvements, the project will be more maintainable, secure, and production-ready.

