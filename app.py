import hmac
import os
import uuid
from datetime import datetime, timedelta, timezone
from functools import wraps
from time import gmtime

from flask import Flask, jsonify, redirect, render_template, request, session, url_for
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from werkzeug.security import check_password_hash, generate_password_hash

from match_lab import build_match_lab
from match_schedule import match_cycle
from music_profile import build_music_profile


app = Flask(__name__)
app.config.update(
    MAIL_SERVER=os.environ.get("MAIL_SERVER", "smtp.gmail.com"),
    MAIL_PORT=int(os.environ.get("MAIL_PORT", "587")),
    MAIL_USE_TLS=True,
    MAIL_USE_SSL=False,
    MAIL_USERNAME=os.environ.get("MAIL_USERNAME"),
    MAIL_PASSWORD=os.environ.get("MAIL_PASSWORD"),
    PERMANENT_SESSION_LIFETIME=timedelta(
        days=int(os.environ.get("SESSION_LIFETIME_DAYS", "30"))
    ),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true",
)
if os.environ.get("MONGO_URI") and not os.environ.get("SECRET_KEY"):
    raise RuntimeError("Set SECRET_KEY whenever persistent accounts are enabled.")
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-change-me")

mail = Mail(app)
serializer = URLSafeTimedSerializer(app.secret_key)
ACCOUNT_TOKEN_SALT = "wavelength-account-action-v1"
ACCOUNT_TOKEN_MAX_AGE = int(os.environ.get("ACCOUNT_TOKEN_MAX_AGE", "3600"))


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
    collection = client[os.environ.get("MONGO_DB", "tangle")][
        os.environ.get("MONGO_COLLECTION", "users")
    ]
    collection.create_index("email", unique=True, name="unique_account_email")
    return collection


coll = create_collection()


def database_required():
    if coll is None:
        return jsonify(
            success=False,
            message="Account services are not configured in this environment.",
        ), 503
    return None


def utc_now():
    return datetime.now(timezone.utc)


def stanford_email(value):
    email = (value or "").strip().lower()
    return email if email.endswith("@stanford.edu") else None


def account_required(view):
    """Require an account in deployed mode; keep the database-free demo usable."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if coll is not None and not session.get("user"):
            if request.path.startswith("/api/"):
                return jsonify(success=False, message="Please log in first."), 401
            return redirect(url_for("index", next=request.path))
        return view(*args, **kwargs)

    return wrapped


def begin_account_action(email, purpose):
    action_id = uuid.uuid4().hex
    token = serializer.dumps(
        {"email": email, "purpose": purpose, "action_id": action_id},
        salt=ACCOUNT_TOKEN_SALT,
    )
    coll.update_one(
        {"email": email},
        {
            "$set": {
                "email": email,
                "_account_action_id": action_id,
                "_account_action_purpose": purpose,
                "_account_action_requested_on": utc_now(),
            },
            "$setOnInsert": {
                "confirmed": False,
                "created_on": utc_now(),
                "_profile": 0,
                "_stored": 0,
            },
        },
        upsert=True,
    )
    return token


def load_account_action(token):
    payload = serializer.loads(
        token, salt=ACCOUNT_TOKEN_SALT, max_age=ACCOUNT_TOKEN_MAX_AGE
    )
    if not isinstance(payload, dict):
        raise ValueError("Invalid account action")
    email = stanford_email(payload.get("email"))
    purpose = payload.get("purpose")
    action_id = payload.get("action_id")
    if not email or purpose not in {"register", "reset"} or not action_id:
        raise ValueError("Invalid account action")
    user = coll.find_one(
        {
            "email": email,
            "_account_action_id": action_id,
            "_account_action_purpose": purpose,
        }
    )
    if not user:
        raise ValueError("Account action has already been used")
    return payload, user


def send_account_email(email, purpose, token):
    action_url = url_for("confirm_email", token=token, _external=True)
    subject = "Confirm your Wavelength account" if purpose == "register" else "Reset your Wavelength password"
    verb = "finish creating your account" if purpose == "register" else "reset your password"
    msg = Message(subject, sender=app.config["MAIL_USERNAME"], recipients=[email])
    msg.body = f"Open this one-time link within one hour to {verb}: {action_url}"
    mail.send(msg)


def start_user_session(email):
    session.clear()
    session.permanent = True
    session["user"] = email
    session["session_id"] = str(uuid.uuid4())
    user = coll.find_one({"email": email}, {"_stored": 1}) if coll is not None else None
    session["stored"] = bool(user and user.get("_stored"))


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
    return render_template(
        'index.html',
        title='Welcome',
        current_user=session.get("user"),
        accounts_enabled=coll is not None,
    )

@app.route('/register', methods=['POST'])
def register():
    unavailable = database_required()
    if unavailable:
        return unavailable
    email = stanford_email(request.form.get('registerEmail'))
    if not email:
        return jsonify({'success': False, 'message': 'Please enter a Stanford email address.'})
    existing = coll.find_one({'email': email})
    if existing and existing.get('confirmed') and existing.get('_password'):
        return jsonify({'success': False, 'message': 'Account already exists. Please log in.'})
    if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
        return jsonify({'success': False, 'message': 'Email delivery is not configured.'}), 503
    token = begin_account_action(email, "register")
    send_account_email(email, "register", token)
    return jsonify({'success': True, 'message': 'Please check your email to confirm your account.'})

@app.route('/forgot', methods=['POST'])
def forgot_password():
    unavailable = database_required()
    if unavailable:
        return unavailable
    email = stanford_email(request.form.get('forgotEmail'))
    if not email:
        return jsonify({'success': False, 'message': 'Please enter your Stanford email address.'})
    user = coll.find_one({'email': email, 'confirmed': True})
    if user:
        if not app.config.get('MAIL_USERNAME') or not app.config.get('MAIL_PASSWORD'):
            return jsonify({'success': False, 'message': 'Email delivery is not configured.'}), 503
        token = begin_account_action(email, "reset")
        send_account_email(email, "reset", token)
    # Do not disclose whether a Stanford address has an account.
    return jsonify({'success': True, 'message': 'If that account exists, a reset link is on its way.'})

@app.route('/confirm_email/<token>')
def confirm_email(token):
    unavailable = database_required()
    if unavailable:
        return unavailable
    try:
        payload, user = load_account_action(token)
    except Exception:
        return 'The confirmation link is invalid or has expired.', 400
    if payload["purpose"] == "register" and not user.get("confirmed"):
        coll.update_one(
            {"email": payload["email"]},
            {"$set": {"confirmed": True, "confirmed_on": utc_now()}},
        )
    return render_template('set_password.html', action_token=token)


@app.route('/set_password', methods=['POST'])
def set_password():
    unavailable = database_required()
    if unavailable:
        return unavailable
    password = request.form.get('password') or ''
    if len(password) < 10:
        return jsonify({'success': False, 'message': 'Use at least 10 characters.'}), 400
    token = request.form.get('actionToken') or ''
    try:
        payload, user = load_account_action(token)
    except Exception:
        return jsonify({'success': False, 'message': 'This link is invalid, expired, or already used.'}), 400
    if not user.get('confirmed'):
        return jsonify({'success': False, 'message': 'Confirm your Stanford email first.'}), 400
    result = coll.update_one(
        {"email": payload["email"], "_account_action_id": payload["action_id"]},
        {
            "$set": {"_password": generate_password_hash(password), "password_changed_on": utc_now()},
            "$unset": {
                "_account_action_id": "",
                "_account_action_purpose": "",
                "_account_action_requested_on": "",
            },
        },
    )
    if not result.modified_count:
        return jsonify({'success': False, 'message': 'This link has already been used.'}), 400
    start_user_session(payload["email"])
    return jsonify({'success': True, 'message': 'Password set!'})
    
    
    

    
@app.route('/login', methods=['POST'])
def login():
    unavailable = database_required()
    if unavailable:
        return unavailable
    email = stanford_email(request.form.get('email'))
    if not email:
        return jsonify({'success': False, 'message': 'Please enter a Stanford email address.'})
    user = coll.find_one({'email': email, 'confirmed': True})
    if not user:
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
        start_user_session(email)
        return jsonify({'success': True, 'message': 'Logged in!'})    
    else:
        return jsonify({'success': False, 'message': 'Incorrect password, try again.'})


@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('index'))


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
    if match_cycle()["phase"] in {"locked", "released"}:
        return jsonify({"error": "This cohort is locked. Your changes can enter the next cycle."}), 409
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
@account_required
def music_profile():
    return render_template(
        "music_profile.html",
        title="Build your music profile",
        existing_profile=get_current_music_profile(),
    )


@app.route("/api/music-profile", methods=["POST"])
@account_required
def save_music_profile():
    if coll is not None and match_cycle()["phase"] in {"locked", "released"}:
        return jsonify(
            success=False,
            message="This cohort is locked. Your changes can enter the next cycle.",
        ), 409
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
                    "_short_tracks": profile["current_items"],
                    "_long_tracks": profile["rewind_items"],
                    "_long_art": profile["forever_artists"],
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
@account_required
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


@app.route("/match-lab")
def match_lab_page():
    try:
        noise_percent = max(0, min(int(request.args.get("noise", "0")), 50))
    except ValueError:
        noise_percent = 0
    respect_constraints = request.args.get("constraints", "1") != "0"
    return render_template(
        "match_lab.html",
        title="Synthetic Match Lab",
        lab=build_match_lab(noise_percent, respect_constraints),
    )


@app.route("/api/match-lab")
def match_lab_api():
    try:
        noise_percent = max(0, min(int(request.args.get("noise", "0")), 50))
    except ValueError:
        noise_percent = 0
    respect_constraints = request.args.get("constraints", "1") != "0"
    return jsonify(build_match_lab(noise_percent, respect_constraints))
    

@app.route("/about")
def about():
    return render_template('about.html')

@app.route("/match")
@account_required
def match():
    cycle = match_cycle()
    participant = None
    match_name = None
    email = session.get("user")
    if email and coll is not None:
        participant = coll.find_one(
            {"email": email},
            {"_profile": 1, "_music_profile": 1, "_match": 1, "_match_cycle": 1},
        )
        if (
            cycle["phase"] == "released"
            and participant
            and participant.get("_match")
            and participant.get("_match_cycle") == cycle["name"]
        ):
            matched = coll.find_one(
                {"email": participant["_match"]},
                {"_firstname": 1, "_lastname": 1},
            )
            if matched:
                match_name = " ".join(
                    part for part in (matched.get("_firstname"), matched.get("_lastname")) if part
                )
    return render_template(
        'match.html', cycle=cycle, participant=participant, match_name=match_name
    )



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
