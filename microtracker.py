from g_tracker import create_app, db
from g_tracker.models import Item, PasswordResetToken, Person, Receipt

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {
        'db': db,
        'Receipt': Receipt,
        'Person': Person,
        'Item': Item,
        'PasswordResetToken': PasswordResetToken,
    }