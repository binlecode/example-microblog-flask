import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_mail import Mail
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from config import Config
from elasticsearch import Elasticsearch
from redis import Redis
import rq

# instantiate extensions as global objects, and then bind them to the
# application in create_app(config) factory function
#
db = SQLAlchemy()
migrate = Migrate()
# initialize flask-login extension
login = LoginManager()
# set login page for login-required access when authentication fails
# login-required routing can use @login_required decorator
login.login_view = 'auth.login'
# mail used for password reset and other notification workflows
mail = Mail()
# initialize bootstrap extension, with this, a bootstrap/base.html
# template becomes available and can be referenced from application
# templates with `extends` clause.
bootstrap = Bootstrap()
# initialize flask-moment to include moment.js
# now moment becomes available in views
# see script block in templates/base.html file
moment = Moment()


# application factory function, to be called by top-level scripts, such as
# `microblog.py`
# the application factory pattern prevents the app from being exposed in the
# global scope.
# for example, if we need a testing script to load an instance of the app, we
# can create a top-level `tests.py` and call this factory function in it
def create_app(config_class=Config):
    # initialize Flask app with the package name (via __name__ of __init__ file)
    # this is a common practice if Flask app is defined in __init__ file
    app = Flask(__name__)

    # config Flask app with Config object, all settings in Config object are
    # loaded to and accessible in app.config as a dictionary
    app.config.from_object(Config)

    db.init_app(app)
    migrate.init_app(app, db)
    login.init_app(app)
    mail.init_app(app)
    bootstrap.init_app(app)
    moment.init_app(app)

    # register blueprints
    #
    from app.errors import bp as errors_bp
    app.register_blueprint(errors_bp)

    from app.auth import bp as auth_bp
    # url prefix is optional, it is a good practice to namespace all auth urls
    # the `url_for` view helper will auto prefix the given <bp>.<handler-func>.
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.main import bp as main_bp
    app.register_blueprint(main_bp)

    if not app.debug and not app.testing:
        if app.config['MAIL_SERVER']:
            auth = None
            if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
                auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
            secure = None
            if app.config['MAIL_USE_TLS']:
                secure = ()
            mail_handler = SMTPHandler(
                mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
                fromaddr='no-reply@' + app.config['MAIL_SERVER'],
                toaddrs=app.config['ADMINS'],
                subject='Microblog Failure',
                credentials=auth,
                secure=secure
            )
            mail_handler.setLevel(logging.ERROR)
            app.logger.addHandler(mail_handler)

        # logging config
        #
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler('logs/microblog.log', maxBytes=10240,
                                           backupCount=10)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        app.logger.setLevel(logging.INFO)
        app.logger.info('Microblog startup')

    if app.config['ENABLE_ELASTICSEARCH']:
        # add elasticsearch as app attribute
        app.elasticsearch = Elasticsearch(
            [app.config['ELASTICSEARCH_URL']],
            basic_auth=(app.config['ELASTICSEARCH_USER'], app.config['ELASTICSEARCH_PASSWORD']),
            verify_certs=None
        )
        # disable unverified https warning (due to verify_cert=None option):
        import urllib3
        urllib3.disable_warnings()
        app.logger.info('Elasticsearch initialized')
        app.logger.info(f'Elasticsearch client info: {app.elasticsearch.info()}')
    else:
        app.elasticsearch = None

    # setup redis task queue
    # this task queue can be access from anywhere via 'current_app'
    app.redis = Redis.from_url(app.config['REDIS_URL'])
    app.task_queue = rq.Queue('microblog-tasks', connection=app.redis)

    return app


from app import models
