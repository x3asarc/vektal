"""
Utilities for provisioning and managing tenant schemas.
"""
import logging
from sqlalchemy import text
from src.models import db
from src.core.tenancy.context import get_tenant_schema_name

logger = logging.getLogger(__name__)

def provision_tenant_schema(store_id: int) -> bool:
    """
    Create a new isolated schema for a tenant and initialize tables.
    
    Args:
        store_id: The ID of the ShopifyStore
        
    Returns:
        True if successful, False otherwise
    """
    schema_name = get_tenant_schema_name(store_id)
    
    try:
        # 1. Create the schema
        db.session.execute(text(f"CREATE SCHEMA IF NOT EXISTS {schema_name}"))
        
        # 2. Set search_path for this session to create tables in the new schema
        db.session.execute(text(f"SET search_path TO {schema_name}"))
        
        # 3. Create all tables in the new schema
        # Note: We must be careful not to create 'global' tables like users here.
        # However, for simplicity in v1.0, we can create all tables and just ignore
        # the ones we don't use in the tenant schema.
        # A more advanced version would filter the MetaData.
        db.create_all()
        
        # 4. Reset search_path
        db.session.execute(text("SET search_path TO public"))
        
        db.session.commit()
        logger.info(f"Provisioned schema {schema_name} for store {store_id}")
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to provision schema {schema_name}: {str(e)}")
        return False

def deprovision_tenant_schema(store_id: int) -> bool:
    """
    Drop a tenant's isolated schema (destructive!).
    """
    schema_name = get_tenant_schema_name(store_id)
    try:
        db.session.execute(text(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE"))
        db.session.commit()
        return True
    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to drop schema {schema_name}: {str(e)}")
        return False
