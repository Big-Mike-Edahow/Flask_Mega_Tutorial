# forms.py

from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, TextAreaField, ValidationError
from wtforms.validators import DataRequired, Length

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Login')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    submit = SubmitField('Register')

class EditProfileForm(FlaskForm):
    nickname = StringField('Nickname', validators=[DataRequired()])
    about = TextAreaField('About', validators=[Length(min=0, max=250)])
    submit = SubmitField('Submit')
    
class PostForm(FlaskForm):
    title = StringField('Title', [DataRequired(), Length(max=255)])
    body = TextAreaField('Content', [DataRequired()])

class CommentForm(FlaskForm):
    comment = TextAreaField(u'Comment', validators=[DataRequired()])
