import logging
import sys
from pathlib import Path
from typing import Optional
from ..config.settings import settings


def setup_logger(
    name: str = "mail_service",
    level: Optional[str] = None,
    log_file: Optional[str] = None
) -> logging.Logger:
    """设置日志配置"""

    # 使用配置中的日志级别，如果没有传入的话
    log_level = level or settings.log_level
    log_file_path = log_file or settings.log_file

    # 创建logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # 避免重复添加handler
    if logger.handlers:
        return logger

    # 创建formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件handler（如果指定了日志文件）
    if log_file_path:
        # 确保日志文件的目录存在
        log_path = Path(log_file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 创建默认logger实例
logger = setup_logger()
