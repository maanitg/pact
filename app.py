import uuid
from flask import Flask, request, url_for, session, redirect, render_template, jsonify, g
from flask_session import Session
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
import os
import time 
import json
from flask_caching import Cache
from datetime import datetime, timedelta
from time import gmtime, strftime
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, ValidationError
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from pymongo.errors import DuplicateKeyError


client = MongoClient(
    "mongodb+srv://maanit:We'reall50%25banana@tangle.h9qzr.mongodb.net/?retryWrites=true&w=majority&appName=tangle",
    server_api=ServerApi('1'),
    maxPoolSize=50,
    wtimeoutMS=2500,
    connectTimeoutMS=2000,
    serverSelectionTimeoutMS=3000
)


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
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'fotoxre@gmail.com'
app.config['MAIL_PASSWORD'] = 'ovuagvufsbfqwdng'
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)
app.secret_key = SECRET_KEY
#cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache'})

MATCHED = False

mail = Mail(app)
serializer = (URLSafeTimedSerializer(app.config['SECRET_KEY']))

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def get_password_by_email(email):
    # Find the document with the given email
    document = coll.find_one({"email": email})
    
    if document:
        # If the document exists, return the password
        return document.get("_password")
    else:
        # If no document is found with the given email
        return None



@app.route("/")
def index():
    session['user'] = None
    return render_template('index.html', title='Welcome')

@app.route('/register', methods=['GET', 'POST'])
def register():
    email = request.form.get('registerEmail')
    if not email.endswith('@stanford.edu'):
        return jsonify({'success': False, 'message': 'Please enter a Stanford email address.'})
    token = serializer.dumps(email, salt='email-confirm')
    if not coll.find_one({'email': email}):
        confirm_url = url_for('confirm_email', token=token, _external=True)
        msg = Message('Confirm Your Email', sender='your_email@gmail.com', recipients=[email])
        msg.body = f'Click the following link to confirm your email: {confirm_url}'
        mail.send(msg)
        print("sending reg!")
        return jsonify({'success': True, 'message': 'Please check your email to confirm your account.'})
    else:
        return jsonify({'success': False, 'message': 'Account already exists. Please log in.'})

@app.route('/forgot', methods=['GET', 'POST'])
def forgot_password():
    email = request.form.get('forgotEmail')
    if not email.endswith('@stanford.edu'):
        return jsonify({'success': False, 'message': 'Please enter your Stanford email address.'})
    if not coll.find_one({'email': email}):
        return jsonify({'success': False, 'message': 'Email not found. Register for new account.'})
    else:
        token = serializer.dumps(email, salt='email-confirm')
        confirm_url = url_for('confirm_email', token=token, _external=True)
        msg = Message('Confirm Your Email', sender='your_email@gmail.com', recipients=[email])
        msg.body = f'Click the following link to reset your password: {confirm_url}'
        mail.send(msg)
        print("sending!")
        return jsonify({'success': True, 'message': 'Please check your email for password reset link.'})

@app.route('/confirm_email/<token>')
def confirm_email(token):
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=3600)
    except:
        return 'The confirmation link is invalid or has expired.'
    

    coll.update_one(
        {"email": email},
        {"$set": {"confirmed": True, "confirmed_on": datetime.now()}},
        upsert=True
    )
    print(f"User confirmed with no issue: {email}")

    
    return render_template('set_password.html', email=email)


@app.route('/set_password/', methods=['POST'])
def set_password():

    email = request.form.get('setEmail') 
    password = request.form.get('password')
    if coll.find_one({'email': email}):
        coll.update_one({ "email": email },
        { "$set": { "_password": password }  }
        )
        
        session['user'] = email
        session['stored'] = False
        session['session_id'] = session.get('session_id', str(uuid.uuid4()))
        #fixed session id
        return jsonify({'success': True, 'message': 'Password set!'})
    else:
        return jsonify({'success': False, 'message': 'Invalid email address.'})
    
    
    

    
@app.route('/login', methods=['POST'])
def login():

    email = request.form.get('email')
    if not email.endswith('@stanford.edu'):
        return jsonify({'success': False, 'message': 'Please enter a Stanford email address.'})
    if not coll.find_one({'email': email}):
        return jsonify({'success': False, 'message': 'Account does not exist. Please register.'})
    password = request.form.get('password')
    p = get_password_by_email(email)

    if password == p:
        session.clear()
        session['user'] = email
        session['stored'] = False
        session['session_id'] = session.get('session_id', str(uuid.uuid4()))
        
        if coll.find_one({'email': session['user'], '_stored': 1}):
            session['stored'] = True
           
        return jsonify({'success': True, 'message': 'Logged in!'})    
    else:
        return jsonify({'success': False, 'message': 'Incorrect password, try again.'})


@app.route("/form")
def form():
    
    if not coll.find_one({'email': session['user'], '_profile': 1}):
        return render_template('form.html')
    else:
        return redirect(url_for("loginSpotify", _external=True))


@app.route('/submit-form', methods=['POST'])
#@cache.cached(timeout=50)
def submit_form():

    try:
        # Get JSON data from request
        data = request.get_json()  # Since we're sending JSON from the frontend
        
        # Process and upload data to MongoDB
        coll.update_one(
            {"email": session['user']},
            {"$set": {
                "_firstname": data["firstName"],
                "_lastname": data["lastName"],
                "_year": data["year"],
                "_gender": data["gender"],
                "_friendpartner": data["lookingFor"],  # This will be an array like ["Friend", "Partner"]
                "_partner": data["attractedTo"],       # This will be an array like ["Male", "Female"]
                "_redflag": data["spotifyRedFlag"],
                "_profile": 1
            }},
            upsert=True
        )

        return jsonify({"redirectUrl": url_for('loginSpotify')})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400

   

def create_spotify_oauth(session_id):
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=url_for("redirectPage",_external=True, _scheme='https'),
        scope="user-top-read user-library-read",
        cache_path=f'.spotipyoauthcache_{session_id}'
    )

# Request auth to access data
@app.route("/loginSpotify")
def loginSpotify():

    if not coll.find_one({'email': session['user'], '_stored': 1}):
        print("Accessing spotify...")
        session['sp_oauth'] = create_spotify_oauth(session['session_id'])
        print(session['sp_oauth'])
        auth_url = session['sp_oauth'].get_authorize_url()
        print(auth_url)
        return redirect(auth_url) # prompt user to login to Spotify
    else:
        print("redirecting to receipts, because stored is true")
        return redirect(url_for("receipts", _external=True))



def get_token(code):
    token_info = session['sp_oauth'].get_access_token(code)
    if not token_info:
        return redirect(url_for("loginSpotify"))
    else:
        now = int(time.time())
        if token_info['expires_at'] - now < 60:
            token_info = session['sp_oauth'].refresh_access_token(token_info['refresh_token'])
    return token_info

# fetch and store data from Spotify
@app.route("/redirectPage")
def redirectPage():
    
    # request access and refresh tokens
    code = request.args.get('code') # returns token
    session[TOKEN_INFO] = get_token(code)
    
    # retrieve data from API using access token
    coll.update_one(
            {"email": session['user']},
            {"$set": {
                "spotify_access_token": session[TOKEN_INFO]['access_token'],
                "spotify_refresh_token": session[TOKEN_INFO]['refresh_token'],
                "token_expiry": session[TOKEN_INFO]['expires_at']
            }},
            upsert=True
        )
   # if data not already stored:
    sp = spotipy.Spotify(oauth_manager=session['sp_oauth'], auth=session[TOKEN_INFO]['access_token'])
    print(sp.current_user()['display_name'])
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
    
    coll.update_one(
        { "email": session['user'] },
        { "$set": { "_stored": 1, 
                   "_short_tracks_obj": short_tracks_temp,
                    "_med_tracks_obj": medium_tracks_temp,
                    "_long_tracks_obj": long_tracks_temp,
                    "_short_tracks": short_tracks, 
                    "_med_tracks": medium_tracks,
                    "_long_tracks": long_tracks,
                    "_med_art": medium_art, 
                    "_long_art": long_art, 
                    "_med_gen": medium_gen, 
                    "_long_gen": long_gen, 
                    "_med_alb": medium_alb, 
                    "_long_alb": long_alb 
        }},
        upsert=True 
    )


    return redirect(url_for("receipts", _external=True))
    


@app.route("/receipts")
def receipts():
    if ((session['user'] is None) or (coll.find_one({'email': session['user'], '_stored': 1}) is None)):
        return render_template('receiptNoUser.html');
    else:

        user_data = coll.find_one({"email": session['user']})
        if not user_data or 'spotify_access_token' not in user_data:
            return redirect(url_for("loginSpotify"))
        
        current_user_name = session['user']

        short_term = coll.find_one({"email": session['user']}, {"_short_tracks_obj": 1, "_id": 0})
        medium_term = coll.find_one({"email": session['user']}, {"_med_tracks_obj": 1, "_id": 0})
        long_term = coll.find_one({"email": session['user']}, {"_long_tracks_obj": 1, "_id": 0})

        if os.path.exists(".cache"): 
            os.remove(".cache")

        return render_template('receipt.html', 
                               user_display_name=current_user_name, 
                               short_term=short_term['_short_tracks_obj'], 
                               medium_term=medium_term['_med_tracks_obj'], 
                               long_term=long_term['_long_tracks_obj'], 
                               title="You've connected your Spotify. Matches are coming.", 
                               currentTime=gmtime())
    

@app.route("/about")
def about():
    return render_template('about.html')

@app.route("/match")
def match():
    if not globals()["MATCHED"]:
        return render_template('match.html')
    else:
        return render_template('match.html')



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
