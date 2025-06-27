"""
定时任务调度器模块
实现基于APScheduler的定时邮件同步功能
"""

from datetime import datetime
from typing import Optional, Dict, Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED

from ..config.settings import settings
from ..utils.logger import get_logger
from ..services.email_sync import email_sync_service

logger = get_logger('mail_scheduler')


class MailScheduler:
    """邮件定时任务调度器"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._setup_event_listeners()

    def _setup_event_listeners(self):
        """设置事件监听器"""
        self.scheduler.add_listener(self._job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error, EVENT_JOB_ERROR)

    def _job_executed(self, event):
        """任务执行成功事件处理"""
        logger.info(f"任务执行成功: {event.job_id}")

    def _job_error(self, event):
        """任务执行失败事件处理"""
        logger.error(f"任务执行失败: {event.job_id}, 异常: {event.exception}")
        # 可以在这里添加重试逻辑或告警通知

    async def sync_emails_task(self):
        """邮件同步定时任务"""
        try:
            logger.info("开始执行定时邮件同步任务")
            start_time = datetime.now()

            # 执行增量邮件同步
            result = await email_sync_service.incremental_sync()

            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info(
                f"定时邮件同步任务完成，耗时: {duration:.2f}秒，"
                f"新邮件数: {result.new_emails}，"
                f"总处理数: {result.total_processed}，"
                f"重复跳过: {result.duplicates_skipped}，"
                f"规则跳过: {result.rule_skipped}，"
                f"错误数: {result.errors}"
            )

            return result

        except Exception as e:
            logger.error(f"定时邮件同步任务执行失败: {e}", exc_info=True)
            # 不重新抛出异常，避免调度器停止

    def start(self):
        """启动调度器"""
        try:
            # 添加定时邮件同步任务
            self.scheduler.add_job(
                self.sync_emails_task,
                trigger=IntervalTrigger(seconds=settings.mail_check_interval),
                id='sync_emails',
                name='定时邮件同步',
                replace_existing=True,
                max_instances=1,  # 确保同一时间只有一个实例运行
                misfire_grace_time=60,  # 错过触发时间的宽限期
                coalesce=True  # 合并错过的任务
            )

            self.scheduler.start()
            logger.info(f"邮件调度器已启动，同步间隔: {settings.mail_check_interval}秒")

        except Exception as e:
            logger.error(f"启动调度器失败: {e}", exc_info=True)
            raise

    def stop(self):
        """停止调度器"""
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=True)
                logger.info("邮件调度器已停止")
        except Exception as e:
            logger.error(f"停止调度器失败: {e}", exc_info=True)

    def get_job_status(self) -> Dict[str, Any]:
        """获取任务状态"""
        job = self.scheduler.get_job('sync_emails')
        if job:
            return {
                'job_id': job.id,
                'job_name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger),
                'running': self.scheduler.running,
                'max_instances': job.max_instances,
                'misfire_grace_time': job.misfire_grace_time
            }
        return {'running': self.scheduler.running, 'job_exists': False}

    async def trigger_manual_sync(self, limit: Optional[int] = None,
                                  since_date: Optional[datetime] = None) -> Dict[str, Any]:
        """手动触发邮件同步"""
        try:
            logger.info(f"手动触发邮件同步，限制数量: {limit}，起始日期: {since_date}")

            # 检查是否正在同步
            if email_sync_service.is_syncing:
                logger.warning("邮件同步正在进行中，无法执行手动同步")
                return {
                    'success': False,
                    'message': '邮件同步正在进行中，请稍后再试'
                }

            # 根据是否提供since_date选择同步方式
            if since_date:
                result = await email_sync_service.force_sync_since(since_date, limit)
            else:
                result = await email_sync_service.incremental_sync(limit)

            logger.info(f"手动同步完成: {result}")
            return {
                'success': True,
                'stats': {
                    'total_processed': result.total_processed,
                    'new_emails': result.new_emails,
                    'duplicates_skipped': result.duplicates_skipped,
                    'rule_skipped': result.rule_skipped,
                    'errors': result.errors,
                    'sync_time': result.sync_time.isoformat() if result.sync_time else None
                }
            }

        except Exception as e:
            logger.error(f"手动同步失败: {e}", exc_info=True)
            return {
                'success': False,
                'message': f'同步失败: {str(e)}'
            }

    async def get_sync_status(self) -> Dict[str, Any]:
        """获取邮件同步状态"""
        try:
            # 获取邮件同步服务状态
            sync_status = await email_sync_service.get_sync_status()

            # 获取调度器任务状态
            job_status = self.get_job_status()

            return {
                'scheduler': job_status,
                'sync_service': sync_status
            }

        except Exception as e:
            logger.error(f"获取同步状态失败: {e}", exc_info=True)
            return {
                'error': f'获取状态失败: {str(e)}'
            }


# 全局调度器实例
mail_scheduler = MailScheduler()
