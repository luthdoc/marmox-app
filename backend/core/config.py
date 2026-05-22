"""
Configuração centralizada da aplicação via variáveis de ambiente.

Usa pydantic-settings para carregar e validar as variáveis no boot.
Falha imediatamente com mensagem clara se uma variável obrigatória estiver ausente.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Variáveis de ambiente da aplicação Marmax.

    Variáveis obrigatórias falham no boot se ausentes.
    Variáveis opcionais têm defaults seguros declarados.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- Supabase ---
    supabase_url: str
    supabase_service_key: str

    # --- Anthropic ---
    anthropic_api_key: str

    # --- Z-API ---
    zapi_instance_id: str
    zapi_token: str

    # --- Aplicação (opcionais com defaults seguros) ---
    app_env: str = "development"
    log_level: str = "INFO"
