import os

basedir = os.path.abspath(os.path.dirname(__file__))

# in debug (development) mode, `flask run` command will auto load .flaskenv
# and .env files, but production mode doesn't run `flask` command, therefore,
# it is important to load .env settings explicitly
# NOTE: .env is for deployment specific sensitive data, NEVER add it to VCS!
from dotenv import load_dotenv
load_dotenv(os.path.join(basedir, '.env'))


# it is a good practice to define a class to store configuration
# config settings are defined as class variables
class Config(object):
    # SECRET_KEY is need by flask and extensions as cryptographic key, used to
    # generate signature or tokens.
    # For example, flask-wtf extension use this key to protect CSRF attack
    # on web forms.
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'sqlite:///' + os.path.join(basedir, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # print sql in debug mode
    SQLALCHEMY_ECHO = True if os.environ.get('FLASK_ENV') == 'development' else False
    # pagination
    POSTS_PER_PAGE = 3

    ENABLE_ELASTICSEARCH = os.environ.get('ENABLE_ELASTICSEARCH') == 'True' or False
    ELASTICSEARCH_URL = os.environ.get('ELASTICSEARCH_URL') or 'https://localhost:9200'
    ELASTICSEARCH_USER = os.environ.get('ELASTICSEARCH_USER')
    ELASTICSEARCH_PASSWORD = os.environ.get('ELASTICSEARCH_PASSWORD')

    # Redis task queue
    REDIS_URL = os.environ.get('REDIS_URL') or 'redis://'

    # Email server setup
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = os.environ.get('MAIL_PORT')
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') or 1
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
