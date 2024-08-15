import flask
from databaser import Databaser


app = flask.Flask(__name__)
db = Databaser()


@app.route('/')
def root():
    videos = db.get_videos()
    return flask.render_template('index.html', videos=videos)


@app.route('/<video_id>')
def video_page(video_id):
    video = db.get_video(video_id)

    if video is None:
        return 'Видео не найдено'

    return flask.render_template('video_page.html', video=video)


@app.route('/<video_id>/like', methods=['POST'])
def like_video(video_id):
    video_id = int(video_id)
    db.like_video(video_id)
    return 'ok'

@app.route('/<video_id>/dislike', methods=['POST'])
def dislike_video(video_id):
    video_id = int(video_id)
    db.dislike_video(video_id)
    return 'ok'


if __name__ == '__main__':
    app.run(debug=True)