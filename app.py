from flask import Flask, render_template, redirect, url_for, request, make_response
from flask.ext.sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import bcrypt, uuid, json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    username = db.Column(db.String(), unique=True)
    password = db.Column(db.String())
    salt = db.Column(db.String())
    session_id = db.Column(db.String())
    session_time = db.Column(db.String())
    user_account_type = db.Column(db.String())

    def __init__(self, username, password, salt, session_id, session_time, user_account_type):
        self.username = username
        self.password = password
        self.salt = salt
        self.session_id = session_id
        self.session_time = session_time
        self.user_account_type = user_account_type

    def __repr__(self):
        return '<User %r>' % self.username


class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    video = db.Column(db.String())
    title = db.Column(db.String())
    uploader = db.Column(db.String())

    def __init__(self, video, title, uploader):
        self.video = video
        self.title = title
        self.uploader = uploader

    def __repr__(self):
        return '<Video %r>' % self.id


# Returns True if specified cookie is in the User's Browser
def cookie_exists(cookie_name):
    if cookie_name in request.cookies:
        return True
    else:
        return False


# Returns a dict with the data from the specified cookie
def get_saved_data(key):
    data = json.loads(request.cookies.get(key, '{}'))
    return data


# Input: Username Output: Dictionary containing information on the row containing that user's information
# Used for getting data, not for updating data
def db_user_info(type_of_request, data):
    if type_of_request == "username":
        # return json.loads(str(User.query.filter_by(username=data).first()))
        return User.query.filter_by(username=data).first()
    elif type_of_request == "session_id":
        # return json.loads(str(User.query.filter_by(session_id=data).first()))
        return User.query.filter_by(session_id=data).first()


# Returns true if session is valid, returns false if not
# It checks if the session_id is in the database, and then checks the last time it was activated
# If activated more than 20 minutes ago, it'll return False.
def check_if_valid_session(session_id):
    if session_id == "invalid":
        return False
    else:
        try:
            if db_user_info("session_id", session_id).session_id == session_id:
                original_time = datetime.strptime(db_user_info("session_id", session_id).session_time,
                                                  "%Y-%m-%d %H:%M:%S.%f")
                right_now = datetime.strptime(str(datetime.utcnow()), "%Y-%m-%d %H:%M:%S.%f")

                if original_time < right_now + timedelta(minutes=-20):
                    # print("Session too old. Last login was {} and it is now {}".format(original_time, right_now))
                    return False
                else:
                    # print("Session not too old. Last login was {} and it is now {}".format(original_time, right_now))
                    return True
            else:
                print("Error getting session id")
                return False
        except:
            try:
                print(session_id)
                print(db_user_info("session_id", session_id).session_id)
            except:
                print("No such user exists")
            return False


# Returns the session_id from the database to be put into a dict in the user's cookies if the
# username/password combination is right. If they're wrong it returns invalid.
def make_session(form_data):
    try:
        account = db_user_info("username", form_data.get('username', ''))
        hashed_password = account.password
        salt = account.salt
        entered_password = bcrypt.hashpw(str.encode(form_data.get('password')), salt)
        if hashed_password == entered_password:
            user = User.query.filter_by(username=form_data.get('username', '')).first()
            user.session_time = str(datetime.utcnow())
            db.session.commit()
            return db_user_info("username", form_data.get('username')).session_id
        else:
            return "invalid"
    except:
        print("Wrong Username or Password")
        return "invalid"


def is_admin(session_id):
    if db_user_info("session_id", session_id).user_account_type == "admin":
        return True
    else:
        return False


def database_add_user(username, password):
    session_id = str(uuid.uuid4())
    current_time = str(datetime.utcnow())
    salt = bcrypt.gensalt()
    ciphered_password = bcrypt.hashpw(str.encode(password), salt)
    db.session.add(User(username, ciphered_password, salt, session_id, current_time, "user"))
    db.session.commit()
    return "Successfully added a new user"


def database_add_video(video, title, uploader):
    db.session.add(Video(video, title, uploader))
    db.session.commit()
    return "Successfully added video!"


def database_get_videos(type_of_request, data):
    number_of_videos = 0
    response = {}
    if type_of_request == "all":
        for video in Video.query.order_by(Video.id.desc()).all():
            response[number_of_videos] = {'id': video.id,
                                          'title': video.title,
                                          'video': video.video,
                                          'uploader': video.uploader,
                                          }
            number_of_videos += 1
        return response
    elif type_of_request == "video_id":
        for video in Video.query.order_by(Video.id.desc()).filter(Video.id == data).all():
            response[number_of_videos] = {'id': video.id,
                                          'title': video.title,
                                          'video': video.video,
                                          'uploader': video.uploader,
                                          }
            number_of_videos += 1
        return response


@app.route('/')
def index():
    data = get_saved_data("data")
    session_id = data.get('session_id')
    if cookie_exists("data") and check_if_valid_session(session_id):
        return make_response(redirect(url_for('home')))
    else:
        return make_response(redirect(url_for('login')))


@app.route('/login')
def login():
    data = get_saved_data("data")
    session_id = data.get('session_id')
    if cookie_exists("data") and check_if_valid_session(session_id):
        return make_response(redirect(url_for('index')))
    else:
        return render_template('login.html')


@app.route('/logout')
def logout():
    data = get_saved_data("data")
    session_id = data.get('session_id')
    if cookie_exists("data") and check_if_valid_session(session_id):
        response = make_response(redirect(url_for('index')))
        response.set_cookie("data", json.dumps({"session_id": "invalid"}))
        return response
    else:
        return render_template('login.html')


@app.route('/login_post/<request_type>', methods=['POST'])
def login_post(request_type):
    form_response = dict(request.form.items())
    if request_type == "login":
        response = make_response(redirect(url_for('index')))
        new_session_id = make_session(form_response)
        response.set_cookie("data", json.dumps({"session_id": new_session_id}))
        return response
    elif request_type == "register":
        response = make_response(redirect(url_for('index')))
        database_add_user(form_response.get('username'), form_response.get('password'))
        new_session_id = make_session(form_response)
        response.set_cookie("data", json.dumps({"session_id": new_session_id}))
        return response


@app.route('/home')
def home():
    data = get_saved_data("data")
    session_id = data.get('session_id')
    if cookie_exists("data") and check_if_valid_session(session_id):
        return render_template('home.html',
                               database_get_videos=lambda x, y: database_get_videos(x, y)
                               )
    else:
        return make_response(redirect(url_for('index')))


@app.route('/view_video/<int:video_id>')
def view_video(video_id):
    data = get_saved_data("data")
    session_id = data.get('session_id')
    if cookie_exists("data") and check_if_valid_session(session_id):
        video = Video.query.filter(Video.id == video_id).first()
        return render_template('video_page.html',
                               video=video
                               )
    else:
        return make_response(redirect(url_for('index')))


@app.route('/search', methods=['POST'])
def search():
    form_response = dict(request.form.items())
    return form_response.get('query')


@app.route('/upload')
def upload():
    data = get_saved_data("data")
    session_id = data.get('session_id')
    if cookie_exists("data") and check_if_valid_session(session_id):
        return render_template('upload.html')
    else:
        return make_response(redirect(url_for('index')))


@app.route('/upload_post', methods=['POST'])
def upload_post():
    data = get_saved_data("data")
    session_id = data.get('session_id')
    form_response = dict(request.form.items())
    if cookie_exists("data") and check_if_valid_session(session_id):
        uploader = db_user_info("session_id", session_id).username
        title = form_response.get('title')
        video = form_response.get('video')
        database_add_video(video, title, uploader)
        return make_response(redirect(url_for('home')))
    else:
        return make_response(redirect(url_for('index')))


app.run(debug=True, host='0.0.0.0', port=8000)
