
import sqlite3


class Databaser:

    def __init__(self, db_name='database.db'):
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS videos (
                            id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            name TEXT,
                            desc TEXT,
                            likes INT,
                            dislikes INT,
                            author_name TEXT)''')

    def add_video(self, name, desc, author_name):
        self.cursor.execute('''INSERT INTO videos (name, desc, likes, dislikes, author_name) 
        VALUES (?, ?, 0, 0, ?)''', (name, desc, author_name))
        self.connection.commit()

    def get_video(self, video_id):
        self.cursor.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
        r = self.cursor.fetchone()

        if not r:
            return

        return dict(r)

    def change_video(self, video_id, name=None, desc=None, author_name=None):
        old = self.get_video(video_id)

        if name is None:
            name = old['name']
        if desc is None:
            desc = old['desc']
        if author_name is None:
            author_name = old['author_name']

        self.cursor.execute('UPDATE videos SET name = ?, desc = ?, author_name = ? WHERE id = ?', (name, desc, author_name, video_id))
        self.connection.commit()

    def like_video(self, video_id):
        self.cursor.execute('UPDATE videos SET likes = likes + 1 WHERE id =?', (video_id,))

    def dislike_video(self, video_id):
        self.cursor.execute('UPDATE videos SET dislikes = dislikes + 1 WHERE id =?', (video_id,))

    def get_videos(self):
        self.cursor.execute('SELECT * FROM videos')
        videos = self.cursor.fetchall()

        videos = list(map(dict, videos))
        videos.sort(key=lambda x: x['likes'] - x['dislikes'], reverse=True)

        return videos


if __name__ == '__main__':
    db = Databaser()
    db.add_video('Как устроен PNG', 'Описание потом придумаю', 'eleday')
    db.add_video('Автомонтаж видео на Python', 'Описание потом придумаю', 'eleday')
