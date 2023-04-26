import unittest
from config import Config
from app import create_app, db
from app.models import User


# overriding Config class with testing need
class TestConfig(Config):
    TESTING = True
    # use an in-memory sqlite db for testing
    SQLALCHEMY_DATABASE_URI = 'sqlite://'


class UserModelCase(unittest.TestCase):
    def setUp(self) -> None:
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        # app_context.push() injects context to the current active app
        # so that `current_app` is attached to this active app
        # `current_app.config` is used by sqlalchemy to identify the
        # correct db setting
        self.app_context.push()
        # pave down all db components in `current_app`, the testing db
        db.create_all()

    def tearDown(self) -> None:
        db.session.remove()
        db.drop_all()
        # remove the injected testing application context
        self.app_context.pop()

    def test_password_hashing(self):
        u = User(username='susan')
        u.set_password('cat')
        self.assertFalse(u.check_password('dog'))
        self.assertTrue(u.check_password('cat'))


if __name__ == '__main__':
    unittest.main(verbosity=2)