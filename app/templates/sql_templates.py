"""
SQL Templates Module

This module contains SQL templates organized by business type.
Each template is a string with placeholders that will be replaced with actual values.

Templates use SQLAlchemy's named parameter style with colons (e.g., :parameter_name).
Optional parameters can be handled with Jinja2-style conditionals.
"""

import os
import json
import logging
from flask import current_app

# Configure logging
logger = logging.getLogger(__name__)

# SQL Templates dictionary
# Keys are business types, values are the SQL template strings
SQL_TEMPLATES = {
    # Customer analysis template
    "customer_analysis": """
        SELECT 
            o.order_id, 
            p.product_name, 
            o.amount, 
            o.purchase_date
        FROM 
            orders o
        JOIN 
            products p ON o.product_id = p.product_id
        WHERE 
            o.customer_id = :customer_id
            AND o.purchase_date BETWEEN :start_date AND :end_date
        {% if product_category %}
            AND p.category = :product_category
        {% endif %}
        ORDER BY 
            o.purchase_date DESC
    """,
    
    # Product performance template
    "product_performance": """
        SELECT 
            p.product_name,
            COUNT(o.order_id) as order_count,
            SUM(o.amount) as total_revenue
        FROM 
            products p
        JOIN 
            orders o ON p.product_id = o.product_id
        WHERE 
            o.purchase_date BETWEEN :start_date AND :end_date
        {% if category_id %}
            AND p.category_id = :category_id
        {% endif %}
        GROUP BY 
            p.product_id
        ORDER BY 
            total_revenue DESC
        {% if limit %}
            LIMIT :limit
        {% endif %}
    """,
    
    # Customer segmentation template
    "customer_segmentation": """
        SELECT 
            c.customer_id,
            c.customer_name,
            c.email,
            COUNT(o.order_id) as total_orders,
            SUM(o.amount) as total_spent,
            AVG(o.amount) as avg_order_value,
            MAX(o.purchase_date) as last_purchase_date
        FROM 
            customers c
        LEFT JOIN 
            orders o ON c.customer_id = o.customer_id
        WHERE 
            o.purchase_date BETWEEN :start_date AND :end_date
        {% if customer_region %}
            AND c.region = :customer_region
        {% endif %}
        GROUP BY 
            c.customer_id
        {% if min_orders %}
            HAVING COUNT(o.order_id) >= :min_orders
        {% endif %}
        ORDER BY 
            total_spent DESC
    """,
    
    # Inventory status template
    "inventory_status": """
        SELECT 
            p.product_id,
            p.product_name,
            i.quantity_in_stock,
            i.reorder_level,
            s.supplier_name,
            p.unit_price,
            (i.quantity_in_stock * p.unit_price) as inventory_value
        FROM 
            products p
        JOIN 
            inventory i ON p.product_id = i.product_id
        JOIN 
            suppliers s ON p.supplier_id = s.supplier_id
        {% if low_stock_only %}
            WHERE i.quantity_in_stock <= i.reorder_level
        {% else %}
            WHERE 1=1
        {% endif %}
        {% if supplier_id %}
            AND p.supplier_id = :supplier_id
        {% endif %}
        {% if category_id %}
            AND p.category_id = :category_id
        {% endif %}
        ORDER BY 
            {% if sort_by_stock %}
                i.quantity_in_stock ASC
            {% else %}
                p.product_name
            {% endif %}
    """
}

# Template metadata with parameter validation info
TEMPLATE_METADATA = {
    "customer_analysis": {
        "description": "Analyze customer order history",
        "required_params": ["customer_id", "start_date", "end_date"],
        "optional_params": ["product_category"],
        "param_types": {
            "customer_id": "integer",
            "start_date": "date",
            "end_date": "date",
            "product_category": "string"
        }
    },
    "product_performance": {
        "description": "Analyze product sales performance",
        "required_params": ["start_date", "end_date"],
        "optional_params": ["category_id", "limit"],
        "param_types": {
            "start_date": "date",
            "end_date": "date",
            "category_id": "integer",
            "limit": "integer"
        }
    },
    "customer_segmentation": {
        "description": "Segment customers based on purchase behavior",
        "required_params": ["start_date", "end_date"],
        "optional_params": ["customer_region", "min_orders"],
        "param_types": {
            "start_date": "date",
            "end_date": "date",
            "customer_region": "string",
            "min_orders": "integer"
        }
    },
    "inventory_status": {
        "description": "Check inventory levels and value",
        "required_params": [],
        "optional_params": ["low_stock_only", "supplier_id", "category_id", "sort_by_stock"],
        "param_types": {
            "low_stock_only": "boolean",
            "supplier_id": "integer",
            "category_id": "integer",
            "sort_by_stock": "boolean"
        }
    }
}

def load_templates_from_file():
    """
    Load SQL templates from JSON file if available
    
    This allows templates to be defined externally without code changes
    """
    try:
        # Check if templates directory exists in app instance folder
        templates_dir = os.path.join(current_app.instance_path, 'templates')
        if not os.path.exists(templates_dir):
            os.makedirs(templates_dir)
            
        templates_file = os.path.join(templates_dir, 'sql_templates.json')
        
        # If file exists, load templates from it
        if os.path.exists(templates_file):
            with open(templates_file, 'r') as f:
                file_templates = json.load(f)
                
            # Update the built-in templates with file-based ones
            for biz_type, template in file_templates.items():
                SQL_TEMPLATES[biz_type] = template
                logger.info(f"Loaded template for business type: {biz_type} from file")
                
            logger.info(f"Loaded {len(file_templates)} SQL templates from file")
            
    except Exception as e:
        logger.warning(f"Failed to load SQL templates from file: {str(e)}")

def get_template(biz_type):
    """
    Get SQL template for a specific business type
    
    Args:
        biz_type: Business type identifier
        
    Returns:
        SQL template string or None if not found
    """
    return SQL_TEMPLATES.get(biz_type)

def get_template_metadata(biz_type):
    """
    Get metadata for a specific template
    
    Args:
        biz_type: Business type identifier
        
    Returns:
        Template metadata dictionary or None if not found
    """
    return TEMPLATE_METADATA.get(biz_type)

def list_templates():
    """
    Get list of all available templates with their descriptions
    
    Returns:
        Dictionary of template IDs and descriptions
    """
    result = {}
    for biz_type in SQL_TEMPLATES:
        if biz_type in TEMPLATE_METADATA:
            result[biz_type] = TEMPLATE_METADATA[biz_type]["description"]
        else:
            result[biz_type] = "No description available"
    
    return result

def validate_template_parameters(biz_type, parameters):
    """
    Validate parameters against template metadata
    
    Args:
        biz_type: Business type identifier
        parameters: Dictionary of parameters to validate
        
    Returns:
        (bool, str) tuple - (is_valid, error_message)
    """
    metadata = get_template_metadata(biz_type)
    if not metadata:
        return True, ""  # No metadata, can't validate
    
    # Check required params
    missing_params = []
    for param in metadata["required_params"]:
        if param not in parameters:
            missing_params.append(param)
    
    if missing_params:
        return False, f"Missing required parameters: {', '.join(missing_params)}"
    
    # Check parameter types
    for param, value in parameters.items():
        if param in metadata["param_types"]:
            expected_type = metadata["param_types"][param]
            
            # Basic type validation
            if expected_type == "integer":
                try:
                    int(value)
                except (ValueError, TypeError):
                    return False, f"Parameter '{param}' must be an integer"
                    
            elif expected_type == "date":
                # Simple date format check (could be more sophisticated)
                if not isinstance(value, str) or len(value) < 8:
                    return False, f"Parameter '{param}' must be a date string (YYYY-MM-DD)"
            
            elif expected_type == "boolean":
                if not isinstance(value, bool) and value not in ("true", "false", "0", "1"):
                    return False, f"Parameter '{param}' must be a boolean"
    
    return True, "" 