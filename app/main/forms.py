from flask import request
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField
from wtforms.validators import ValidationError
from wtforms.validators import DataRequired
from wtforms.validators import Length
from app.models import User


# this search form supports direct Enter key-press for form submission
# this search form is loaded in before_request interceptor, see:
# `app/main/routes.py`
class SearchForm(FlaskForm):
    q = StringField('Search', validators=[DataRequired()])

    # Custom constructor to support GET params by loading request.args
    # into `formdata` hash.
    # Also disable csrf in form submission to support GET request.
    # By setting 'meta' to {'csrf': False}, flask-wtf knows this form bypasses
    # csrf validation.
    # This is because forms have CSRF protection added by default, with the
    # inclusion of a CSRF token that is added to the form via the
    # `form.hidden_tag()` construct in form templates.
    def __init__(self, *args, **kwargs):
        if 'formdata' not in kwargs:
            kwargs['formdata'] = request.args
        if 'meta' not in kwargs:
            kwargs['meta'] = {'csrf': False}
        super(SearchForm, self).__init__(*args, **kwargs)


class EditProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3)])
    about_me = TextAreaField('About me', validators=[Length(min=0, max=140)])
    submit = SubmitField('Submit')

    # sqlalchemy model classes usually only define db level validation
    # entity (application) level validations are defined in FlaskForms

    # overloaded constructor that takes argument `username`, saves it
    # as original_username in internal state during instantiation
    # this overloaded constructor saves original username value
    # in case new input value fails validation
    def __init__(self, original_username, *args, **kwargs):
        # get EditProfileForm's super class (which is FlaskForm) constructor
        # to instantiate an instance
        super(EditProfileForm, self).__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, username):
        if username != self.original_username:
            user = User.query.filter_by(username=username.data).first()
            if user is not None:
                raise ValidationError('Username already taken, please use a different username')


class PostForm(FlaskForm):
    post = TextAreaField("Say something", validators=[
        DataRequired(), Length(min=1, max=140)
    ])
    submit = SubmitField('Submit')
