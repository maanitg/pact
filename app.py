import hmac
import os
import uuid
from datetime import datetime
from time import gmtime

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from werkzeug.security import check_password_hash, generate_password_hash

from music_profile import build_music_profile


app = Flask(__name__)
app.config.update(
    MAIL_SERVER=os.environ.get("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_PORT=int(os.environ.get("MAIL_PORT", "587")),
    MAIL_USE_TLS=True,
    MAIL_USE_SSL=False,
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
    SESSION_PERMANENT=False,
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)


def create_collection():
    """Connect only when a Mongo URI is configured."""
    mongo_uri = os.environ.get("MONGO_URI")
    if not mongo_uri:
        return None
    client = MongoClient(
        mongo_uri,
        server_api=ServerApi("1"),
        maxPoolSize=50,
        wtimeoutMS=2500,
        connectTimeoutMS=2000,
        serverSelectionTimeoutMS=3000,
    )
    return client[os.environ.get("MONGO_DB", "tangle")][
        os.environ.get("MONGO_COLLECTION", "users")
    ]


coll = create_collection()


def database_required():
    if coll is None:
        return jsonify(
            success=False,
            message="Account services are not configured in this environment.",
        ), 503
    return None


def get_current_music_profile():
    profile = session.get("music_profile")
    email = session.get("user")
    if email and coll is not None:
        user = coll.find_one({"email": email}, {"_music_profile": 1, "_id": 0})
        if user and user.get("_music_profile"):
            profile = user["_music_profile"]
    return profile


def is_password_hash(value):
    return isinstance(value, str) and value.startswith(("scrypt:", "pbkdf2:"))

def get_password_by_email(email):
    if coll is None:
        return None
    document = coll.find_one({"email": email})
    return document.get("_password") if document else None



@app.route("/")
def index():
    return render_template('index.html', title='Welcome')

@app.route('/register', methods=['POST'])
def register():
    unavailable = database_required()
    if unavailable:
        return unavailable
    email = (request.form.get('registerEmail') or '').strip().lower()
    if not email.endswith('@stanford.edu'):
        return jsonify({'success': False, 'message': 'Please enter a Stanford email address.'})
    token = serializer.dumps(email, salt='email-confirm')
    if not coll.find_one({'email': email}):
        confirm_url = url_for('confirm_email', token=token, _external=True)
        if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
            return jsonify({'success': False, 'message': 'Email delivery is not configured.'}), 503
        msg = Message('Confirm Your Email', sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f'Click the following link to confirm your email: {confirm_url}'
        mail.send(msg)
        print("sending reg!")
        return jsonify({'success': True, 'message': 'Please check your email to confirm your account.'})
    else:
        return jsonify({'success': False, 'message': 'Account already exists. Please log in.'})

@app.route('/forgot', methods=['POST'])
def forgot_password():
    unavailable = database_required()
    if unavailable:
        return unavailable
    email = (request.form.get('forgotEmail') or '').strip().lower()
    if not email.endswith('@stanford.edu'):
        return jsonify({'success': False, 'message': 'Please enter your Stanford email address.'})
    if not coll.find_one({'email': email}):
        return jsonify({'success': False, 'message': 'Email not found. Register for new account.'})
    else:
        token = serializer.dumps(email, salt='email-confirm')
        confirm_url = url_for('confirm_email', token=token, _external=True)
        if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
            return jsonify({'success': False, 'message': 'Email delivery is not configured.'}), 503
        msg = Message('Reset Your Password', sender=app.config['MAIL_USERNAME'], recipients=[email])
        msg.body = f'Click the following link to reset your password: {confirm_url}'
        mail.send(msg)
        print("sending!")
        return jsonify({'success': True, 'message': 'Please check your email for password reset link.'})

@app.route('/confirm_email/<token>')
def confirm_email(token):
    unavailable = database_required()
    if unavailable:
        return unavailable
    try:
        email = serializer.loads(token, salt='email-confirm', max_age=3600)
    except Exception:
        return 'The confirmation link is invalid or has expired.', 400
    

    coll.update_one(
        {"email": email},
        {"$set": {"confirmed": True, "confirmed_on": datetime.now()}},
        upsert=True
    )
    print(f"User confirmed with no issue: {email}")

    
    return render_template('set_password.html', email=email)


@app.route('/set_password/', methods=['POST'])
def set_password():
    unavailable = database_required()
    if unavailable:
        return unavailable
    email = (request.form.get('setEmail') or '').strip().lower()
    password = request.form.get('password') or ''
    if len(password) < 10:
        return jsonify({'success': False, 'message': 'Use at least 10 characters.'}), 400
    if coll.find_one({'email': email, 'confirmed': True}):
        coll.update_one({ "email": email },
        { "$set": { "_password": generate_password_hash(password) }  }
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
    unavailable = database_required()
    if unavailable:
        return unavailable
    email = (request.form.get('email') or '').strip().lower()
    if not email.endswith('@stanford.edu'):
        return jsonify({'success': False, 'message': 'Please enter a Stanford email address.'})
    if not coll.find_one({'email': email}):
        return jsonify({'success': False, 'message': 'Account does not exist. Please register.'})
    password = request.form.get('password') or ''
    p = get_password_by_email(email)

    valid_password = (
        check_password_hash(p, password)
        if is_password_hash(p)
        else hmac.compare_digest(p or '', password)
    )
    if valid_password:
        if not is_password_hash(p):
            coll.update_one(
                {'email': email},
                {'$set': {'_password': generate_password_hash(password)}}
            )
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
    email = session.get('user')
    if not email:
        return redirect(url_for('index'))
    if coll is None:
        return redirect(url_for('music_profile'))
    if not coll.find_one({'email': email, '_profile': 1}):
        return render_template('form.html')
    else:
        return redirect(url_for("music_profile"))


@app.route('/submit-form', methods=['POST'])
#@cache.cached(timeout=50)
def submit_form():
    email = session.get('user')
    if not email:
        return jsonify({"error": "Please log in before submitting the form."}), 401
    if coll is None:
        return jsonify({"error": "Account services are not configured."}), 503
    try:
        # Get JSON data from request
        data = request.get_json()  # Since we're sending JSON from the frontend
        
        # Process and upload data to MongoDB
        coll.update_one(
            {"email": email},
            {"$set": {
                "_firstname": data["firstName"],
                "_lastname": data["lastName"],
                "_year": data["year"],
                "_gender": data["gender"],
                "_friendpartner": data["lookingFor"],  # This will be an array like ["Friend", "Partner"]
                "_partner": data["attractedTo"],       # This will be an array like ["Male", "Female"]
                "_redflag": data["spotifyRedFlag"],
                "_spotify_reflection": data.get("spotifyReflection"),
                "_music_openness": data.get("musicOpenness"),
                "_profile": 1
            }},
            upsert=True
        )

        return jsonify({"redirectUrl": url_for('music_profile')})
    
    except Exception as e:
        return jsonify({"error": str(e)}), 400

   

@app.route("/loginSpotify")
def loginSpotify():
    return redirect(url_for("music_profile"), code=301)


@app.route("/redirectPage")
def redirectPage():
    return redirect(url_for("music_profile"), code=301)
@app.route("/music-profile")
def music_profile():
    return render_template(
        "music_profile.html",
        title="Build your music profile",
        existing_profile=get_current_music_profile(),
    )


@app.route("/api/music-profile", methods=["POST"])
def save_music_profile():
    try:
        profile = build_music_profile(request.get_json(silent=True) or {})
    except ValueError as error:
        return jsonify(success=False, message=str(error)), 400

    # Screenshot pixels are processed in the browser. Only confirmed text is saved.
    session["music_profile"] = profile
    session.modified = True
    email = session.get("user")
    if email and coll is not None:
        coll.update_one(
            {"email": email},
            {
                "$set": {
                    "_music_profile": profile,
                    "_short_tracks": profile["top_tracks"],
                    "_med_art": profile["top_artists"],
                    "_stored": 1,
                },
                "$unset": {
                    "spotify_access_token": "",
                    "spotify_refresh_token": "",
                    "token_expiry": "",
                },
            },
            upsert=True,
        )
    return jsonify(success=True, redirectUrl=url_for("receipts"))


@app.route("/receipts")
def receipts():
    profile = get_current_music_profile()
    if not profile:
        return redirect(url_for("music_profile"))
    display_name = (session.get("user") or "GUEST").split("@")[0]
    return render_template(
        "music_receipt.html",
        user_display_name=display_name,
        profile=profile,
        title="Your music fingerprint is ready.",
        currentTime=gmtime(),
    )
    

@app.route("/about")
def about():
    return render_template('about.html')

@app.route("/match")
def match():
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


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
