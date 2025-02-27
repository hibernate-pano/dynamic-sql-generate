import os
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def create_app(config_name=None):
    """
    Application factory function to initialize and configure the Flask app
    Args:
        config_name: Configuration name to use (default: None, will use environment variable)
    Returns:
        Configured Flask application
    """
    # Create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    
    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    
    # Enable CORS
    CORS(app)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    # Load the appropriate configuration
    if config_name == 'production':
        app.config.from_object('app.config.config.ProductionConfig')
    elif config_name == 'testing':
        app.config.from_object('app.config.config.TestingConfig')
    else:
        app.config.from_object('app.config.config.DevelopmentConfig')
    
    # Initialize database
    from app.database import db
    db.init_app(app)
    
    # Register blueprints
    from app.api.routes import api_bp
    app.register_blueprint(api_bp)
    
    # Add health check endpoint
    @app.route('/health')
    def health_check():
        # Check database connection
        db_status = "healthy"
        try:
            # Quick query to check database connection
            with app.app_context():
                db.get_connection()
        except Exception as e:
            db_status = f"unhealthy: {str(e)}"
        
        return {
            "status": "healthy" if db_status == "healthy" else "degraded",
            "service": "dynamic-sql-generator",
            "database": db_status,
            "environment": app.config.get('ENV', 'development')
        }, 200 if db_status == "healthy" else 503
    
    # Add global error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "status": "error",
            "error": "The requested resource was not found",
            "code": "NOT_FOUND"
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            "status": "error",
            "error": "The method is not allowed for the requested URL",
            "code": "METHOD_NOT_ALLOWED"
        }), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "status": "error",
            "error": "Internal server error",
            "code": "SERVER_ERROR"
        }), 500
    
    return app 