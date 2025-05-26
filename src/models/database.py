import aiomysql
import pymysql
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from ..config.settings import settings
from ..utils.logger import logger


class DatabaseManager:
    """数据库连接管理器"""

    def __init__(self):
        self._pool: Optional[aiomysql.Pool] = None

    async def create_pool(self) -> aiomysql.Pool:
        """创建异步数据库连接池"""
        if self._pool is None:
            try:
                self._pool = await aiomysql.create_pool(
                    host=settings.db_host,
                    port=settings.db_port,
                    user=settings.db_user,
                    password=settings.db_password,
                    db=settings.db_name,
                    charset='utf8mb4',
                    autocommit=False,
                    minsize=1,
                    maxsize=10
                )
                logger.info("数据库连接池创建成功")
            except Exception as e:
                logger.error(f"创建数据库连接池失败: {e}")
                raise
        return self._pool

    async def close_pool(self):
        """关闭数据库连接池"""
        if self._pool:
            self._pool.close()
            await self._pool.wait_closed()
            self._pool = None
            logger.info("数据库连接池已关闭")

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[aiomysql.Connection, None]:
        """获取数据库连接的异步上下文管理器"""
        if self._pool is None:
            await self.create_pool()

        async with self._pool.acquire() as conn:
            try:
                yield conn
            except Exception as e:
                await conn.rollback()
                logger.error(f"数据库操作错误: {e}")
                raise

    @asynccontextmanager
    async def get_transaction(self) -> AsyncGenerator[aiomysql.Connection, None]:
        """获取带事务的数据库连接"""
        async with self.get_connection() as conn:
            try:
                await conn.begin()
                yield conn
                await conn.commit()
            except Exception as e:
                await conn.rollback()
                logger.error(f"事务执行失败: {e}")
                raise


class SyncDatabaseManager:
    """同步数据库连接管理器（用于初始化等场景）"""

    @staticmethod
    def get_sync_connection() -> pymysql.Connection:
        """获取同步数据库连接"""
        try:
            connection = pymysql.connect(
                host=settings.db_host,
                port=settings.db_port,
                user=settings.db_user,
                password=settings.db_password,
                database=settings.db_name,
                charset='utf8mb4',
                autocommit=False
            )
            return connection
        except Exception as e:
            logger.error(f"创建同步数据库连接失败: {e}")
            raise

    @staticmethod
    def create_tables():
        """创建数据库表"""
        create_emails_table = """
        CREATE TABLE IF NOT EXISTS emails (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            message_id VARCHAR(255) UNIQUE NOT NULL COMMENT '邮件唯一标识',
            subject TEXT COMMENT '邮件主题',
            sender VARCHAR(255) COMMENT '发送者',
            recipients TEXT COMMENT '收件人(JSON格式)',
            cc TEXT COMMENT '抄送人(JSON格式)',
            bcc TEXT COMMENT '密送人(JSON格式)',
            content_text TEXT COMMENT '纯文本内容',
            content_html LONGTEXT COMMENT 'HTML内容',
            date_sent DATETIME COMMENT '发送时间',
            date_received DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '接收时间',
            raw_headers LONGTEXT COMMENT '原始邮件头',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            INDEX idx_message_id (message_id),
            INDEX idx_date_received (date_received),
            INDEX idx_sender (sender)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        create_attachments_table = """
        CREATE TABLE IF NOT EXISTS attachments (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            email_id BIGINT NOT NULL COMMENT '邮件ID',
            original_filename VARCHAR(255) COMMENT '原始文件名',
            stored_filename VARCHAR(255) COMMENT '存储文件名',
            file_path VARCHAR(500) COMMENT '文件路径',
            file_size BIGINT COMMENT '文件大小',
            content_type VARCHAR(100) COMMENT '文件类型',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
            INDEX idx_email_id (email_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        create_email_forwards_table = """
        CREATE TABLE IF NOT EXISTS email_forwards (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            email_id BIGINT NOT NULL COMMENT '原始邮件ID',
            to_addresses TEXT NOT NULL COMMENT '转发收件人(JSON格式)',
            cc_addresses TEXT COMMENT '转发抄送人(JSON格式)',
            bcc_addresses TEXT COMMENT '转发密送人(JSON格式)',
            additional_message TEXT COMMENT '附加消息',
            forward_status ENUM('pending', 'sent', 'failed') DEFAULT 'pending' COMMENT '转发状态',
            error_message TEXT COMMENT '错误信息',
            forwarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '转发时间',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
            INDEX idx_email_id (email_id),
            INDEX idx_forwarded_at (forwarded_at),
            INDEX idx_forward_status (forward_status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """

        try:
            with SyncDatabaseManager.get_sync_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(create_emails_table)
                    cursor.execute(create_attachments_table)
                    cursor.execute(create_email_forwards_table)
                    conn.commit()
                    logger.info("数据库表创建成功")
        except Exception as e:
            logger.error(f"创建数据库表失败: {e}")
            raise


# 全局数据库管理器实例
db_manager = DatabaseManager()
sync_db_manager = SyncDatabaseManager()
