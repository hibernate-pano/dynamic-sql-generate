import jinja2
import logging
import time
import hashlib
from functools import lru_cache
from flask import current_app
from app.templates.sql_templates import get_template, validate_template_parameters
from app.database.db import db

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Jinja2 environment for SQL templates
jinja_env = jinja2.Environment(
    autoescape=False,  # No HTML escaping for SQL
    trim_blocks=True,
    lstrip_blocks=True
)

class SQLService:
    # Cache for rendered SQL templates (key: hash of biz_type + params, value: rendered SQL)
    _sql_cache = {}
    _cache_hits = 0
    _cache_misses = 0
    _cache_size_limit = 100  # Maximum number of cached templates
    
    @staticmethod
    def _generate_cache_key(biz_type, parameters):
        """
        Generate a cache key from business type and parameters
        
        Args:
            biz_type: Business type
            parameters: Parameter dictionary
            
        Returns:
            String cache key
        """
        # Create a string representation of parameters
        param_str = str(sorted([(k, str(v)) for k, v in parameters.items()]))
        
        # Generate MD5 hash
        key = hashlib.md5(f"{biz_type}:{param_str}".encode()).hexdigest()
        return key
    
    @staticmethod
    def process_template(biz_type, parameters, group_parameters=None, sort_parameters=None):
        """
        Process SQL template with given parameters
        
        Args:
            biz_type: Business type to determine which SQL template to use
            parameters: Dictionary of parameters to fill into the template
            group_parameters: Comma-separated field names to group by
            sort_parameters: List of dictionaries with sort_param and sort_type
            
        Returns:
            Rendered SQL query string or None if template not found
            
        Raises:
            ValueError: If biz_type is invalid or required parameters are missing
        """
        # Validate parameters
        is_valid, error_message = validate_template_parameters(biz_type, parameters)
        if not is_valid:
            logger.error(f"Parameter validation error: {error_message}")
            raise ValueError(error_message)
        
        # Check cache first
        cache_key = SQLService._generate_cache_key(biz_type, parameters)
        if cache_key in SQLService._sql_cache and not group_parameters and not sort_parameters:
            SQLService._cache_hits += 1
            logger.debug(f"Cache hit for business type '{biz_type}' (hits: {SQLService._cache_hits}, misses: {SQLService._cache_misses})")
            return SQLService._sql_cache[cache_key]
        
        SQLService._cache_misses += 1
        
        # Get the template
        template_str = get_template(biz_type)
        if not template_str:
            logger.error(f"Unknown business type: {biz_type}")
            raise ValueError(f"Unknown business type: {biz_type}")
        
        # Add dynamic GROUP BY if provided
        if group_parameters:
            group_fields = [field.strip() for field in group_parameters.split(',')]
            group_by_clause = f"GROUP BY {', '.join(group_fields)}"
            
            # Check if there's already a GROUP BY in the template
            if "GROUP BY" in template_str:
                # Replace existing GROUP BY with our dynamic one
                template_str = template_str.split("GROUP BY")[0] + group_by_clause
                
                # Check if there's a HAVING clause to preserve
                if "HAVING" in template_str:
                    having_clause = "HAVING" + template_str.split("HAVING")[1].split("ORDER BY")[0]
                    template_str = template_str.split("HAVING")[0] + having_clause
            else:
                # Add GROUP BY before ORDER BY if it exists
                if "ORDER BY" in template_str:
                    template_str = template_str.split("ORDER BY")[0] + group_by_clause + "\nORDER BY" + template_str.split("ORDER BY")[1]
                else:
                    # Add at the end if no ORDER BY
                    template_str += f"\n{group_by_clause}"
        
        # Add dynamic ORDER BY if provided
        if sort_parameters and isinstance(sort_parameters, list) and len(sort_parameters) > 0:
            sort_clauses = []
            for sort_item in sort_parameters:
                if isinstance(sort_item, dict) and 'sort_param' in sort_item and 'sort_type' in sort_item:
                    sort_param = sort_item['sort_param']
                    sort_type = sort_item['sort_type'].upper()
                    if sort_type not in ['ASC', 'DESC']:
                        sort_type = 'ASC'  # Default to ascending
                    sort_clauses.append(f"{sort_param} {sort_type}")
            
            if sort_clauses:
                order_by_clause = f"ORDER BY {', '.join(sort_clauses)}"
                
                # Check if there's already an ORDER BY in the template
                if "ORDER BY" in template_str:
                    # Replace existing ORDER BY with our dynamic one
                    template_str = template_str.split("ORDER BY")[0] + order_by_clause
                    
                    # Check if there's a LIMIT clause to preserve
                    if "LIMIT" in template_str:
                        limit_clause = "LIMIT" + template_str.split("LIMIT")[1]
                        template_str = template_str.split("LIMIT")[0] + limit_clause
                else:
                    # Add at the end if no ORDER BY
                    template_str += f"\n{order_by_clause}"
        
        try:
            # Render the template with parameters
            template = jinja_env.from_string(template_str)
            sql = template.render(**parameters)
            
            # Clean up the SQL (remove excessive whitespace)
            sql = ' '.join(line.strip() for line in sql.splitlines() if line.strip())
            
            logger.info(f"Generated SQL for business type '{biz_type}'")
            logger.debug(f"Generated SQL: {sql}")
            
            # Cache the result (with cache size limit management)
            if len(SQLService._sql_cache) >= SQLService._cache_size_limit:
                # Simple strategy: remove a random entry
                try:
                    SQLService._sql_cache.pop(next(iter(SQLService._sql_cache)))
                except Exception:
                    # If that fails, just clear the whole cache
                    SQLService._sql_cache.clear()
            
            # Only cache if no dynamic parameters were used
            if not group_parameters and not sort_parameters:
                SQLService._sql_cache[cache_key] = sql
            
            return sql
        except jinja2.exceptions.TemplateError as e:
            logger.error(f"Template rendering error: {str(e)}")
            raise ValueError(f"Error rendering SQL template: {str(e)}")
    
    @staticmethod
    def execute_dynamic_query(biz_type, parameters, group_parameters=None, sort_parameters=None):
        """
        Generate and execute a dynamic SQL query based on business type and parameters
        
        Args:
            biz_type: Business type to determine which SQL template to use
            parameters: Dictionary of parameters to fill into the template
            group_parameters: Comma-separated field names to group by
            sort_parameters: List of dictionaries with sort_param and sort_type
            
        Returns:
            Query result (list of dictionaries)
            
        Raises:
            ValueError: If biz_type is invalid or required parameters are missing
        """
        start_time = time.time()
        
        # Process the template
        sql = SQLService.process_template(biz_type, parameters, group_parameters, sort_parameters)
        
        # Extract only the parameters that should be passed to the SQL query
        # (excluding any that were only used for template conditionals)
        query_params = {
            k: v for k, v in parameters.items() 
            if k in sql and not isinstance(v, bool)
        }
        
        template_time = time.time() - start_time
        
        # Execute the query
        try:
            logger.info(f"Executing query for business type '{biz_type}'")
            result = db.execute_query(sql, query_params)
            
            # Add template processing time to result
            result['template_time_ms'] = int(template_time * 1000)
            
            # Add cache stats to result
            result['cache_info'] = {
                'hits': SQLService._cache_hits,
                'misses': SQLService._cache_misses,
                'current_size': len(SQLService._sql_cache)
            }
            
            return result
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}")
            raise ValueError(f"Error executing query: {str(e)}")
    
    @staticmethod
    def clear_cache():
        """Clear the SQL template cache"""
        SQLService._sql_cache.clear()
        SQLService._cache_hits = 0
        SQLService._cache_misses = 0
        logger.info("SQL template cache cleared")
    
    @staticmethod
    def get_cache_stats():
        """Get statistics about the SQL template cache"""
        return {
            'size': len(SQLService._sql_cache),
            'hits': SQLService._cache_hits,
            'misses': SQLService._cache_misses,
            'hit_ratio': SQLService._cache_hits / (SQLService._cache_hits + SQLService._cache_misses) if (SQLService._cache_hits + SQLService._cache_misses) > 0 else 0
        }


# Create a single instance to be used throughout the app
sql_service = SQLService() 