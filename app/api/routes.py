from flask import Blueprint, request, jsonify, current_app
from app.services.sql_service import sql_service
from app.templates.sql_templates import list_templates, load_templates_from_file
import logging
import time
import datetime
from marshmallow import Schema, fields, validate, ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

def init_bp(app):
    """Initialize the blueprint with the app context"""
    with app.app_context():
        load_templates_from_file()

# Define validation schema
class QueryRequestSchema(Schema):
    biz_type = fields.String(required=True, validate=validate.Length(min=1))
    parameters = fields.Dict(required=True)
    group_parameters = fields.String(required=False)
    sort_parameters = fields.List(fields.Dict(), required=False)

@api_bp.route('/query', methods=['POST'])
def query():
    """
    API endpoint to handle dynamic SQL queries
    
    Request body should be a JSON object with:
    - biz_type: String identifying the business type / SQL template to use
    - parameters: Dictionary of parameters to fill into the template
    
    Returns:
        JSON response with query results or error message
    """
    start_time = time.time()
    
    # Get JSON data from request
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'error': 'No JSON data provided', 'code': 'INVALID_INPUT'}), 400
            
        # Validate input
        schema = QueryRequestSchema()
        validated_data = schema.load(data)
        
        biz_type = validated_data['biz_type']
        parameters = validated_data['parameters']
        
        # Get optional group_parameters and sort_parameters
        group_parameters = validated_data.get('group_parameters')
        sort_parameters = validated_data.get('sort_parameters')
        
        logger.info(f"Received query request for business type: {biz_type}")
        
        # Process date strings into proper format if needed
        for key, value in parameters.items():
            if isinstance(value, str) and key.endswith(('_date', 'date_', 'date')):
                try:
                    # Try to parse and standardize date format
                    date_obj = datetime.datetime.strptime(value, '%Y-%m-%d')
                    parameters[key] = date_obj.strftime('%Y-%m-%d')
                except ValueError:
                    # If it's not a standard format, leave it unchanged
                    pass
        
        # Execute query
        result = sql_service.execute_dynamic_query(
            biz_type, 
            parameters, 
            group_parameters=group_parameters, 
            sort_parameters=sort_parameters
        )
        
        # Build response
        total_time = int((time.time() - start_time) * 1000)  # Total API time in ms
        response = {
            'status': 'success',
            'data': result['data'],
            'row_count': result['row_count'],
            'db_execution_time_ms': result['execution_time_ms'],
            'template_time_ms': result.get('template_time_ms', 0),
            'total_time_ms': total_time,
            'cache_hit': result.get('cache_info', {}).get('hits', 0) > 0
        }
        
        logger.info(f"Query complete. Returned {result['row_count']} rows in {total_time}ms")
        return jsonify(response)
    
    except ValidationError as e:
        logger.warning(f"Input validation error: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e), 'code': 'VALIDATION_ERROR'}), 400
    
    except ValueError as e:
        logger.warning(f"Value error: {str(e)}")
        return jsonify({'status': 'error', 'error': str(e), 'code': 'VALUE_ERROR'}), 400
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        if current_app.debug:
            # In debug mode, include the full error details
            return jsonify({'status': 'error', 'error': str(e), 'code': 'SERVER_ERROR'}), 500
        else:
            # In production, return a generic error message
            return jsonify({'status': 'error', 'error': 'An unexpected error occurred', 'code': 'SERVER_ERROR'}), 500

@api_bp.route('/templates', methods=['GET'])
def get_templates():
    """
    API endpoint to list available SQL templates/business types
    
    Returns:
        JSON list of available business types with descriptions
    """
    templates = list_templates()
    return jsonify({
        'status': 'success',
        'templates': templates,
        'count': len(templates)
    })

@api_bp.route('/cache/stats', methods=['GET'])
def cache_stats():
    """
    API endpoint to get SQL template cache statistics
    
    Returns:
        JSON object with cache statistics
    """
    stats = sql_service.get_cache_stats()
    return jsonify({
        'status': 'success',
        'cache_stats': stats
    })

@api_bp.route('/cache/clear', methods=['POST'])
def clear_cache():
    """
    API endpoint to clear the SQL template cache
    
    Returns:
        JSON confirmation message
    """
    sql_service.clear_cache()
    return jsonify({
        'status': 'success',
        'message': 'Cache cleared successfully'
    })

@api_bp.route('/sample/<biz_type>', methods=['GET'])
def get_sample_request(biz_type):
    """
    API endpoint to get a sample request for a specific business type
    
    Returns:
        JSON sample request object
    """
    from app.templates.sql_templates import get_template_metadata
    
    metadata = get_template_metadata(biz_type)
    if not metadata:
        return jsonify({
            'status': 'error',
            'error': f'Unknown business type: {biz_type}',
            'code': 'UNKNOWN_BIZ_TYPE'
        }), 404
    
    # Create sample parameters based on metadata
    sample_params = {}
    for param in metadata.get('required_params', []):
        param_type = metadata.get('param_types', {}).get(param, 'string')
        
        if param_type == 'integer':
            sample_params[param] = 1
        elif param_type == 'date':
            sample_params[param] = '2023-01-01'
        elif param_type == 'boolean':
            sample_params[param] = True
        else:
            sample_params[param] = 'sample_value'
    
    # Add first optional param as example
    if metadata.get('optional_params'):
        opt_param = metadata['optional_params'][0]
        param_type = metadata.get('param_types', {}).get(opt_param, 'string')
        
        if param_type == 'integer':
            sample_params[opt_param] = 100
        elif param_type == 'date':
            sample_params[opt_param] = '2023-12-31'
        elif param_type == 'boolean':
            sample_params[opt_param] = True
        else:
            sample_params[opt_param] = 'optional_value'
    
    sample_request = {
        'biz_type': biz_type,
        'parameters': sample_params
    }
    
    return jsonify({
        'status': 'success',
        'sample_request': sample_request,
        'description': metadata.get('description', 'No description available'),
        'required_params': metadata.get('required_params', []),
        'optional_params': metadata.get('optional_params', [])
    }) 