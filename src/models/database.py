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
    def check_tables():
        """检查数据库表是否存在"""
        required_tables = ['emails', 'attachments']

        try:
            with SyncDatabaseManager.get_sync_connection() as conn:
                with conn.cursor() as cursor:
                    missing_tables = []

                    for table_name in required_tables:
                        cursor.execute("SHOW TABLES LIKE %s", (table_name,))
                        if cursor.fetchone() is None:
                            missing_tables.append(table_name)

                    if missing_tables:
                        error_msg = f"数据库表不存在: {', '.join(missing_tables)}"
                        logger.error(error_msg)
                        raise RuntimeError(error_msg)

                    logger.info("数据库表检查通过")

        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            else:
                logger.error(f"检查数据库表失败: {e}")
                raise


# 全局数据库管理器实例
db_manager = DatabaseManager()
sync_db_manager = SyncDatabaseManager()
