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
    content_disposition_type VARCHAR(50),  -- Content-Disposition类型(如attachment/inline/form-data等)
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

### 阶段2: 邮件读取和存储功能 ✅ 已完成
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

4. **数据库存储** ✅
   - ✅ 邮件数据入库：基于EmailDatabaseService的异步数据库操作
   - ✅ 附件信息记录：完整的附件信息存储和关联管理
   - ✅ 去重机制（基于message_id）：自动去重避免重复存储

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

**EmailDatabaseService (services/email_database.py)**
- 异步数据库操作：基于aiomysql连接池的高性能数据库访问
- 事务性操作：邮件和附件的原子性保存，确保数据完整性
- 智能去重：基于message_id的自动去重机制
- 完整的CRUD操作：邮件和附件的增删改查功能
- 数据统计：邮件统计信息和系统状态监控
- JSON字段处理：自动处理recipients、cc、bcc等JSON字段序列化

**验证测试**
- ✅ IMAP连接测试通过
- ✅ 邮件列表获取正常
- ✅ 中文主题正确解码
- ✅ 多部分邮件解析正常
- ✅ 附件信息提取正确
- ✅ 文件存储服务全功能测试通过
- ✅ 数据库连接和操作测试通过
- ✅ 邮件数据库服务全功能验证
- ✅ 去重机制和事务性操作测试通过

### 阶段3: 定时任务 ✅ 已完成
1. **任务调度器** ✅
   - ✅ 配置APScheduler：基于AsyncIOScheduler的异步调度器
   - ✅ 实现定期邮件检查任务：使用IntervalTrigger按配置间隔执行
   - ✅ 错误处理和重试机制：任务失败不影响后续执行，支持错过触发的宽限期

2. **邮件同步逻辑** ✅
   - ✅ 增量同步（只读取新邮件）：集成EmailSyncService的增量同步功能
   - ✅ 处理IMAP连接异常：完整的异常处理和日志记录
   - ✅ 邮件状态跟踪：支持同步状态查询和统计信息

#### 阶段3完成的技术实现细节：

**MailScheduler (tasks/scheduler.py)**
- 基于APScheduler的异步任务调度器
- 事件监听器处理任务执行成功/失败事件
- 智能同步控制：max_instances=1确保同时只有一个同步任务
- 错过触发处理：misfire_grace_time=60秒宽限期，coalesce=True合并错过的任务
- 完整的状态监控和手动触发支持

**定时任务特性**
- **自动启动**: 服务启动时自动启动调度器，按MAIL_CHECK_INTERVAL间隔执行
- **增量同步**: 定时任务执行增量同步，只处理新邮件
- **并发控制**: 确保同一时间只有一个同步任务运行，避免资源冲突
- **错误容错**: 单次任务失败不影响后续定时执行
- **优雅关闭**: 服务关闭时优雅停止调度器

**API接口**
- `POST /sync/manual` - 手动触发邮件同步（支持limit和since_date查询参数）
- `GET /sync/status` - 获取邮件同步状态（包含调度器和同步服务状态）
- `GET /scheduler/status` - 获取调度器任务状态

**集成到主服务**
- FastAPI服务生命周期管理：启动时启动调度器，关闭时停止调度器
- 完整的错误处理：调度器启动失败不阻止服务启动
- 日志监控：详细的调度器状态和任务执行日志

**验证测试**
- ✅ 调度器启动和停止功能测试
- ✅ 定时任务执行和日志记录验证
- ✅ 手动同步API接口测试
- ✅ 状态查询API功能验证

### 阶段4: 邮件转发功能 ✅ 已完成
1. **SMTP服务** ✅
   - ✅ 网易SMTP连接配置：基于smtplib的SSL连接，支持网易企业邮箱
   - ✅ 邮件发送功能：完整的SMTP认证和邮件发送机制

2. **邮件转发器** ✅
   - ✅ 保持原始邮件头信息：转发时保持完整的邮件头格式
   - ✅ 处理附件转发：支持附件读取和转发，保持原有content-disposition-type
   - ✅ 支持多收件人：支持to、cc、bcc多种收件人类型

3. **转发API** ✅
   - ✅ REST API接口设计：POST /emails/{email_id}/forward接口
   - ✅ 请求参数验证：完整的参数校验和错误处理
   - ✅ 异步邮件发送：异步处理转发操作，提升性能

#### 阶段4完成的技术实现细节：

**EmailForwarder (services/email_forwarder.py)**
- 基于网易企业邮箱SMTP服务的邮件转发功能
- 完整的转发记录管理：保存转发历史到email_forwards表
- 智能邮件格式处理：支持HTML和纯文本邮件转发
- 附件转发支持：读取原始附件并添加到转发邮件中
- 保持原始content-disposition-type：inline/attachment等类型保持不变
- 转发状态追踪：pending/sent/failed状态管理

**SMTP发送特性**
- **SSL连接**: 使用SMTP_SSL确保连接安全
- **认证机制**: 支持用户名密码认证
- **多收件人**: 支持to、cc、bcc多种收件人模式
- **错误处理**: 完整的SMTP异常处理和重试机制
- **编码支持**: 正确处理中文主题和内容编码

**转发邮件格式**
- **主题处理**: 自动添加"Fwd:"前缀（如果不存在）
- **转发头部**: 标准的"---------- Forwarded message ----------"格式
- **原始信息**: 保留原始发送者、日期、主题、收件人信息
- **内容格式**: 支持HTML和纯文本两种格式
- **附加消息**: 支持在转发时添加自定义消息

**数据库集成**
- 扩展EmailDatabaseService支持转发记录操作
- save_email_forward: 保存转发记录
- update_forward_status: 更新转发状态
- get_forward_history: 获取转发历史
- get_forward_by_id: 获取转发记录详情

**API接口**
- `POST /emails/{email_id}/forward` - 转发邮件接口
- 请求体格式：
  ```json
  {
    "to_addresses": ["recipient@example.com"],
    "cc_addresses": ["cc@example.com"],  // 可选
    "bcc_addresses": ["bcc@example.com"], // 可选
    "additional_message": "转发说明"  // 可选
  }
  ```

**数据模型扩展**
- EmailForwardModel: 转发记录数据模型
- EmailForwardRequest: API请求模型
- 完整的JSON序列化支持和数据库字段映射

**验证测试**
- ✅ SMTP连接和认证测试通过
- ✅ 邮件转发功能完整测试
- ✅ 附件转发功能验证
- ✅ 多收件人转发测试
- ✅ 转发状态追踪功能测试
- ✅ API接口功能验证


## API接口设计

### 邮件相关
- `GET /emails` - 获取邮件列表（支持分页、筛选）
- `GET /emails/{email_id}` - 获取邮件详情
- `POST /emails/{email_id}/forward` - 转发邮件
- `GET /emails/{email_id}/attachments/{attachment_id}/download` - 下载附件

### 系统管理
- `GET /health` - 健康检查
- `POST /sync/manual` - 手动触发邮件同步
- `GET /sync/status` - 获取邮件同步状态
- `GET /scheduler/status` - 获取调度器状态

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

## 开发状态总结

**已完成的开发阶段：**
- ✅ **阶段1**: 项目基础搭建已完成
- ✅ **阶段2**: 邮件读取和存储功能已完成  
- ✅ **阶段3**: 定时任务已完成
- ✅ **阶段4**: 邮件转发功能已完成

**核心功能实现：**
1. ✅ 定期从网易企业邮箱读取新邮件并存储到MariaDB
2. ✅ 附件自动下载和存储管理
3. ✅ 邮件转发功能，支持多收件人、附件转发、保持原始格式
4. ✅ 完整的数据库操作和事务管理
5. ✅ 异步任务调度和状态监控
6. ✅ RESTful API接口（转发功能）

**技术栈完整实现：**
- FastAPI + 异步数据库连接池
- IMAP邮件读取 + SMTP邮件发送
- 网易企业邮箱完整支持
- MariaDB数据存储
- APScheduler定时任务
- 完整的错误处理和日志系统

邮箱微服务核心功能开发完成，可投入使用。