"""
Testes para backend/core/config.py — carregamento e validação de variáveis de ambiente.
"""
import os
import pytest
from unittest.mock import patch

_BASE_ENV = {
    "SUPABASE_URL": "https://abc.supabase.co",
    "SUPABASE_SERVICE_KEY": "service-key-123",
    "ANTHROPIC_API_KEY": "anthropic-key-456",
    "META_WHATSAPP_ACCESS_TOKEN": "EAABs-token",
    "META_WHATSAPP_VERIFY_TOKEN": "verify-token-xyz",
}


def test_settings_loads_required_variables():
    """Settings deve carregar variáveis obrigatórias quando presentes."""
    with patch.dict(os.environ, _BASE_ENV, clear=True):
        from core.config import Settings
        settings = Settings()
        assert settings.supabase_url == "https://abc.supabase.co"
        assert settings.supabase_service_key == "service-key-123"
        assert settings.anthropic_api_key == "anthropic-key-456"
        assert settings.meta_whatsapp_access_token == "EAABs-token"
        assert settings.meta_whatsapp_verify_token == "verify-token-xyz"


def test_settings_defaults_for_optional_variables():
    """APP_ENV e LOG_LEVEL devem ter defaults quando não definidas."""
    with patch.dict(os.environ, _BASE_ENV, clear=True):
        from core.config import Settings
        settings = Settings()
        assert settings.app_env == "development"
        assert settings.log_level == "INFO"


def test_settings_fails_when_supabase_url_missing():
    """Settings deve falhar com erro claro se SUPABASE_URL estiver ausente."""
    env = {k: v for k, v in _BASE_ENV.items() if k != "SUPABASE_URL"}
    with patch.dict(os.environ, env, clear=True):
        from core.config import Settings
        with pytest.raises(Exception):
            Settings()


def test_settings_fails_when_anthropic_api_key_missing():
    """Settings deve falhar com erro claro se ANTHROPIC_API_KEY estiver ausente."""
    env = {k: v for k, v in _BASE_ENV.items() if k != "ANTHROPIC_API_KEY"}
    with patch.dict(os.environ, env, clear=True):
        from core.config import Settings
        with pytest.raises(Exception):
            Settings()


def test_settings_fails_when_meta_access_token_missing():
    """Settings deve falhar se META_WHATSAPP_ACCESS_TOKEN estiver ausente."""
    env = {k: v for k, v in _BASE_ENV.items() if k != "META_WHATSAPP_ACCESS_TOKEN"}
    with patch.dict(os.environ, env, clear=True):
        from core.config import Settings
        with pytest.raises(Exception):
            Settings()


def test_settings_accepts_production_app_env():
    """APP_ENV=production deve ser aceito."""
    env = {**_BASE_ENV, "APP_ENV": "production"}
    with patch.dict(os.environ, env, clear=True):
        from core.config import Settings
        settings = Settings()
        assert settings.app_env == "production"


def test_settings_accepts_custom_log_level():
    """LOG_LEVEL customizado deve ser carregado."""
    env = {**_BASE_ENV, "LOG_LEVEL": "DEBUG"}
    with patch.dict(os.environ, env, clear=True):
        from core.config import Settings
        settings = Settings()
        assert settings.log_level == "DEBUG"
