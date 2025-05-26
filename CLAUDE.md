# 邮箱微服务开发计划

## 项目概述
基于FastAPI框架实现邮箱相关操作的微服务，支持：
1. 定期读取网易企业邮箱新邮件，保存到MariaDB并下载附件
2. 邮件转发功能，保持原始邮件格式

## 技术栈
- **框架**: FastAPI
- **邮箱协议**: IMAP (读取) + SMTP (发送)
- **邮箱服务**: 网易企业邮箱
- **数据库**: MariaDB
- **Python库**: 
  - fastapi
  - uvicorn
  - aiomysql / pymysql
  - imapclient (IMAP客户端)
  - smtplib
  - email (标准库)
  - python-dotenv
  - apscheduler (定时任务)

## 环境变量配置 (.env)
```
# 邮箱配置
EMAIL_USERNAME=your_email@company.com
EMAIL_PASSWORD=your_password
IMAP_SERVER=imap.qiye.163.com
IMAP_PORT=993
SMTP_SERVER=smtp.qiye.163.com
SMTP_PORT=465

# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=password
DB_NAME=mail_service

# 文件存储
ATTACHMENT_PATH=/path/to/attachments

# 系统配置
MAIL_CHECK_INTERVAL=300  # 秒，检查邮件频率
```

## 数据库设计

### emails 表
```sql
CREATE TABLE emails (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    message_id VARCHAR(255) UNIQUE NOT NULL,  -- 邮件唯一标识，用于去重
    subject TEXT,
    sender VARCHAR(255),
    recipients TEXT,  -- JSON格式存储多个收件人
    cc TEXT,          -- JSON格式存储抄送人
    bcc TEXT,         -- JSON格式存储密送人
    content_text TEXT,
    content_html LONGTEXT,
    date_sent DATETIME,
    date_received DATETIME DEFAULT CURRENT_TIMESTAMP,
    raw_headers LONGTEXT,  -- 原始邮件头
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_message_id (message_id),
    INDEX idx_date_received (date_received),
    INDEX idx_sender (sender)
);
```

### attachments 表
```sql
CREATE TABLE attachments (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    email_id BIGINT,
    original_filename VARCHAR(255),
    stored_filename VARCHAR(255),
    file_path VARCHAR(500),
    file_size BIGINT,
    content_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
    INDEX idx_email_id (email_id)
);
```

### email_forwards 表
```sql
CREATE TABLE email_forwards (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    email_id BIGINT NOT NULL,
    to_addresses TEXT NOT NULL,      -- JSON格式存储转发收件人
    cc_addresses TEXT,               -- JSON格式存储转发抄送人
    bcc_addresses TEXT,              -- JSON格式存储转发密送人
    additional_message TEXT,         -- 转发时的附加消息
    forward_status ENUM('pending', 'sent', 'failed') DEFAULT 'pending',
    error_message TEXT,              -- 转发失败时的错误信息
    forwarded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (email_id) REFERENCES emails(id) ON DELETE CASCADE,
    INDEX idx_email_id (email_id),
    INDEX idx_forwarded_at (forwarded_at),
    INDEX idx_forward_status (forward_status)
);
```

## 项目结构
```
src/
├── main.py                 # FastAPI应用入口
├── config/
│   └── settings.py         # 配置管理
├── models/
│   ├── __init__.py
│   ├── database.py         # 数据库连接
│   └── email_models.py     # 数据模型
├── services/
│   ├── __init__.py
│   ├── email_reader.py     # 邮件读取服务
│   ├── email_forwarder.py  # 邮件转发服务
│   └── file_storage.py     # 文件存储服务
├── api/
│   ├── __init__.py
│   └── email_routes.py     # API路由
├── tasks/
│   ├── __init__.py
│   └── scheduler.py        # 定时任务
└── utils/
    ├── __init__.py
    ├── email_parser.py     # 邮件解析工具
    └── logger.py           # 日志工具
```

## 开发计划

### 阶段1: 项目基础搭建 ✅ 已完成
1. **初始化项目结构** ✅
   - ✅ 创建目录结构：已按照设计创建完整的src目录结构
   - ✅ 配置requirements.txt：包含所有必需的Python依赖
   - ✅ 设置.env模板：定义了所有环境变量配置项

2. **配置管理** ✅
   - ✅ 实现settings.py：使用pydantic-settings读取环境变量
   - ✅ 配置日志系统：实现了统一的日志管理工具

3. **数据库连接** ✅
   - ✅ 实现数据库连接池：基于aiomysql的异步连接池
   - ✅ 创建数据模型类：完整的Email、Attachment、Forward模型

#### 阶段1完成的技术实现细节：

**项目结构**
```
src/
├── main.py                 # FastAPI应用入口
├── config/
│   └── settings.py         # 基于pydantic-settings的配置管理
├── models/
│   ├── __init__.py
│   ├── database.py         # 异步数据库连接池 + 同步表创建
│   └── email_models.py     # Pydantic数据模型
├── services/               # 业务服务层
├── api/                    # API路由层
├── tasks/                  # 定时任务
└── utils/
    ├── __init__.py
    └── logger.py           # 统一日志配置
```

**关键技术选型**
- **配置管理**: pydantic-settings + python-dotenv
- **数据库**: aiomysql异步连接池 + pymysql同步操作
- **数据模型**: Pydantic BaseModel，支持JSON序列化
- **日志**: Python标准logging + 自定义格式化

**数据库设计优化**
- 移除了冗余的`has_attachments`和`attachment_count`字段
- 采用关联查询动态获取附件信息
- 保证数据一致性，降低维护成本

**连接池配置**
- 异步连接池：minsize=1, maxsize=10
- 事务支持：自动回滚机制
- 字符集：utf8mb4，支持完整Unicode

**下一阶段准备**
- 数据库表已定义，可直接创建
- 配置系统已就绪，支持环境变量读取
- 日志系统已配置，便于调试和监控

### 阶段2: 邮件读取功能 ✅ 已完成
1. **IMAP连接服务** ✅
   - ✅ 实现IMAP连接和认证：基于imapclient库的SSL连接
   - ✅ 邮件列表获取：支持文件夹选择和邮件搜索
   - ✅ 邮件内容解析：集成EmailParser进行完整解析

2. **邮件解析器** ✅
   - ✅ 解析邮件头信息：支持MIME编码解码（UTF-8、GB2312等）
   - ✅ 提取文本和HTML内容：多部分邮件内容解析
   - ✅ 处理附件：附件信息提取和内容获取

3. **文件存储服务** ✅
   - ✅ 实现附件下载和存储：基于FileStorageService的异步文件操作
   - ✅ 按日期时间(精确到分钟)+邮件ID+原文件名命名：YYYYMMDDHHMM_邮件ID_原文件名
   - ✅ 文件路径管理：自动创建目录、安全文件名清理、文件信息管理

4. **数据库存储** ⏳ 待实现
   - 邮件数据入库
   - 附件信息记录
   - 去重机制（基于message_id）

#### 阶段2完成的技术实现细节：

**EmailReader (services/email_reader.py)**
- SSL IMAP连接管理（支持上下文管理器）
- 邮箱文件夹操作和邮件搜索
- 原始邮件数据获取和解析邮件数据获取
- 网易邮箱兼容性处理（ID命令）
- 完整的错误处理和日志记录

**EmailParser (utils/email_parser.py)**
- MIME编码邮件头解码（RFC2047）
- 多部分邮件内容解析（文本/HTML/附件）
- 字符编码处理（UTF-8、GB2312等）
- 附件信息提取和内容获取
- 文件名解码处理

**关键技术特性**
- **职责分离**: EmailReader专注IMAP操作，EmailParser专注邮件解析
- **MIME支持**: 完整的MIME编码解码，支持中文主题和附件名
- **错误容错**: 字符编码失败时的降级处理
- **可复用性**: EmailParser可在转发、API等模块中重用

**FileStorageService (services/file_storage.py)**
- 异步文件存储操作（保存、读取、删除）
- 智能文件命名：YYYYMMDDHHMM_邮件ID_原文件名格式
- 文件名安全性处理：移除危险字符、长度限制
- 支持中文文件名和多种编码
- 文件信息管理和旧文件清理功能
- 完整的错误处理和日志记录

**验证测试**
- ✅ IMAP连接测试通过
- ✅ 邮件列表获取正常
- ✅ 中文主题正确解码
- ✅ 多部分邮件解析正常
- ✅ 附件信息提取正确
- ✅ 文件存储服务全功能测试通过

### 阶段3: 定时任务
1. **任务调度器**
   - 配置APScheduler
   - 实现定期邮件检查任务
   - 错误处理和重试机制

2. **邮件同步逻辑**
   - 增量同步（只读取新邮件）
   - 处理IMAP连接异常
   - 邮件状态跟踪

### 阶段4: 邮件转发功能
1. **SMTP服务**
   - 网易SMTP连接配置
   - 邮件发送功能

2. **邮件转发器**
   - 保持原始邮件头信息
   - 处理附件转发
   - 支持多收件人

3. **转发API**
   - REST API接口设计
   - 请求参数验证
   - 异步邮件发送

### 阶段5: API和服务完善
1. **RESTful API**
   - 邮件列表查询
   - 邮件详情获取
   - 邮件转发接口
   - 附件下载接口

2. **错误处理**
   - 统一异常处理
   - API错误响应
   - 日志记录

3. **性能优化**
   - 数据库查询优化
   - 异步处理
   - 连接池管理

### 阶段6: 测试和部署
1. **单元测试**
   - 邮件解析测试
   - 数据库操作测试
   - API接口测试

2. **集成测试**
   - 端到端邮件处理流程
   - 异常情况测试

3. **部署配置**
   - Docker配置
   - 生产环境配置
   - 监控和日志

## API接口设计

### 邮件相关
- `GET /emails` - 获取邮件列表（支持分页、筛选）
- `GET /emails/{email_id}` - 获取邮件详情
- `POST /emails/{email_id}/forward` - 转发邮件
- `GET /emails/{email_id}/attachments/{attachment_id}/download` - 下载附件

### 系统管理
- `GET /health` - 健康检查
- `POST /sync/manual` - 手动触发邮件同步
- `GET /stats` - 系统统计信息

## 关键技术点

1. **邮件去重**: 使用Message-ID作为唯一标识
2. **附件命名**: `YYYYMMDDHHMM_邮件ID_原文件名`
3. **原始邮件头保留**: 转发时保持完整的邮件头信息
4. **异步处理**: 使用FastAPI的异步特性处理IO密集操作
5. **错误恢复**: IMAP连接断开重连，邮件处理失败重试
6. **安全性**: 邮箱密码加密存储，API访问控制

## 注意事项

1. **IMAP连接管理**: 合理控制连接数，避免服务器限制
2. **大附件处理**: 设置文件大小限制，流式下载
3. **邮件编码**: 正确处理各种字符编码
4. **时区处理**: 邮件时间的时区转换
5. **内存管理**: 大邮件处理时的内存控制

## 开发优先级
1. 基础框架搭建 → 邮件读取 → 数据存储 → 定时任务 → 转发功能 → API完善 → 测试部署