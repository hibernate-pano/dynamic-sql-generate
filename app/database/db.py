from flask import current_app, g
from sqlalchemy import create_engine, text
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.engine = None

    def init_app(self, app):
        """Initialize the database with the Flask app
        
        Args:
            app: Flask application instance
        """
        # Close database connection on app teardown
        app.teardown_appcontext(self.close_connection)
    
    def get_connection(self):
        """Get database connection from context or create a new one
        
        Returns:
            SQLAlchemy engine connection
        """
        if 'db_conn' not in g:
            try:
                # Create engine if it doesn't exist
                if not self.engine:
                    logger.info("Creating new SQLAlchemy engine")
                    self.engine = create_engine(
                        current_app.config['SQLALCHEMY_DATABASE_URI'],
                        pool_pre_ping=True,  # Check connection before use
                        pool_recycle=3600,   # Recycle connections after 1 hour
                        pool_size=10,        # Connection pool size
                        max_overflow=20      # Max additional connections
                    )
                
                # Create new connection
                g.db_conn = self.engine.connect()
                logger.debug("Created new database connection")
            except Exception as e:
                logger.error(f"Database connection error: {str(e)}")
                raise
        
        return g.db_conn
    
    def close_connection(self, exception=None):
        """Close database connection if it exists
        
        Args:
            exception: Exception that caused teardown (if any)
        """
        db_conn = g.pop('db_conn', None)
        
        if db_conn is not None:
            db_conn.close()
            logger.debug("Closed database connection")
    
    def execute_query(self, sql, params=None):
        """Execute SQL query and return results
        
        Args:
            sql: SQL query string
            params: Dictionary of parameters to bind to the query
            
        Returns:
            List of dictionaries representing rows
        """
        conn = self.get_connection()
        start_time = time.time()
        
        try:
            # Log the SQL statement with parameter values (for development/debugging)
            if current_app.debug:
                logger.debug(f"Executing SQL: {sql}")
                if params:
                    logger.debug(f"Parameters: {params}")
            
            # Execute the query
            result = conn.execute(text(sql), params or {})
            
            # Convert result to list of dictionaries
            columns = result.keys()
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            
            # Log execution time
            execution_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            logger.info(f"Query executed in {execution_time:.2f}ms, returned {len(rows)} rows")
            
            return {
                "data": rows,
                "row_count": len(rows),
                "execution_time_ms": int(execution_time)
            }
            
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}")
            raise


# Create a single instance to be used throughout the app
db = Database() 