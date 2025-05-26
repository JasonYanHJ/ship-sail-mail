from fastapi import FastAPI
from contextlib import asynccontextmanager
from .config.settings import settings
from .models.database import db_manager, sync_db_manager
from .utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    logger.info("邮箱微服务启动中...")

    # 确保附件目录存在
    settings.ensure_attachment_dir()

    # 创建数据库表
    try:
        sync_db_manager.create_tables()
        logger.info("数据库表检查完成")
    except Exception as e:
        logger.error(f"数据库表创建失败: {e}")
        raise

    # 创建数据库连接池
    try:
        await db_manager.create_pool()
        logger.info("数据库连接池初始化完成")
    except Exception as e:
        logger.error(f"数据库连接池初始化失败: {e}")
        raise

    logger.info("邮箱微服务启动完成")

    yield

    # 关闭时执行
    logger.info("邮箱微服务关闭中...")
    await db_manager.close_pool()
    logger.info("邮箱微服务已关闭")


app = FastAPI(
    title="邮箱微服务",
    description="基于FastAPI的邮箱操作微服务",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def read_root():
    return {"message": "邮箱微服务运行中", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "mail-service"}
