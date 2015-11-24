from flask import Flask, render_template, redirect, url_for, request, make_response, jsonify
from flask.ext.sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import bcrypt, uuid, json, random

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


class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    video_id = db.Column(db.Integer)
    tag = db.Column(db.String())

    def __init__(self, video_id, tag):
        self.video_id = video_id
        self.tag = tag

    def __repr__(self):
        return '<Tag %r>' % self.id


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


def database_add_tag(video_id, tag):
    db.session.add(Tag(video_id, tag))
    db.session.commit()
    return 'Successfully added tag!'


# TODO: Add likes, dislikes, views, and descriptions to video tables
def database_get_videos(type_of_request, data):
    number_of_videos = 0
    response = {}
    fake_description = "Donec at sollicitudin nisi, vitae tristique urna. Suspendisse nisi odio, maximus ut vehicula elementum, tempus ac magna. In at massa lectus. Nunc id tellus velit. Morbi nec interdum tortor, id consequat mi. Phasellus ut lectus ac odio fringilla scelerisque id at diam. Ut egestas accumsan nunc, eget pellentesque velit placerat eleifend. Nunc felis eros, vestibulum a ligula vel, euismod pharetra nibh. Vestibulum faucibus porta nulla, a ornare mi tincidunt semper. Nunc facilisis dui felis, eu iaculis ligula interdum eu."
    if type_of_request == "all":
        for video in Video.query.order_by(Video.id.desc()).all():
            response[number_of_videos] = {'id': video.id,
                                          'title': video.title,
                                          'video': video.video,
                                          'uploader': video.uploader,
                                          'description': fake_description,
                                          'likes': 0,
                                          'dislikes': 0,
                                          'views': 0
                                          }
            number_of_videos += 1
        return response
    elif type_of_request == "video_id":
        for video in Video.query.order_by(Video.id.desc()).filter(Video.id == data).all():
            response[number_of_videos] = {'id': video.id,
                                          'title': video.title,
                                          'video': video.video,
                                          'uploader': video.uploader,
                                          'description': fake_description,
                                          'likes': 0,
                                          'dislikes': 0,
                                          'views': 0
                                          }
            number_of_videos += 1
        return response
    elif type_of_request == "query":
        query = data.lower().split(" ")

        for video in Video.query.order_by(Video.id.desc()).filter(Tag.video_id == Video.id).filter(
                Tag.tag.in_(query)).all():
            response[number_of_videos] = {'id': video.id,
                                          'title': video.title,
                                          'video': video.video,
                                          'uploader': video.uploader,
                                          'description': fake_description,
                                          'likes': 0,
                                          'dislikes': 0,
                                          'views': 0,
                                          'weight': 0
                                          }
            tags = []
            for tag in Tag.query.filter(Tag.video_id == video.id).all():
                tags.append(tag.tag)
            # Updates the weight by how many matches there are between the query and tags
            for tag in query:
                response[number_of_videos]['weight'] += tags.count(tag)
            number_of_videos += 1
        # Sorts videos by weight/search relevancy
        for i in range(1, len(response)):
            if response[i - 1]['weight'] < response[i]['weight']:
                response[i - 1], response[i] = response[i], response[i - 1]
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
    logged_in = False
    if cookie_exists("data") and check_if_valid_session(session_id):
        logged_in = True
    # video = Video.query.filter(Video.id == video_id).first()
    video = {}
    for vid in database_get_videos("video_id", video_id).items():
        video = vid[1]
    return render_template('video_page.html',
                           video=video,
                           database_get_videos=lambda x, y: database_get_videos(x, y),
                           logged_in=logged_in
                           )


@app.route('/search', methods=['POST'])
def search():
    form_response = dict(request.form.items())
    data = get_saved_data("data")
    session_id = data.get('session_id')
    if cookie_exists("data") and check_if_valid_session(session_id):
        return make_response(redirect(url_for('search_results', query=form_response.get('query'))))
    else:
        return make_response(redirect(url_for('index')))


@app.route('/search_results/<query>')
def search_results(query):
    data = get_saved_data("data")
    session_id = data.get('session_id')
    if cookie_exists("data") and check_if_valid_session(session_id):
        return render_template('search_result.html',
                               query=query,
                               database_get_videos=lambda x, y: database_get_videos(x, y)
                               )
    else:
        return make_response(redirect(url_for('index')))


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
        video = video[:len(video) - 4]
        video += "preview"
        database_add_video(video, title, uploader)
        uploaded_video = Video.query.order_by(Video.id.desc()).filter(Video.title == title).filter(
            Video.video == video).filter(Video.uploader == uploader).first()
        tags = form_response.get('tags').lower().split(" ")
        for tag in tags:
            database_add_tag(uploaded_video.id, tag)
        return make_response(redirect(url_for('home')))
    else:
        return make_response(redirect(url_for('index')))


app.randomyear = 0


def randomyear():
    app.randomyear += 1
    return app.randomyear


app.yeardata = []

app.list_of_stuff = []


def sort_once():
    def sort_in_eight():
        length = int(len(app.list_of_stuff) / 8)
        first_quarter = app.list_of_stuff[:length * 1]
        second_quarter = app.list_of_stuff[length * 1:length * 2]
        third_quarter = app.list_of_stuff[length * 2:length * 3]
        fourth_quarter = app.list_of_stuff[length * 3:length * 4]
        fifth_quarter = app.list_of_stuff[length * 4:length * 5]
        sixth_quarter = app.list_of_stuff[length * 5:length * 6]
        seventh_quarter = app.list_of_stuff[length * 6:length * 7]
        eighth_quarter = app.list_of_stuff[length * 7:length * 8]
        in_order = True
        for i in range(1, len(first_quarter)):
            if first_quarter[i - 1][1] < first_quarter[i][1]:
                in_order = False
                first_quarter[i - 1][1], first_quarter[i][1] = first_quarter[i][1], first_quarter[i - 1][1]
        for i in range(1, len(second_quarter)):
            if second_quarter[i - 1][1] < second_quarter[i][1]:
                in_order = False
                second_quarter[i - 1][1], second_quarter[i][1] = second_quarter[i][1], second_quarter[i - 1][1]
        for i in range(1, len(third_quarter)):
            if third_quarter[i - 1][1] < third_quarter[i][1]:
                in_order = False
                third_quarter[i - 1][1], third_quarter[i][1] = third_quarter[i][1], third_quarter[i - 1][1]
        for i in range(1, len(fourth_quarter)):
            if fourth_quarter[i - 1][1] < fourth_quarter[i][1]:
                in_order = False
                fourth_quarter[i - 1][1], fourth_quarter[i][1] = fourth_quarter[i][1], fourth_quarter[i - 1][1]
        for i in range(1, len(fifth_quarter)):
            if fifth_quarter[i - 1][1] < fifth_quarter[i][1]:
                in_order = False
                fifth_quarter[i - 1][1], fifth_quarter[i][1] = fifth_quarter[i][1], fifth_quarter[i - 1][1]
        for i in range(1, len(sixth_quarter)):
            if sixth_quarter[i - 1][1] < sixth_quarter[i][1]:
                in_order = False
                sixth_quarter[i - 1][1], sixth_quarter[i][1] = sixth_quarter[i][1], sixth_quarter[i - 1][1]
        for i in range(1, len(seventh_quarter)):
            if seventh_quarter[i - 1][1] < seventh_quarter[i][1]:
                in_order = False
                seventh_quarter[i - 1][1], seventh_quarter[i][1] = seventh_quarter[i][1], seventh_quarter[i - 1][1]
        for i in range(1, len(eighth_quarter)):
            if eighth_quarter[i - 1][1] < eighth_quarter[i][1]:
                in_order = False
                eighth_quarter[i - 1][1], eighth_quarter[i][1] = eighth_quarter[i][1], eighth_quarter[i - 1][1]
        app.list_of_stuff = []
        for i in first_quarter:
            app.list_of_stuff.append(i)
        for i in second_quarter:
            app.list_of_stuff.append(i)
        for i in third_quarter:
            app.list_of_stuff.append(i)
        for i in fourth_quarter:
            app.list_of_stuff.append(i)
        for i in fifth_quarter:
            app.list_of_stuff.append(i)
        for i in sixth_quarter:
            app.list_of_stuff.append(i)
        for i in seventh_quarter:
            app.list_of_stuff.append(i)
        for i in eighth_quarter:
            app.list_of_stuff.append(i)
        return in_order

    def sort_in_four():
        length = int(len(app.list_of_stuff) / 4)
        first_quarter = app.list_of_stuff[:length * 1]
        second_quarter = app.list_of_stuff[length * 1:length * 2]
        third_quarter = app.list_of_stuff[length * 2:length * 3]
        fourth_quarter = app.list_of_stuff[length * 3:length * 4]
        in_order = True
        for i in range(1, len(first_quarter)):
            if first_quarter[i - 1][1] < first_quarter[i][1]:
                in_order = False
                first_quarter[i - 1][1], first_quarter[i][1] = first_quarter[i][1], first_quarter[i - 1][1]
        for i in range(1, len(second_quarter)):
            if second_quarter[i - 1][1] < second_quarter[i][1]:
                in_order = False
                second_quarter[i - 1][1], second_quarter[i][1] = second_quarter[i][1], second_quarter[i - 1][1]
        for i in range(1, len(third_quarter)):
            if third_quarter[i - 1][1] < third_quarter[i][1]:
                in_order = False
                third_quarter[i - 1][1], third_quarter[i][1] = third_quarter[i][1], third_quarter[i - 1][1]
        for i in range(1, len(fourth_quarter)):
            if fourth_quarter[i - 1][1] < fourth_quarter[i][1]:
                in_order = False
                fourth_quarter[i - 1][1], fourth_quarter[i][1] = fourth_quarter[i][1], fourth_quarter[i - 1][1]
        app.list_of_stuff = []
        for i in first_quarter:
            app.list_of_stuff.append(i)
        for i in second_quarter:
            app.list_of_stuff.append(i)
        for i in third_quarter:
            app.list_of_stuff.append(i)
        for i in fourth_quarter:
            app.list_of_stuff.append(i)
        return in_order

    def sort_in_two():
        length = int(len(app.list_of_stuff) / 2)
        first_half = app.list_of_stuff[:length * 1]
        second_half = app.list_of_stuff[length * 1:length * 2]
        in_order = True
        for i in range(1, len(first_half)):
            if first_half[i - 1][1] < first_half[i][1]:
                in_order = False
                first_half[i - 1][1], first_half[i][1] = first_half[i][1], first_half[i - 1][1]
        for i in range(1, len(second_half)):
            if second_half[i - 1][1] < second_half[i][1]:
                in_order = False
                second_half[i - 1][1], second_half[i][1] = second_half[i][1], second_half[i - 1][1]
        app.list_of_stuff = []
        for i in first_half:
            app.list_of_stuff.append(i)
        for i in second_half:
            app.list_of_stuff.append(i)
        return in_order

    def complete_sort():
        status = True
        for i in range(1, len(app.list_of_stuff)):
            if app.list_of_stuff[i - 1][1] < app.list_of_stuff[i][1]:
                status = False
                app.list_of_stuff[i - 1][1], app.list_of_stuff[i][1] = app.list_of_stuff[i][1], app.list_of_stuff[i - 1][1]
        return status

    if sort_in_eight() is True:
        if sort_in_four() is True:
            if complete_sort() is True:
                generate_new_dataset()
    return


@app.route('/generate_new_dataset')
def generate_new_dataset():
    app.list_of_stuff = []
    for i in range(0, 300):
        app.list_of_stuff.append([i, random.random() * 1000])
    return make_response(redirect(url_for('bar_graph')))


@app.route('/live_stats')
def live_stats():
    return render_template('ajax/index.html')


@app.route('/ajax')
def bar_graph():
    return render_template('ajax.html')


@app.route('/sort_example')
def sort_example():
    sort_once()
    response = {
        "label": "Sorting Example",
        "data": app.list_of_stuff
    }
    return jsonify(**response)


@app.route('/random_number')
def random_number():
    app.yeardata.append([randomyear(), random.random() * 1000])
    response = {
        "label": "Europe (EU27)",
        "data": app.yeardata
    }
    print(app.randomyear)
    return jsonify(**response)


app.run(debug=True, host='0.0.0.0', port=8000)
