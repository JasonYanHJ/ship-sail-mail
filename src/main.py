from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional
from .config.settings import settings
from .models.database import db_manager, sync_db_manager
from .utils.logger import logger
from .tasks.scheduler import mail_scheduler
from .api.email_routes import router as email_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    logger.info("邮箱微服务启动中...")

    # 确保附件目录存在
    settings.ensure_attachment_dir()

    # 检查数据库表
    try:
        sync_db_manager.check_tables()
        logger.info("数据库表检查完成")
    except Exception as e:
        logger.error(f"数据库表检查失败: {e}")
        raise

    # 创建数据库连接池
    try:
        await db_manager.create_pool()
        logger.info("数据库连接池初始化完成")
    except Exception as e:
        logger.error(f"数据库连接池初始化失败: {e}")
        raise

    # 启动邮件调度器
    try:
        mail_scheduler.start()
        logger.info("邮件调度器启动完成")
    except Exception as e:
        logger.error(f"邮件调度器启动失败: {e}")
        # 不阻止服务启动，但记录警告
        logger.warning("邮件调度器未启动，定时同步功能将不可用")

    logger.info("邮箱微服务启动完成")

    yield

    # 关闭时执行
    logger.info("邮箱微服务关闭中...")

    # 停止邮件调度器
    try:
        mail_scheduler.stop()
        logger.info("邮件调度器已停止")
    except Exception as e:
        logger.error(f"邮件调度器停止失败: {e}")

    await db_manager.close_pool()
    logger.info("邮箱微服务已关闭")


app = FastAPI(
    title="邮箱微服务",
    description="基于FastAPI的邮箱操作微服务",
    version="1.0.0",
    lifespan=lifespan
)

# 注册路由
app.include_router(email_router)


@app.get("/")
async def read_root():
    return {"message": "邮箱微服务运行中", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "mail-service"}


@app.post("/sync/manual")
async def manual_sync(limit: Optional[int] = None, since_date: Optional[str] = None):
    """手动触发邮件同步"""
    try:
        # 解析since_date参数
        parsed_since_date = None
        if since_date:
            try:
                parsed_since_date = datetime.fromisoformat(
                    since_date.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="日期格式错误，请使用ISO格式")

        result = await mail_scheduler.trigger_manual_sync(limit=limit, since_date=parsed_since_date)
        return result

    except Exception as e:
        logger.error(f"手动同步请求失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sync/status")
async def get_sync_status():
    """获取邮件同步状态"""
    try:
        status = await mail_scheduler.get_sync_status()
        return status
    except Exception as e:
        logger.error(f"获取同步状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/scheduler/status")
async def get_scheduler_status():
    """获取调度器状态"""
    try:
        status = mail_scheduler.get_job_status()
        return status
    except Exception as e:
        logger.error(f"获取调度器状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
