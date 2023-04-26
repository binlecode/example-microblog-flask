from datetime import datetime
from hashlib import md5
from flask_login import UserMixin
from flask import current_app
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
from app import login

# Elasticsearch #
#
# define a searchable model mixin for elasticsearch functions driven
# by sqlalchemy events
from app.search import query_index, add_to_index, remove_from_index


# implementation design:
# - all indexes will be named with the name Flask-SQLAlchemy assigned to the
#   relational table
# - sqlalchemy take ES returned ids list to query db to get entity objects
# - in sql query, ensure objects are ordered with same ordering of ES returned
#   ids list, because this ordering reflects ES match scores
# - the elasticsearch specific search impl is external and loaded as a module,
#   so that searching logic and data layer logic are decoupled
class SearchableMixin(object):
    @classmethod
    def search(cls, expression, page, per_page):
        ids, total = query_index(cls.__tablename__, expression,
                                 page, per_page)
        if total == 0:
            return cls.query.filter_by(id=0), 0

        # query database by ids list, with case-when sorting
        when = []
        for i in range(len(ids)):
            when.append((ids[i], i))
        return cls.query.filter(cls.id.in_(ids)).order_by(
            db.case(when, value=cls.id)), total

    # register all session transactional entities into session hash so that
    # after session commit the Elasticsearch search module can update index
    # accordingly,
    # this is because after session commit, the objects that are marked
    # 'new', 'dirty', and 'deleted' will all be gone
    @classmethod
    def before_commit(cls, session):
        session._changes = {
            'add': list(session.new),
            'update': list(session.dirty),
            'delete': list(session.deleted)
        }

    # after_commit event is only triggered after a session commit is successful,
    # this means that ES indexing only happens after a successful session
    # commit.
    @classmethod
    def after_commit(cls, session):
        for obj in session._changes['add']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        # use same function for update
        for obj in session._changes['update']:
            if isinstance(obj, SearchableMixin):
                add_to_index(obj.__tablename__, obj)
        for obj in session._changes['delete']:
            if isinstance(obj, SearchableMixin):
                remove_from_index(obj.__tablename__, obj)
        # clear session _changes hash
        session._changes = None

    # a helper method to refresh an index for all the data rows of an entity
    @classmethod
    def reindex(cls):
        # todo: this loads all the rows from table, could be a performance issue
        for obj in cls.query:
            add_to_index(cls.__tablename__, obj)


# register sqlalchemy event handlers
db.event.listen(db.session, 'before_commit', SearchableMixin.before_commit)
db.event.listen(db.session, 'after_commit', SearchableMixin.after_commit)

# Redis task queue #
#
import redis
import rq


# Task model has many-to-one FK to User model
#
class Task(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128), index=True)
    description = db.Column(db.String(128))
    complete = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def get_rq_job(self):
        try:
            rq_job = rq.job.Job.fetch(self.id, current_app.redis)
        except (redis.exceptions.RedisError, rq.exceptions.NoSuchJobError):
            return None
        return rq_job

    def get_progress(self):
        job = self.get_rq_job()
        return job.meta.get('progress', 0) if job is not None else 100


# flask-login extension provides UserMixin that includes four methods:
# - is_authenticated
# - is_active
# - is_anonymous
# - get_id
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(120), index=True, unique=True)
    password_hash = db.Column(db.String(128))
    posts = db.relationship('Post', backref='author', lazy='dynamic')
    # these two are added later so will need new migration scripts
    # after adding these two column definition,
    # run: flask db migrate -dm "new fields in user model", and flask
    # will detect this change and generate migration script accordingly
    about_me = db.Column(db.String(140))
    last_seen = db.Column(db.DateTime, default=datetime.utcnow())
    # has many tasks
    tasks = db.relationship('Task', backref='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # generate avatar icon url
    def avatar(self, size=64):
        digest = md5(self.email.lower().encode('utf-8')).hexdigest()
        return f"https://www.gravatar.com/avatar/{digest}?d=identicon&s={size}"

    def __repr__(self):
        return '<User {}>'.format(self.username)

    # submit a job to rq queue for a given task
    # name - task function name
    def launch_task(self, name, description, *args, **kwargs):
        rq_job = current_app.task_queue.enqueue('app.tasks.' + name,
                                                self.id, *args, **kwargs)
        task = Task(id=rq_job.get_id(), name=name,
                    description=description, user=self)
        # task entity is added to session, but NOT committed, this means
        # we let sqlalchemy to decide when to flush and commit the session
        db.session.add(task)
        return task

    def get_tasks_in_progress(self):
        return Task.query.filter_by(user=self, complete=False).all()

    # get first in-progress task with given task name
    # this is used to check if a task is running to prevent double-submission
    def get_task_in_progress(self, name):
        return Task.query.filter_by(user=self, name=name, complete=False).first()


# flask-login extension does not know how to fetch user data
# flask-login delegates user data access to this function
@login.user_loader
def load_user(id):
    return User.query.get(int(id))


class Post(SearchableMixin, db.Model):
    # define a class attribute to include all ES indexed fields
    __searchable__ = ['body']

    id = db.Column(db.Integer, primary_key=True)
    body = db.Column(db.String(140))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    def __repr__(self):
        return '<Post {}>'.format(self.body)
