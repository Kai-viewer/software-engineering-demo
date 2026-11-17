import sqlite3
import unittest
from fastapi.testclient import TestClient
from main import app, hash_password
from db import get_db

class Cursor:
    def __init__(self, cursor):
        self.cursor, self.rowcount = cursor, cursor.rowcount
    async def fetchone(self): return self.cursor.fetchone()
    async def fetchall(self): return self.cursor.fetchall()

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(':memory:', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript('''
            CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, password_hash TEXT, name TEXT, role TEXT);
            CREATE TABLE submissions (id INTEGER PRIMARY KEY, author_id INTEGER, category TEXT, title TEXT, content TEXT, status TEXT);
        ''')
    async def execute(self, sql, params=()): return Cursor(self.conn.execute(sql.replace('%s', '?'), params))
    async def commit(self): self.conn.commit()

class WorkflowTest(unittest.TestCase):
    def setUp(self):
        self.db = Database()
        for username, name, role in [('author', '作者', 'author'), ('other', '其他作者', 'author'), ('editor', '編輯', 'editor')]:
            self.db.conn.execute('INSERT INTO users (username, password_hash, name, role) VALUES (?, ?, ?, ?)', (username, hash_password('pass1234'), name, role))
        self.db.conn.commit()
        async def database(): yield self.db
        app.dependency_overrides[get_db] = database
        self.client = TestClient(app)
    def tearDown(self):
        self.client.close()
        self.db.conn.close()
        app.dependency_overrides.clear()
    def login(self, username):
        return self.client.post('/login', data={'username': username, 'password': 'pass1234'}, follow_redirects=False)
    def test_submission_review_flow_and_permissions(self):
        self.assertEqual(self.client.get('/author', follow_redirects=False).status_code, 303)
        self.assertEqual(self.login('author').status_code, 303)
        self.assertEqual(self.client.post('/author/new', data={'category': '小說', 'title': '第一篇', 'content': '內容'}, follow_redirects=False).status_code, 303)
        self.assertIn('第一篇', self.client.get('/author').text)
        self.client.post('/logout')
        self.login('other')
        self.assertEqual(self.client.post('/author/1/submit').status_code, 404)
        self.client.post('/logout')
        self.login('author')
        self.assertEqual(self.client.post('/author/1/submit', follow_redirects=False).status_code, 303)
        self.assertEqual(self.client.post('/author/1/delete').status_code, 404)
        self.client.post('/logout')
        self.login('editor')
        self.assertIn('第一篇', self.client.get('/editor').text)
        self.assertIn('內容', self.client.get('/editor/1').text)
        self.assertEqual(self.client.post('/editor/1/return', follow_redirects=False).status_code, 303)
        self.assertEqual(self.client.post('/editor/1/approve').status_code, 404)
        self.client.post('/logout')
        self.login('author')
        self.assertEqual(self.client.post('/author/1/edit', data={'category': '小說', 'title': '修改後', 'content': '新內容'}, follow_redirects=False).status_code, 303)
        self.client.post('/author/1/submit')
        self.client.post('/logout')
        self.login('editor')
        self.assertEqual(self.client.post('/editor/1/approve', follow_redirects=False).status_code, 303)
        self.client.post('/logout')
        self.login('author')
        self.assertIn('已通過', self.client.get('/author').text)
        self.assertEqual(self.client.post('/author/1/delete').status_code, 404)
    def test_login_and_role_restrictions(self):
        self.assertEqual(self.client.post('/login', data={'username': 'author', 'password': 'wrong'}).status_code, 401)
        self.login('author')
        self.assertEqual(self.client.get('/editor').status_code, 403)

if __name__ == '__main__': unittest.main()
