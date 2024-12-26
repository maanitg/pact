
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, ValidationError
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import os




def validate_stanford_email(form, field):
    if not field.data.endswith('@stanford.edu'):
        raise ValidationError('Please use your Stanford email address.')
    
class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email(), validate_stanford_email])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Register')

