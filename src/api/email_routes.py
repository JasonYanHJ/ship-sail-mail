from fastapi import APIRouter, HTTPException
from ..models.email_models import EmailForwardRequest
from ..services.email_database import EmailDatabaseService
from ..services.email_forwarder import EmailForwarder
from ..utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/emails", tags=["emails"])

# 服务实例
db_service = EmailDatabaseService()
forwarder = EmailForwarder()


@router.post("/{email_id}/forward")
async def forward_email(email_id: int, request: EmailForwardRequest):
    """转发邮件"""
    try:
        # 验证邮件是否存在
        email = await db_service.get_email_by_id(email_id)
        if not email:
            raise HTTPException(status_code=404, detail="邮件不存在")

        # 验证收件人地址
        if not request.to_addresses:
            raise HTTPException(status_code=400, detail="收件人地址不能为空")

        # 执行转发
        success = await forwarder.forward_email(
            email_id=email_id,
            to_addresses=request.to_addresses,
            cc_addresses=request.cc_addresses,
            bcc_addresses=request.bcc_addresses,
            additional_message=request.additional_message
        )

        if success:
            return {"message": "邮件转发成功", "email_id": email_id}
        else:
            raise HTTPException(status_code=500, detail="邮件转发失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"转发邮件失败: {e}")
        raise HTTPException(status_code=500, detail="转发邮件失败")
