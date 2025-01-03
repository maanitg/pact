from flask import Flask, request, url_for, session, redirect, render_template, jsonify
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import os
import time 
from datetime import datetime
from time import gmtime, strftime
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, ValidationError
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi


# database set up


uri = "mongodb+srv://maanit:We'reall50%25banana@tangle.h9qzr.mongodb.net/?retryWrites=true&w=majority&appName=tangle"
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = client.tangle
coll = db.users


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
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'fotoxre@gmail.com'
app.config['MAIL_PASSWORD'] = 'ovuagvufsbfqwdng'
app.secret_key = SECRET_KEY
# app.config['SERVER_NAME'] = 'legendary-train-4r6j4qv7p76c7w6g-5000.app.github.dev'

USER = None
STORED = False
mail = Mail(app)
serializer = (URLSafeTimedSerializer(app.config['SECRET_KEY']))



def get_password_by_email(email):
    # Find the document with the given email
    document = coll.find_one({"_email": email})
    
    if document:
        # If the document exists, return the password
        return document.get("_password")
    else:
        # If no document is found with the given email
        return None

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=url_for("redirectPage",_external=True, _scheme='http'),
        scope="user-top-read user-library-read"
    )

@app.route("/")
def index():
    return render_template('index.html', title='Welcome')

@app.route('/register', methods=['GET', 'POST'])
def register():
    email = request.form.get('registerEmail')
    if not email.endswith('@stanford.edu'):
        return jsonify({'success': False, 'message': 'Please enter a Stanford email address.'})
    token = serializer.dumps(email, salt='email-confirm')
    if not coll.find_one({'_email': email}):
        confirm_url = url_for('confirm_email', token=token, _external=True)
        msg = Message('Confirm Your Email', sender='your_email@gmail.com', recipients=[email])
        msg.body = f'Click the following link to confirm your email: {confirm_url}'
        mail.send(msg)
        return jsonify({'success': True, 'message': 'Please check your email to confirm your account.'})
    else:
        return jsonify({'success': False, 'message': 'Account already exists. Please log in.'})

    
@app.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=3600)
    except:
        return 'The confirmation link is invalid or has expired.'
    
    coll.insert_one({ "_email": email})
    return render_template('set_password.html', email=email)

@app.route('/set_password/', methods=['POST'])
def set_password():
    email = request.form.get('email') 
    if (coll.find_one({'_email': email})):
        password = request.form.get('password')
        coll.update_one({ "_email": email },
            { "$set": { "_password": password, "_stored": 0 }  }
        )
        return jsonify({'success': True, 'message': 'Account created successfully!'})
    else:
        return jsonify({'success': False, 'message': 'Please enter your provided email address.'})

    
@app.route('/login', methods=['POST'])
def login():

 
    email = request.form.get('email')

    if not email.endswith('@stanford.edu'):
        return jsonify({'success': False, 'message': 'Please enter a Stanford email address.'})
    if not coll.find_one({'_email': email}):
        return jsonify({'success': False, 'message': 'Account does not exist. Please register.'})
    password = request.form.get('password')
    p = get_password_by_email(email)

    if password == p:
    
        globals()["USER"] = email
        
        if coll.find_one({'_email': globals()["USER"], '_stored': 1}):
            globals()["STORED"] = True
           
        return jsonify({'success': True, 'message': 'Logged in!'})    
    else:
        return jsonify({'success': False, 'message': 'Incorrect password, try again.'})

    # add forgot password button

@app.route("/form")
def form():
    return render_template('form.html')

@app.route("/loginSpotify")
def loginSpotify():

 #   if not coll.find_one({'_email': globals()["USER"], '_stored': 1}):
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
    return redirect(url_for("storeData", _external=True))
    
def get_token():
    token_info = session.get(TOKEN_INFO, None)
    return token_info

@app.route("/storeData")
def storeData():
 
    if not globals()["STORED"]:
        user_token = get_token()
        sp = spotipy.Spotify(
            auth=user_token['access_token']
        )
        current_user_name = sp.current_user()['display_name']
        short_tracks_temp = sp.current_user_top_tracks(
            limit=10,
            time_range=SHORT_TERM,
        )
        medium_tracks_temp = sp.current_user_top_tracks(
            limit=10,
            time_range=MEDIUM_TERM,
        )
        long_tracks_temp = sp.current_user_top_tracks(
            limit=10,
            time_range=LONG_TERM,
        )
        medium_art_temp = sp.current_user_top_artists(
            limit=20,
            time_range=MEDIUM_TERM,
        )
        long_art_temp = sp.current_user_top_artists(
            limit=20,
            time_range=LONG_TERM,
        )
        short_tracks = []
        for track in short_tracks_temp['items']:
            short_tracks.append(track['name'])
        medium_tracks = []
        for track in medium_tracks_temp['items']:
            medium_tracks.append(track['name'])
        long_tracks = []
        for track in long_tracks_temp['items']:
            long_tracks.append(track['name'])
        medium_art = []
        for artist in medium_art_temp['items']:
            medium_art.append(artist['name'])
        long_art = []
        for artist in long_art_temp['items']:
            long_art.append(artist['name'])

        medium_alb = []
        for track in medium_tracks_temp['items']:
            medium_alb.append(track['album'])
        long_alb = []
        for track in long_tracks_temp['items']:
            long_alb.append(track['album'])

        medium_gen = []
        for artist in medium_art_temp['items']:
            medium_gen.extend(artist['genres'])
        medium_gen = sorted(list(set(medium_gen)))
        long_gen = []
        for artist in long_art_temp['items']:
            long_gen.extend(artist['genres'])
        long_gen = sorted(list(set(long_gen)))
        
        coll.update_one({ "_email": globals()["USER"] },
            { "$set": { "_stored": 1, "_short_tracks_obj": short_tracks_temp, "_med_tracks_obj": medium_tracks_temp, "_long_tracks_obj": long_tracks_temp, "_short_tracks": short_tracks, "_med_tracks": medium_tracks, "_long_tracks": long_tracks, "_med_art": medium_art, "_long_art": long_art, "_med_gen": medium_gen, "_long_gen": long_gen, "_med_alb": medium_alb, "_long_alb": long_alb } } 
        )
        
    short_term = coll.find_one({"_email": USER}, {"_short_tracks_obj": 1, "_id": 0})
    medium_term = coll.find_one({"_email": USER}, {"_med_tracks_obj": 1, "_id": 0})
    long_term = coll.find_one({"_email": USER}, {"_long_tracks_obj": 1, "_id": 0})
    return render_template('receipt.html', user_display_name=current_user_name, short_term=short_term['_short_tracks_obj'], medium_term=medium_term['_med_tracks_obj'], long_term=long_term['_long_tracks_obj'], title="You've connected your Spotify - now sit back and relax!", currentTime=gmtime())

@app.template_filter('strftime')
def _jinja2_filter_datetime(date, fmt="%a, %d %b %Y"):
    if isinstance(date, str):
        try:
            date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return date  # Return original string if parsing fails
    elif isinstance(date, (int, float)):
        date = datetime.fromtimestamp(date)
    
    if isinstance(date, datetime):
        return date.strftime(fmt)
    else:
        return str(date)  # 

@app.template_filter('mmss')
def _jinja2_filter_miliseconds(time, fmt=None):
    time = int(time / 1000)
    minutes = time // 60 
    seconds = time % 60 
    if seconds < 10: 
        return str(minutes) + ":0" + str(seconds)
    return str(minutes) + ":" + str(seconds ) 