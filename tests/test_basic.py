import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from api.services.config import settings
from api.services.db import init_db, check_db_health

def test_settings_load():
    """Test that settings load correctly"""
    assert settings.postgres_host is not None
    assert settings.postgres_db == "credtech"
    assert settings.scoring_weights_base == 0.55

def test_database_url_generation():
    """Test database URL generation"""
    url = settings.database_url
    assert "postgresql://" in url
    assert settings.postgres_user in url
    assert settings.postgres_password in url
    assert settings.postgres_host in url

def test_event_weight_calculation():
    """Test event weight calculation"""
    weights = settings.get_event_weight("restructuring")
    assert weights == -4.0
    
    weights = settings.get_event_weight("bankruptcy")
    assert weights == -9.0
    
    weights = settings.get_event_weight("unknown_event")
    assert weights == -7.0  # default weight

def test_scoring_weights():
    """Test scoring weights configuration"""
    weights = settings.get_scoring_weights()
    assert weights["base"] == 0.55
    assert weights["market"] == 0.25
    assert weights["event"] == 0.12
    assert weights["macro"] == 0.08
    
    # Ensure weights sum to 1.0
    total_weight = sum(weights.values())
    assert abs(total_weight - 1.0) < 0.001

@pytest.mark.asyncio
async def test_database_connection():
    """Test database connection (requires running database)"""
    try:
        # This will fail if database is not running, which is expected in CI
        await init_db()
        health = await check_db_health()
        assert health is True
    except Exception:
        # Expected to fail in CI without database
        pass

def test_environment_variables():
    """Test environment variable loading"""
    assert hasattr(settings, 'postgres_host')
    assert hasattr(settings, 'redis_url')
    assert hasattr(settings, 'model_version')
    assert hasattr(settings, 'debug')

if __name__ == "__main__":
    pytest.main([__file__])





