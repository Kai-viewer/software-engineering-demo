import unittest
from test_workflow import WorkflowTest

class RefreshTest(WorkflowTest):
    def test_refresh_and_other_app_cookie(self):
        self.login('author')
        self.client.cookies.set('session', 'another-application-value', domain='testserver.local', path='/')
        for _ in range(3):
            response = self.client.get('/author/new')
            self.assertEqual(response.status_code, 200)
            self.assertIn('新增投稿', response.text)
            self.assertEqual(response.headers.get('cache-control'), 'no-store')

    def test_wrong_role_shows_readable_error_page(self):
        self.login('editor')
        response = self.client.get('/author/new')
        self.assertEqual(response.status_code, 403)
        self.assertIn('text/html', response.headers['content-type'])
        self.assertIn('沒有權限', response.text)
        self.assertIn('返回', response.text)

if __name__ == '__main__': unittest.main()
