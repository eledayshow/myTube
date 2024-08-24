import flask
from databaser import Databaser
from auth import hash_password, verify_password, create_token, verify_token
from exceptions import VerifyTokenError

app = flask.Flask(__name__)
db = Databaser()


@app.route('/')
def root():
    videos = db.get_videos()
    return flask.render_template('index.html', videos=videos)


@app.route('/auth')
def auth_page():
    return flask.render_template('auth.html')


@app.route('/<video_id>')
def video_page(video_id):
    video = db.get_video(video_id)

    if video is None:
        return 'Видео не найдено'

    return flask.render_template('video_page.html', video=video)


@app.route('/<video_id>/like', methods=['POST'])
def like_video(video_id):
    token = flask.request.cookies.get('token')
    try:
        verify_token(token)
    except VerifyTokenError:
        return 'Unauthorized', 401
    video_id = int(video_id)
    db.like_video(video_id)
    return 'ok'


@app.route('/<video_id>/dislike', methods=['POST'])
def dislike_video(video_id):
    token = flask.request.cookies.get('token')
    try:
        verify_token(token)
    except VerifyTokenError:
        return 'Unauthorized', 401
    video_id = int(video_id)
    db.dislike_video(video_id)
    return 'ok'


@app.route('/auth/register', methods=['POST'])
def register():
    name = flask.request.args.get('name', default='', type=str)
    password = flask.request.args.get('password', default='', type=str)
    db.add_user(name, hash_password(password))
    return 'ok'


@app.route('/auth/auth', methods=['POST'])
def auth():
    name = flask.request.args.get('name', default='', type=str)
    password = flask.request.args.get('password', default='', type=str)
    user = db.get_user_by_name(name)
    if user is None:
        return 'name not found', 400
    if not verify_password(password, user["password_hash"]):
        return 'incorrect password', 400
    return create_token({'id': user["id"]}), 200


if __name__ == '__main__':
    app.run(debug=True)
