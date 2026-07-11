from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    db_host: str = "db"
    db_port: int = 3306
    db_user: str = "pbxuser"
    db_password: str = "pbx_pass"
    db_name: str = "asterisk_gui"

    ari_host: str = "host.docker.internal"
    ari_port: int = 8088
    ari_user: str = "ariuser"
    ari_password: str = "aripassword"
    ari_app: str = "voice-agent"

    asterisk_trunk: str = "openvox"

    agent_rtp_host: str = "10.10.10.20"
    rtp_port_start: int = 10000
    rtp_port_end: int = 10100

    openai_api_key: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
