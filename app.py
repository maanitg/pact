

from flask import Flask, request, url_for, session, redirect, render_template, jsonify
import spotipy
from database import Database
from spotipy.oauth2 import SpotifyOAuth
from registration import RegistrationForm
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import os
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, ValidationError



CLIENT_ID = "ff513e5fd4dd4e7483ee15b1f58215aa"
CLIENT_SECRET = "0b159e97f65d4ecc86ffcc6ceb82afd7"
TOKEN_INFO = "token_info"
SECRET_KEY = "asdf"

MEDIUM_TERM = "medium_term"
SHORT_TERM = "short_term"
LONG_TERM = "long_term"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_email@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_email_password'
app.secret_key = SECRET_KEY
app.config['SERVER_NAME'] = 'legendary-train-4r6j4qv7p76c7w6g-5000.app.github.dev'

database = Database
mail = Mail(app)
serializer = (URLSafeTimedSerializer(app.config['SECRET_KEY']))

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=url_for("redirectPage",_external=True, _scheme='https'),
        scope="user-top-read user-library-read"
    )

@app.route("/")
def index():
    return render_template('index.html', title='Welcome')

@app.route('/login_school', methods=['GET', 'POST'])
def login_school():

    email = request.form.get('email')
    if not email.endswith('@stanford.edu'):
        return jsonify({'success': False, 'message': 'Please enter a Stanford email address.'})

    token = serializer.dumps(email, salt='email-confirm')
    if(not database.contains_email):
        confirm_url = url_for('confirm_email', token=token, _external=True)
        msg = Message('Confirm Your Email', sender='your_email@gmail.com', recipients=[email])
        msg.body = f'Click the following link to confirm your email: {confirm_url}'
        mail.send(msg)
        return jsonify({'success': True, 'message': 'Please check your email to confirm your account.'})
    else:
         # redirect to login instead of registration

    
@app.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=3600)
    except:
        return 'The confirmation link is invalid or has expired.'
    
    # Here you would typically save the email to your database
    database.regi
    # For now, we'll just render a template to set the password
    return render_template('set_password.html', email=email)

@app.route('/set_password/', methods=['POST'])
def set_password():
    email = request.form.get('email') 
    if not (database.contains_email(email)):
                return jsonify({'success': False, 'message': 'Please enter your provided email address.'})
    password = request.form.get('password')
    return jsonify({'success': True, 'message': 'Account created successfully!'})

@app.route("/loginSpotify")
def login():
    sp_oauth = create_spotify_oauth()
    auth_url = sp_oauth.get_authorize_url()
    return redirect(auth_url)

@app.route("/redirectPage")
def redirectPage():
    sp_oauth = create_spotify_oauth()
    session.clear()
    code = request.args.get('code') # returns token
    token_info = sp_oauth.get_access_token(code)
    session[TOKEN_INFO] = token_info
    return redirect(url_for("receipt", _external=True))
    
def get_token():
    token_info = session.get(TOKEN_INFO, None)
    return token_info

@app.route("/receipt")
def receipt():
    user_token = get_token()
    sp = spotipy.Spotify(
        auth=user_token['access_token']
    )

    short_term = sp.current_user_top_tracks(
        limit=10,
        offset=0,
        time_range=SHORT_TERM,
    )
    medium_term = sp.current_user_top_tracks(
        limit=10,
        offset=0,
        time_range=MEDIUM_TERM,
    )
    long_term = sp.current_user_top_tracks(
        limit=10,
        offset=0,
        time_range=LONG_TERM,
    )

    return render_template('receipt.html', short_term=short_term, medium_term=medium_term, long_term=long_term)


