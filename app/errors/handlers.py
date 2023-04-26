# To test error pages, exception needs to be caught by decorated
# functions below, the `FLASK_ENV` needs to be set to 'production',
# otherwise the built-in debug error stacktrace will take over
# the error page rendering.

from flask import render_template
from app import db
from app.errors import bp


# A difference when writing error handlers inside a blueprint is that if the
# errorhandler decorator is used, the handler will be invoked only for errors
# that originate in the routes defined by the blueprint.
# To install application-wide error handlers, the `app_errorhandler` decorator
# must be used instead of `errorhandler`.

@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404


@bp.app_errorhandler(500)
def internal_error(error):
    # make sure to clear possibly dirty db session
    db.session.rollback()
    return render_template('errors/500.html', error=error), 500
