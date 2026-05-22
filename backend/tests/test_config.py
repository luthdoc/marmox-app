"""
Testes para backend/core/config.py — carregamento e validação de variáveis de ambiente.
"""
import os
import pytest
from unittest.mock import patch


def test_settings_loads_required_variables():
    """Settings deve carregar variáveis obrigatórias quando presentes."""
    env_vars = {
        "SUPABASE_URL": "https://abc.supabase.co",
        "SUPABASE_SERVICE_KEY": "service-key-123",
        "ANTHROPIC_API_KEY": "anthropic-key-456",
        "ZAPI_INSTANCE_ID": "instance-123",
        "ZAPI_TOKEN": "token-789",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        from core.config import Settings
        settings = Settings()
        assert settings.supabase_url == "https://abc.supabase.co"
        assert settings.supabase_service_key == "service-key-123"
        assert settings.anthropic_api_key == "anthropic-key-456"
        assert settings.zapi_instance_id == "instance-123"
        assert settings.zapi_token == "token-789"


def test_settings_defaults_for_optional_variables():
    """APP_ENV e LOG_LEVEL devem ter defaults quando não definidas."""
    env_vars = {
        "SUPABASE_URL": "https://abc.supabase.co",
        "SUPABASE_SERVICE_KEY": "service-key-123",
        "ANTHROPIC_API_KEY": "anthropic-key-456",
        "ZAPI_INSTANCE_ID": "instance-123",
        "ZAPI_TOKEN": "token-789",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        from core.config import Settings
        settings = Settings()
        assert settings.app_env == "development"
        assert settings.log_level == "INFO"


def test_settings_fails_when_supabase_url_missing():
    """Settings deve falhar com erro claro se SUPABASE_URL estiver ausente."""
    env_vars = {
        "SUPABASE_SERVICE_KEY": "service-key-123",
        "ANTHROPIC_API_KEY": "anthropic-key-456",
        "ZAPI_INSTANCE_ID": "instance-123",
        "ZAPI_TOKEN": "token-789",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        from core.config import Settings
        with pytest.raises(Exception):
            Settings()


def test_settings_fails_when_anthropic_api_key_missing():
    """Settings deve falhar com erro claro se ANTHROPIC_API_KEY estiver ausente."""
    env_vars = {
        "SUPABASE_URL": "https://abc.supabase.co",
        "SUPABASE_SERVICE_KEY": "service-key-123",
        "ZAPI_INSTANCE_ID": "instance-123",
        "ZAPI_TOKEN": "token-789",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        from core.config import Settings
        with pytest.raises(Exception):
            Settings()


def test_settings_accepts_production_app_env():
    """APP_ENV=production deve ser aceito."""
    env_vars = {
        "SUPABASE_URL": "https://abc.supabase.co",
        "SUPABASE_SERVICE_KEY": "service-key-123",
        "ANTHROPIC_API_KEY": "anthropic-key-456",
        "ZAPI_INSTANCE_ID": "instance-123",
        "ZAPI_TOKEN": "token-789",
        "APP_ENV": "production",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        from core.config import Settings
        settings = Settings()
        assert settings.app_env == "production"


def test_settings_accepts_custom_log_level():
    """LOG_LEVEL customizado deve ser carregado."""
    env_vars = {
        "SUPABASE_URL": "https://abc.supabase.co",
        "SUPABASE_SERVICE_KEY": "service-key-123",
        "ANTHROPIC_API_KEY": "anthropic-key-456",
        "ZAPI_INSTANCE_ID": "instance-123",
        "ZAPI_TOKEN": "token-789",
        "LOG_LEVEL": "DEBUG",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        from core.config import Settings
        settings = Settings()
        assert settings.log_level == "DEBUG"
