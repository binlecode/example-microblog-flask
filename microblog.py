from app import create_app, db
from app.models import User, Post, Task


app = create_app()


# shell_context_processor decorator registers the target function as a
# shell context function, which is called when `flask shell` command runs
# This also requires env var FLASK_APP is properly set first.
@app.shell_context_processor
def make_shell_context():
    # this adds db, User, and Post instances to the flask shell session
    return {'db': db, 'User': User, 'Post': Post, 'Task': Task}
