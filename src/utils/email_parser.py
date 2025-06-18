from typing import Dict, List, Optional
from datetime import datetime
from email.message import Message
from email import message_from_bytes
import email.utils
import email.header
from .logger import logger


class EmailParser:
    """邮件解析工具类"""

    @staticmethod
    def parse_message_from_bytes(raw_email: bytes) -> Message:
        """从字节数据解析邮件消息对象"""
        try:
            return message_from_bytes(raw_email)
        except Exception as e:
            logger.error(f"解析邮件字节数据失败: {e}")
            raise

    @staticmethod
    def parse_headers(msg: Message) -> Dict:
        """解析邮件头信息"""
        try:
            # 解析发件人
            sender_raw = msg.get('From', '')
            sender = email.utils.parseaddr(sender_raw)[1] if sender_raw else ''

            # 解析收件人
            recipients = []
            to_header = msg.get('To', '')
            if to_header:
                recipients.extend(
                    [addr[1] for addr in email.utils.getaddresses([to_header])])

            # 解析抄送
            cc = []
            cc_header = msg.get('Cc', '')
            if cc_header:
                cc.extend([addr[1]
                          for addr in email.utils.getaddresses([cc_header])])

            # 解析密送
            bcc = []
            bcc_header = msg.get('Bcc', '')
            if bcc_header:
                bcc.extend([addr[1]
                           for addr in email.utils.getaddresses([bcc_header])])

            # 解析日期
            date_sent = None
            date_header = msg.get('Date', '')
            if date_header:
                try:
                    date_tuple = email.utils.parsedate_tz(date_header)
                    if date_tuple:
                        timestamp = email.utils.mktime_tz(date_tuple)
                        date_sent = datetime.fromtimestamp(timestamp)
                except Exception as e:
                    logger.warning(f"解析邮件日期失败: {e}")

            # 解析主题 - 处理MIME编码
            subject = EmailParser._decode_header(msg.get('Subject', ''))

            return {
                'message_id': msg.get('Message-ID', ''),
                'subject': subject,
                'sender': sender,
                'recipients': recipients,
                'cc': cc,
                'bcc': bcc,
                'date_sent': date_sent,
                'raw_headers': EmailParser._extract_raw_headers(msg)
            }

        except Exception as e:
            logger.error(f"解析邮件头失败: {e}")
            raise

    @staticmethod
    def parse_content(msg: Message) -> Dict:
        """解析邮件内容"""
        try:
            content_text = ""
            content_html = ""
            attachments = []

            if msg.is_multipart():
                # 多部分邮件
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = part.get('Content-Disposition', '')

                    if content_type == 'text/plain' and 'attachment' not in content_disposition:
                        # 文本内容
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            try:
                                content_text += payload.decode(
                                    charset, errors='ignore')
                            except:
                                content_text += payload.decode(
                                    'utf-8', errors='ignore')

                    elif content_type == 'text/html' and 'attachment' not in content_disposition:
                        # HTML内容
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or 'utf-8'
                            try:
                                content_html += payload.decode(
                                    charset, errors='ignore')
                            except:
                                content_html += payload.decode(
                                    'utf-8', errors='ignore')

                    elif 'attachment' in content_disposition or part.get_filename():
                        # 附件
                        filename = part.get_filename()
                        if filename:
                            # 解码文件名
                            decoded_filename = EmailParser._decode_filename(
                                filename)

                            # 提取Content-ID（如果有）
                            content_id = part.get('Content-Id')
                            if content_id:
                                # 移除尖括号（如果存在）
                                content_id = content_id.strip('<>')

                            attachment_info = {
                                'filename': decoded_filename,
                                'content_type': content_type,
                                'size': len(part.get_payload(decode=True) or b''),
                                'content': part.get_payload(decode=True),
                                'content_disposition_type': EmailParser._extract_disposition_type(content_disposition),
                                'content_id': content_id
                            }
                            attachments.append(attachment_info)
            else:
                # 单部分邮件
                content_type = msg.get_content_type()
                payload = msg.get_payload(decode=True)

                if payload:
                    charset = msg.get_content_charset() or 'utf-8'
                    try:
                        content = payload.decode(charset, errors='ignore')
                    except:
                        content = payload.decode('utf-8', errors='ignore')

                    if content_type == 'text/plain':
                        content_text = content
                    elif content_type == 'text/html':
                        content_html = content

            return {
                'content_text': content_text,
                'content_html': content_html,
                'attachments': attachments
            }

        except Exception as e:
            logger.error(f"解析邮件内容失败: {e}")
            raise

    @staticmethod
    def parse_full_email(raw_email: bytes) -> Dict:
        """完整解析邮件（头信息+内容）"""
        try:
            # 解析邮件消息对象
            msg = EmailParser.parse_message_from_bytes(raw_email)

            # 解析邮件头
            headers = EmailParser.parse_headers(msg)

            # 解析邮件内容
            content = EmailParser.parse_content(msg)

            # 合并结果
            return {
                **headers,
                **content
            }

        except Exception as e:
            logger.error(f"完整解析邮件失败: {e}")
            raise

    @staticmethod
    def _decode_header(header_value: str) -> str:
        """解码MIME编码的邮件头"""
        if not header_value:
            return ''

        try:
            # 解码MIME编码的头部
            decoded_parts = email.header.decode_header(header_value)
            decoded_string = ''

            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    # 如果有指定编码，使用指定编码；否则尝试UTF-8
                    if encoding:
                        try:
                            decoded_string += part.decode(encoding)
                        except (UnicodeDecodeError, LookupError):
                            # 如果指定编码失败，尝试UTF-8
                            decoded_string += part.decode('utf-8',
                                                          errors='ignore')
                    else:
                        # 没有编码信息，尝试UTF-8
                        decoded_string += part.decode('utf-8', errors='ignore')
                else:
                    # 已经是字符串
                    decoded_string += part

            return decoded_string.strip()

        except Exception as e:
            logger.warning(f"解码邮件头失败: {e}, 原始值: {header_value}")
            return header_value

    @staticmethod
    def _extract_raw_headers(msg: Message) -> str:
        """提取邮件的原始头信息（不包含正文）"""
        try:
            # 构建包含所有头信息的字符串
            headers = []
            for key, value in msg.items():
                headers.append(f"{key}: {value}")
            return "\n".join(headers)
        except Exception as e:
            logger.warning(f"提取原始邮件头失败: {e}")
            return ""

    @staticmethod
    def _decode_filename(filename: str) -> str:
        """解码文件名"""
        try:
            # 处理 RFC2231 编码的文件名
            return email.utils.collapse_rfc2231_value(filename)
        except:
            # 如果解码失败，尝试MIME解码
            try:
                return EmailParser._decode_header(filename)
            except:
                # 最后返回原文件名
                return filename

    @staticmethod
    def extract_attachment_info(msg: Message) -> List[Dict]:
        """仅提取附件信息（不包含内容）"""
        try:
            attachments = []

            if msg.is_multipart():
                for part in msg.walk():
                    content_disposition = part.get('Content-Disposition', '')

                    if 'attachment' in content_disposition or part.get_filename():
                        filename = part.get_filename()
                        if filename:
                            decoded_filename = EmailParser._decode_filename(
                                filename)

                            attachment_info = {
                                'filename': decoded_filename,
                                'content_type': part.get_content_type(),
                                'size': len(part.get_payload(decode=True) or b''),
                                'content_disposition_type': EmailParser._extract_disposition_type(part.get('Content-Disposition', ''))
                            }
                            attachments.append(attachment_info)

            return attachments

        except Exception as e:
            logger.error(f"提取附件信息失败: {e}")
            return []

    @staticmethod
    def extract_attachment_content(msg: Message, filename: str) -> Optional[bytes]:
        """提取指定附件的内容"""
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    content_disposition = part.get('Content-Disposition', '')

                    if 'attachment' in content_disposition or part.get_filename():
                        part_filename = part.get_filename()
                        if part_filename:
                            decoded_filename = EmailParser._decode_filename(
                                part_filename)
                            if decoded_filename == filename:
                                return part.get_payload(decode=True)

            return None

        except Exception as e:
            logger.error(f"提取附件内容失败: {e}")
            return None

    @staticmethod
    def _extract_disposition_type(content_disposition: str) -> str:
        """
        从Content-Disposition头中提取disposition类型

        Args:
            content_disposition: Content-Disposition头的完整值

        Returns:
            disposition类型（去除参数部分），如果解析失败返回空字符串
        """
        if not content_disposition:
            return ''

        try:
            # Content-Disposition格式为:
            # "attachment; filename=example.txt"
            # "inline; filename=image.jpg"
            # "form-data; name=file"
            # 我们只需要第一部分的disposition类型，去除后续的参数
            disposition_type = content_disposition.split(';')[
                0].strip().lower()

            # 返回disposition类型（保留所有可能的类型值）
            return disposition_type

        except Exception as e:
            logger.warning(
                f"解析Content-Disposition类型失败: {e}, 原始值: {content_disposition}")
            return ''


# 全局邮件解析器实例
email_parser = EmailParser()
