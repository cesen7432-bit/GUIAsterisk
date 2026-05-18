from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    secret_key: str = "change-this-secret-key"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    db_host: str = "db"
    db_port: int = 3306
    db_user: str = "pbxuser"
    db_password: str = "pbx_pass"
    db_name: str = "asterisk_gui"

    ami_host: str = "host.docker.internal"
    ami_port: int = 5038
    ami_user: str = "admin"
    ami_password: str = "secret"

    ari_host: str = "host.docker.internal"
    ari_port: int = 8088
    ari_user: str = "asterisk"
    ari_password: str = "asterisk"

    asterisk_config_path: str = "/etc/asterisk"
    recordings_path: str = "/var/spool/asterisk/monitor"
    sounds_path: str = "/var/lib/asterisk/sounds/custom"
    server_ip: str = "127.0.0.1"

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()


settings = get_settings()
