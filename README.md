## Project setup

This repo is a practice following mega-tutorial:
[Flask Mega-Tutorial](https://blog.miguelgrinberg.com/post/the-flask-mega-tutorial-part-i-hello-world)

Major implementation practice:

- .env for env vars with python-dotenv lib
  - config.py loads env vars
- sqlalchemy orm and database migration
- web form (and custom validation) with flask-wtf extension
- view templates with bootstrap extension
- user authentication with flask-login extension
- client side local timezone conversion with flask-moment (moment.js) extension
- modularize with blueprints (an application subsets) in separate python packages
- full-text search for posts: elasticsearch + sqlalchemy event handlers
- docker container deployment and docker-compose multi-container orchestration

## development environment

```shell
pyenv shell 3.9
python -m venv venv
source venv/bin/activate
pip install -U pip
pip install -r requirements.txt
```

Export env vars, these exports are not needed if defined in a local .env file.

```shell
export FLASK_APP=microblog.py
export FLASK_ENV=development
```

For first time running, make sure to run database migration to initialize 
database schema and tables:

```shell
flask db upgrade
```

Run flask development stack or shell

```sh
flask run
```

Run flask in interactive shell

```shell
flask shell

# in shell, we can load data with model classes
>>> u = User(username='testuser', email='tuser@example.com')
>>> u.set_password('changeme')
>>> db.session.add(u)
>>> db.session.commit()
# check users in db
>>> User.query.all()
```

## mysql

For deployment, use mysql docker container to replace dev-mode sqlite. See [deployment](./README_deployment.md)

In `Dockerfile`, after pip install requirements.txt, `pymysql` is installed for sqlalchemy to connect to mysql.

In `boot.sh file`, `flask db upgrade` is run to apply db migrations before application bootstrap.

## elasticsearch

Docker container deployment see: [deployment](./README_deployment.md).

Python client sdk (https://elasticsearch-py.readthedocs.io/en/v8.0.0/) is used to connect, index, and search posts.
See [app/**init**.py](./app/__init__.py) for client setup. See [Post model](./app/models.py) for `SearchableMixin`
implementation.

To reindex entire posts index in running docker container:

```sh
docker exec -it microblog /bin/bash
# invoke a flask shell
venv/bin/flask shell
# run Post model reindex() method provided by SearchableMixin
>>>Post.reindex()
```

## redis for task queues

Use redis docker container with offical redis image. See [deployment](./README_deployment.md)

There are three major components of rq task queue setup:

- a task queue
- a rq worker that listens to the task queue
- a task function using `rq.get_current_job()` to get assigned job

Once a job is enqueued with a target task function, the worker will schedule the execution of the job with the target
task function.

A simple example below:

Start a rq worker (python process) against a redis queue 'foo':

```shell
rq worker --url redis://@192.168.64.2:6379 foo
11:17:41 Worker rq:worker:5c90d3ca71ec4645b743ba3cd741e69d: started, version 1.10.1
11:17:41 Subscribing to channel rq:pubsub:5c90d3ca71ec4645b743ba3cd741e69d
11:17:41 *** Listening on foo...
11:17:41 Cleaning registries for queue: foo
```

In python shell, enqueue with a defined task function `example()`:

```python
from redis import Redis
from rq import Queue

conn = Redis('192.168.64.2', 6379)
q1 = Queue('foo', connection=conn)
print(q1.key)  # 'rq:queue:foo'
# enqueue a job with a task function named `example()` in `app/tasks.py`
job = q1.enqueue('app.tasks.example')
print(job.get_id())  # something like '9d376f50-222e-43ad-ab54-283e244b30d4'
print(job.meta)  # a python dictionary
print(job.is_finished)  # False -> True when job is done
```

## application docker image and containers

Build docker image. See: [deployment](./README_deployment.md). This image is used for both flask web stack and RQ
background job runner.

Run container as microblog webstack:

- `.env` file is not copied over
  - `FLASK_APP` is set in Dockerfile
  - `FLASK_ENV` is not set, so default to production
- `ENABLE_ELASTICSEARCH` is set to `False` in `config.py`

Run container as redis queue worker process for background jobs:

- docker uses the same image but with an entry point (cmd) override
- override cli has strict order:
  - `--entrypoint` is the executable name
  - but arguments (if any) must be given after the image and tag, at the end of the command line
- add `-d` option to run in detached mode
- entrypoint is RQ workder command, this container does not run db migration, it is connecting to the database managed
  by microblog web stack

## Email

With proper email configurations set by environment variables, a manual email sending can be tested in a flask shell:

```shell
flask shell

from flask_mail import Message
from app import mail
msg = Message('test msg', sender='no-reply@microblog.com', recipients=['bin.le.code@gmail.com'])
msg.body = 'test email body'
msg.html = '<h1>Html body</h1>'
mail.send(msg)
```

## TODOs

- add elasticsearch into docker-compose configuration
- flask-mail config and send-email example
