from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    # 邮箱配置
    email_username: str
    email_password: str
    imap_server: str = "imap.qiye.163.com"
    imap_port: int = 993
    smtp_server: str = "smtp.qiye.163.com"
    smtp_port: int = 465

    # 数据库配置
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "root"
    db_password: str
    db_name: str = "mail_service"

    # 文件存储
    attachment_path: str

    # 系统配置
    mail_check_interval: int = 300  # 秒

    # 日志配置
    log_level: str = "INFO"
    log_file: Optional[str] = None

    # API配置
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        case_sensitive = False

    @property
    def database_url(self) -> str:
        return f"mysql+pymysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def async_database_url(self) -> str:
        return f"mysql+aiomysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    def ensure_attachment_dir(self):
        """确保附件目录存在"""
        if not os.path.exists(self.attachment_path):
            os.makedirs(self.attachment_path, exist_ok=True)


# 全局设置实例
settings = Settings()
