import unittest
import json
from app import create_app
from unittest.mock import patch

class TestAPI(unittest.TestCase):
    def setUp(self):
        """Set up test client and app context"""
        self.app = create_app('testing')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
    
    def tearDown(self):
        """Clean up after tests"""
        self.app_context.pop()
    
    def test_health_check(self):
        """Test the health check endpoint"""
        response = self.client.get('/health')
        data = json.loads(response.data)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['status'], 'healthy')
        self.assertEqual(data['service'], 'dynamic-sql-generator')
    
    def test_list_templates(self):
        """Test the templates listing endpoint"""
        with patch('app.api.routes.SQL_TEMPLATES', {'template1': 'SQL1', 'template2': 'SQL2'}):
            response = self.client.get('/api/templates')
            data = json.loads(response.data)
            
            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['count'], 2)
            self.assertIn('template1', data['templates'])
            self.assertIn('template2', data['templates'])
    
    def test_query_with_valid_input(self):
        """Test the query endpoint with valid input"""
        # Mock the sql_service.execute_dynamic_query function
        with patch('app.api.routes.sql_service.execute_dynamic_query') as mock_execute:
            # Set up the mock to return a result
            mock_execute.return_value = {
                "data": [{"id": 1, "name": "Test"}],
                "row_count": 1,
                "execution_time_ms": 5
            }
            
            # Send a request to the endpoint
            response = self.client.post(
                '/api/query',
                data=json.dumps({
                    'biz_type': 'customer_analysis',
                    'parameters': {'customer_id': 123}
                }),
                content_type='application/json'
            )
            
            # Check the response
            data = json.loads(response.data)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['row_count'], 1)
            self.assertEqual(len(data['data']), 1)
            self.assertEqual(data['data'][0]['id'], 1)
            
            # Check that the mock was called with the correct parameters
            mock_execute.assert_called_once_with('customer_analysis', {'customer_id': 123})
    
    def test_query_with_invalid_input(self):
        """Test the query endpoint with invalid input"""
        # Test with missing biz_type
        response = self.client.post(
            '/api/query',
            data=json.dumps({
                'parameters': {'customer_id': 123}
            }),
            content_type='application/json'
        )
        
        # Check the response
        data = json.loads(response.data)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(data['status'], 'error')
        self.assertIn('code', data)
    
    def test_query_with_invalid_biz_type(self):
        """Test the query endpoint with an invalid business type"""
        # Mock the sql_service.execute_dynamic_query function to raise a ValueError
        with patch('app.api.routes.sql_service.execute_dynamic_query') as mock_execute:
            # Set up the mock to raise a ValueError
            mock_execute.side_effect = ValueError("Unknown business type: invalid_type")
            
            # Send a request to the endpoint
            response = self.client.post(
                '/api/query',
                data=json.dumps({
                    'biz_type': 'invalid_type',
                    'parameters': {'customer_id': 123}
                }),
                content_type='application/json'
            )
            
            # Check the response
            data = json.loads(response.data)
            self.assertEqual(response.status_code, 400)
            self.assertEqual(data['status'], 'error')
            self.assertEqual(data['code'], 'VALUE_ERROR')
            self.assertIn('Unknown business type', data['error'])

if __name__ == '__main__':
    unittest.main() 