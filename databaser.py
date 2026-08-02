
import sqlite3
import bcrypt


class Databaser:

    def __init__(self, db_name='database.db'):
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        
        # Создаем таблицы
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS videos (
                            id INTEGER PRIMARY KEY AUTOINCREMENT, 
                            name TEXT,
                            desc TEXT,
                            likes INT DEFAULT 0,
                            dislikes INT DEFAULT 0,
                            views INT DEFAULT 0,
                            author_name TEXT,
                            author_id INTEGER,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            username TEXT UNIQUE NOT NULL,
                            password TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS reactions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            video_id INTEGER NOT NULL,
                            reaction TEXT NOT NULL,
                            UNIQUE(user_id, video_id),
                            FOREIGN KEY (user_id) REFERENCES users(id),
                            FOREIGN KEY (video_id) REFERENCES videos(id))''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS comments (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER NOT NULL,
                            video_id INTEGER NOT NULL,
                            text TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users(id),
                            FOREIGN KEY (video_id) REFERENCES videos(id))''')
        
        self.cursor.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            subscriber_id INTEGER NOT NULL,
                            channel_id INTEGER NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(subscriber_id, channel_id),
                            FOREIGN KEY (subscriber_id) REFERENCES users(id),
                            FOREIGN KEY (channel_id) REFERENCES users(id))''')
        
        self.connection.commit()

    def add_video(self, name, desc, author_name, author_id):
        self.cursor.execute('''INSERT INTO videos (name, desc, likes, dislikes, views, author_name, author_id) 
        VALUES (?, ?, 0, 0, 0, ?, ?)''', (name, desc, author_name, author_id))
        self.connection.commit()
        return self.cursor.lastrowid

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

    def increment_view_count(self, video_id):
        self.cursor.execute('UPDATE videos SET views = views + 1 WHERE id = ?', (video_id,))
        self.connection.commit()

    def like_video(self, video_id, user_id):
        current_reaction = self.get_user_reaction(user_id, video_id)
        if current_reaction == 'like':
            self.cursor.execute('DELETE FROM reactions WHERE user_id = ? AND video_id = ?', (user_id, video_id))
            self.cursor.execute('UPDATE videos SET likes = likes - 1 WHERE id = ?', (video_id,))
        elif current_reaction == 'dislike':
            self.cursor.execute('UPDATE reactions SET reaction = ? WHERE user_id = ? AND video_id = ?', 
                              ('like', user_id, video_id))
            self.cursor.execute('UPDATE videos SET dislikes = dislikes - 1, likes = likes + 1 WHERE id = ?', (video_id,))
        else:
            self.cursor.execute('INSERT INTO reactions (user_id, video_id, reaction) VALUES (?, ?, ?)', 
                              (user_id, video_id, 'like'))
            self.cursor.execute('UPDATE videos SET likes = likes + 1 WHERE id = ?', (video_id,))
        self.connection.commit()

    def dislike_video(self, video_id, user_id):
        current_reaction = self.get_user_reaction(user_id, video_id)
        if current_reaction == 'dislike':
            self.cursor.execute('DELETE FROM reactions WHERE user_id = ? AND video_id = ?', (user_id, video_id))
            self.cursor.execute('UPDATE videos SET dislikes = dislikes - 1 WHERE id = ?', (video_id,))
        elif current_reaction == 'like':
            self.cursor.execute('UPDATE reactions SET reaction = ? WHERE user_id = ? AND video_id = ?', 
                              ('dislike', user_id, video_id))
            self.cursor.execute('UPDATE videos SET likes = likes - 1, dislikes = dislikes + 1 WHERE id = ?', (video_id,))
        else:
            self.cursor.execute('INSERT INTO reactions (user_id, video_id, reaction) VALUES (?, ?, ?)', 
                              (user_id, video_id, 'dislike'))
            self.cursor.execute('UPDATE videos SET dislikes = dislikes + 1 WHERE id = ?', (video_id,))
        self.connection.commit()
    
    def get_user_reaction(self, user_id, video_id):
        self.cursor.execute('SELECT reaction FROM reactions WHERE user_id = ? AND video_id = ?', 
                          (user_id, video_id))
        r = self.cursor.fetchone()
        return r['reaction'] if r else None

    def get_videos(self, search_query=None):
        if search_query:
            search_pattern = f'%{search_query}%'
            self.cursor.execute('SELECT * FROM videos WHERE name LIKE ? OR desc LIKE ? ORDER BY views DESC', 
                              (search_pattern, search_pattern))
        else:
            self.cursor.execute('SELECT * FROM videos ORDER BY views DESC')
        videos = self.cursor.fetchall()
        return list(map(dict, videos))

    def create_user(self, username, password):
        try:
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            self.cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                              (username, hashed.decode('utf-8')))
            self.connection.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
    
    def get_user_by_username(self, username):
        self.cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        r = self.cursor.fetchone()
        return dict(r) if r else None
    
    def get_user_by_id(self, user_id):
        self.cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        r = self.cursor.fetchone()
        return dict(r) if r else None
    
    def verify_password(self, password, hashed):
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    # Комментарии
    def add_comment(self, user_id, video_id, text):
        self.cursor.execute('INSERT INTO comments (user_id, video_id, text) VALUES (?, ?, ?)', 
                          (user_id, video_id, text))
        self.connection.commit()
        return self.cursor.lastrowid

    def get_comments(self, video_id):
        self.cursor.execute('''
            SELECT c.*, u.username 
            FROM comments c 
            JOIN users u ON c.user_id = u.id 
            WHERE c.video_id = ? 
            ORDER BY c.created_at ASC
        ''', (video_id,))
        return list(map(dict, self.cursor.fetchall()))

    def delete_comment(self, comment_id, user_id):
        self.cursor.execute('DELETE FROM comments WHERE id = ? AND user_id = ?', (comment_id, user_id))
        self.connection.commit()
        return self.cursor.rowcount > 0

    # Профиль и подписки
    def get_user_videos(self, user_id):
        self.cursor.execute('SELECT * FROM videos WHERE author_id = ? ORDER BY created_at DESC', (user_id,))
        return list(map(dict, self.cursor.fetchall()))

    def get_user_stats(self, user_id):
        self.cursor.execute('SELECT COUNT(*) as video_count, COALESCE(SUM(views), 0) as total_views FROM videos WHERE author_id = ?', (user_id,))
        stats = dict(self.cursor.fetchone())
        stats['subscriber_count'] = self.get_subscriber_count(user_id)
        stats['subscription_count'] = self.get_subscription_count(user_id)
        return stats

    def subscribe(self, subscriber_id, channel_id):
        if subscriber_id == channel_id:
            return False
        try:
            self.cursor.execute('INSERT INTO subscriptions (subscriber_id, channel_id) VALUES (?, ?)', 
                              (subscriber_id, channel_id))
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def unsubscribe(self, subscriber_id, channel_id):
        self.cursor.execute('DELETE FROM subscriptions WHERE subscriber_id = ? AND channel_id = ?', 
                          (subscriber_id, channel_id))
        self.connection.commit()
        return self.cursor.rowcount > 0

    def is_subscribed(self, subscriber_id, channel_id):
        self.cursor.execute('SELECT 1 FROM subscriptions WHERE subscriber_id = ? AND channel_id = ?', 
                          (subscriber_id, channel_id))
        return self.cursor.fetchone() is not None

    def get_subscriber_count(self, user_id):
        self.cursor.execute('SELECT COUNT(*) as count FROM subscriptions WHERE channel_id = ?', (user_id,))
        return self.cursor.fetchone()['count']

    def get_subscription_count(self, user_id):
        self.cursor.execute('SELECT COUNT(*) as count FROM subscriptions WHERE subscriber_id = ?', (user_id,))
        return self.cursor.fetchone()['count']

    def delete_video(self, video_id, user_id):
        """Удалить видео если пользователь владелец"""
        self.cursor.execute('DELETE FROM videos WHERE id = ? AND author_id = ?', (video_id, user_id))
        self.connection.commit()
        return self.cursor.rowcount > 0

    def update_video(self, video_id, user_id, name=None, desc=None):
        """Обновить информацию о видео"""
        video = self.get_video(video_id)
        if not video or video['author_id'] != user_id:
            return False
        
        if name is not None:
            self.cursor.execute('UPDATE videos SET name = ? WHERE id = ?', (name, video_id))
        if desc is not None:
            self.cursor.execute('UPDATE videos SET desc = ? WHERE id = ?', (desc, video_id))
        
        self.connection.commit()
        return True


if __name__ == '__main__':
    db = Databaser()
    db.add_video('Как устроен PNG', 'Описание потом придумаю', 'eleday', 1)
    db.add_video('Автомонтаж видео на Python', 'Описание потом придумаю', 'eleday', 1)
