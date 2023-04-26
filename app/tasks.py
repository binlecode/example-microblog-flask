import sys
import time
from rq import get_current_job
from app import create_app, db
from app.models import Task, User

# create application instance for this rq worker python process
app = create_app()
# pushing application context makes this newly created app instance the
# 'current_app' to be referred in this python process, therefore making
# extensions also available, such as current_app.config
app.app_context().push()


def export_posts(user_id):
    try:
        app.logger.info(f'export_posts job started for user: {user_id}')
        user = User.query.get(user_id)
        _set_task_progress(0)
        # todo: read user posts from db
        # todo: send email to user when export is done
        for i in range(10):
            app.logger.info(f'... {i}/10')
            time.sleep(1)  # mimic a long-running task
        app.logger.info(f'export_posts job complete for user: {user_id}')
    except:  # catch all possible exceptions
        app.logger.error('Unhandled exception', exc_info=sys.exc_info())
    finally:
        # mark db task complete either success or fail
        _set_task_progress(100)


# track job status in redis queue and save to database Task row
def _set_task_progress(progress):
    job = get_current_job()  # get job bound to current task
    if job:
        job.meta['progress'] = progress
        # save meta data to redis queue entry
        job.save_meta()
        # mark job complete to Task db row with matching job ID
        task = Task.query.get(job.get_id())
        if progress >= 100:
            task.complete = True
        db.session.commit()


def example(seconds):
    job = get_current_job()
    print(f"Task started with job ID: {job.get_id()}")
    for i in range(seconds):
        job.meta['progress'] = 100.0 * i / seconds
        job.save_meta()  # save meta info to redis
        print(i)
        time.sleep(1)  # sleep for 1s each iteration
    job.meta['progress'] = 100
    job.save_meta()
    print('Task completed')
