from g_tracker import create_app, db
from g_tracker.models import Receipt, Person, Item

app = create_app()


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Receipt': Receipt, 'Person': Person, 'Item': Item}