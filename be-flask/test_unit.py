# tests/test_unit.py
import unittest
from app import app


class TestApp(unittest.TestCase):

    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_home_route(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'"message":"Success"', response.data)
        self.assertIn(b'"data":', response.data)
        self.assertIn(b'"ip":', response.data)

    def test_ip_in_response(self):
        response = self.app.get('/')
        data = response.get_json()
        self.assertEqual(data['message'], 'Success')
        self.assertIn('data', data)
        self.assertIn('ip', data['data'])
        self.assertIn('user_agent', data['data'])
        self.assertIn('method', data['data'])


if __name__ == '__main__':
    unittest.main()
