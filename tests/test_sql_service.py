import unittest
from app.services.sql_service import SQLService
from unittest.mock import patch, MagicMock

class TestSQLService(unittest.TestCase):
    def test_process_template_with_valid_biz_type(self):
        """Test that process_template works with a valid business type"""
        # Mock the get_template function
        with patch('app.services.sql_service.get_template') as mock_get_template:
            # Set up the mock to return a template
            mock_get_template.return_value = "SELECT * FROM users WHERE user_id = :user_id"
            
            # Call the function
            result = SQLService.process_template('user_lookup', {'user_id': 123})
            
            # Check the result
            self.assertEqual(result, "SELECT * FROM users WHERE user_id = :user_id")
            
            # Check that get_template was called with the correct business type
            mock_get_template.assert_called_once_with('user_lookup')
    
    def test_process_template_with_invalid_biz_type(self):
        """Test that process_template raises an error with an invalid business type"""
        # Mock the get_template function
        with patch('app.services.sql_service.get_template') as mock_get_template:
            # Set up the mock to return None (template not found)
            mock_get_template.return_value = None
            
            # Check that the function raises a ValueError
            with self.assertRaises(ValueError):
                SQLService.process_template('invalid_biz_type', {})
    
    def test_execute_dynamic_query(self):
        """Test that execute_dynamic_query works with valid inputs"""
        # Mock process_template and db.execute_query
        with patch('app.services.sql_service.SQLService.process_template') as mock_process_template, \
             patch('app.services.sql_service.db.execute_query') as mock_execute_query:
            
            # Set up the mocks
            mock_process_template.return_value = "SELECT * FROM orders WHERE customer_id = :customer_id"
            mock_execute_query.return_value = {
                "data": [{"order_id": 1, "amount": 100}],
                "row_count": 1,
                "execution_time_ms": 5
            }
            
            # Call the function
            result = SQLService.execute_dynamic_query('order_lookup', {'customer_id': 123})
            
            # Check the result
            self.assertEqual(result["row_count"], 1)
            self.assertEqual(len(result["data"]), 1)
            self.assertEqual(result["data"][0]["order_id"], 1)
            
            # Check that the mocks were called with the correct parameters
            mock_process_template.assert_called_once_with('order_lookup', {'customer_id': 123})
            mock_execute_query.assert_called_once_with(
                "SELECT * FROM orders WHERE customer_id = :customer_id", 
                {'customer_id': 123}
            )

if __name__ == '__main__':
    unittest.main() 