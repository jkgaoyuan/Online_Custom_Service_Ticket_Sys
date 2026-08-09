# T006 SLA 管理与超时监控设计文档

> 版本: v1.0  
> 日期: 2026-08-09  
> 状态: 已评审  
> 对应任务: T006（SLA 记录、超时扫描、通知基础设施）

---

## 一、设计目标

实现工单系统的 SLA（服务等级协议）监控与提醒机制：

- 工单创建时自动生成 SLA 执行记录
- 按分类 + 优先级配置不同的首次响应和解决时限
- 分阶段预警：客服在截止前 3 小时、2 小时收到提醒；主管在截止前 1 小时收到提醒
- 超时后自动标记并通知
- 建立可复用的站内通知基础设施

---

## 二、范围与边界

**T006 包含：**

| 模块 | 说明 | 对应子任务 |
|------|------|-----------|
| SLA 记录模型 | `sla_records` 表 + Alembic 迁移 | M2-T7 |
| SLA 规则引擎 | 工单创建时自动计算并生成 SLA 记录 | M2-T8 |
| Celery 定时扫描 | 每 5 分钟检查预警和超时 | M2-T9 |
| 通知模型 | `notifications` 表 + 通用通知服务 | M2-T10 |
| SLA 超时/预警通知 | 写入站内通知 + 可选邮件调用 | M2-T11 |
| SLA 查询 API | 工单 SLA 详情 + 管理后台超时列表 | — |

**T006 不包含（留给后续任务）：**

- 满意度评价通知（M2-T13）
- 前端通知中心 UI（M2-T18）
- 统计报表中的 SLA 聚合（T007）
- 主管管辖范围细分（通知所有 supervisor，后续按需细化）

---

## 三、关键决策

| 决策 | 选择 | 原因 |
|------|------|------|
| SLA 时间计算 | 自然时间（24/7） | 用户明确，MVP 优先 |
| SLA 配置粒度 | 分类级（`Category.sla_config`） | 复用现有 JSON 字段，零数据库迁移 |
| 配置格式 | 按优先级存储小时数 | 支持不同优先级不同标准，向后兼容空 dict |
| 超时标记 | Celery 扫描任务统一标记 | 避免分散逻辑，单一职责 |
| 首次响应定义 | 非内部备注的 agent/supervisor/admin 回复 | 内部备注不算对客户响应 |
| 预警策略 | 客服 3h/2h、主管 1h 分阶段 | 用户明确需求 |
| 主管通知范围 | 所有 `role='supervisor'` 用户 | MVP 简化，后续按管辖范围细化 |
| 通知存储 | 全部写入 `notifications` 表 | 站内信为基础，邮件通道懒加载调用 Mailer |
| 历史 SLA 保护 | 创建时快照小时数到 `sla_records` | 政策修改不影响历史工单 |

---

## 四、数据模型

### 4.1 `categories.sla_config` 格式

复用现有 `JSON` 字段，标准化为按优先级配置：

```json
{
  "P0": {"first_resp_hours": 1, "resolution_hours": 4},
  "P1": {"first_resp_hours": 2, "resolution_hours": 8},
  "P2": {"first_resp_hours": 4, "resolution_hours": 24},
  "P3": {"first_resp_hours": 8, "resolution_hours": 72}
}
```

**Fallback 策略**：若分类的 `sla_config` 为空或缺少某优先级键，使用全局默认：

```python
DEFAULT_SLA = {
    "P0": {"first_resp_hours": 1, "resolution_hours": 4},
    "P1": {"first_resp_hours": 4, "resolution_hours": 24},
    "P2": {"first_resp_hours": 8, "resolution_hours": 48},
    "P3": {"first_resp_hours": 24, "resolution_hours": 72},
}
```

### 4.2 `sla_records` — SLA 执行记录表

与 `ARCHITECTURE.md` 定义一致，增加预警标记字段：

```sql
CREATE TABLE sla_records (
    id                      SERIAL PRIMARY KEY,
    ticket_id               INTEGER NOT NULL UNIQUE REFERENCES tickets(id) ON DELETE CASCADE,
    priority                VARCHAR(10) NOT NULL,
    first_resp_hours        INTEGER NOT NULL,
    resolution_hours        INTEGER NOT NULL,
    first_resp_due          TIMESTAMP NOT NULL,
    resolution_due          TIMESTAMP NOT NULL,
    first_resp_at           TIMESTAMP,
    resolved_at             TIMESTAMP,
    first_resp_breached     BOOLEAN DEFAULT FALSE,
    resolution_breached     BOOLEAN DEFAULT FALSE,
    -- 预警标记（防止重复提醒）
    first_resp_warned_agent_3h  BOOLEAN DEFAULT FALSE,
    first_resp_warned_agent_2h  BOOLEAN DEFAULT FALSE,
    first_resp_warned_supervisor_1h BOOLEAN DEFAULT FALSE,
    resolution_warned_agent_3h  BOOLEAN DEFAULT FALSE,
    resolution_warned_agent_2h  BOOLEAN DEFAULT FALSE,
    resolution_warned_supervisor_1h BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_sla_due ON sla_records(resolution_due) WHERE resolution_breached = FALSE;
```

**模型定义：**

```python
class SLARecord(Base):
    __tablename__ = "sla_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
    first_resp_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    resolution_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    first_resp_due: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    resolution_due: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    first_resp_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    first_resp_breached: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_breached: Mapped[bool] = mapped_column(Boolean, default=False)

    # 预警标记
    first_resp_warned_agent_3h: Mapped[bool] = mapped_column(Boolean, default=False)
    first_resp_warned_agent_2h: Mapped[bool] = mapped_column(Boolean, default=False)
    first_resp_warned_supervisor_1h: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_warned_agent_3h: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_warned_agent_2h: Mapped[bool] = mapped_column(Boolean, default=False)
    resolution_warned_supervisor_1h: Mapped[bool] = mapped_column(Boolean, default=False)

    ticket: Mapped["Ticket"] = relationship("Ticket")
```

### 4.3 `notifications` — 站内通知表

```sql
CREATE TABLE notifications (
    id              SERIAL PRIMARY KEY,
    user_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type            VARCHAR(30) NOT NULL,
    title           VARCHAR(100) NOT NULL,
    message         TEXT NOT NULL,
    data            JSONB NOT NULL DEFAULT '{}',
    is_read         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_notifications_user_unread ON notifications(user_id, is_read) WHERE is_read = FALSE;
```

**模型定义：**

```python
class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

---

## 五、SLA 规则引擎

### 5.1 创建 SLA 记录

在 `create_ticket()` service 中，工单入库后（`db.flush()` 拿到 `ticket.id`）立即创建：

```python
async def create_sla_record(db, ticket: Ticket) -> SLARecord:
    sla_config = ticket.category.sla_config or {}
    priority_config = sla_config.get(ticket.priority, DEFAULT_SLA[ticket.priority])

    now = datetime.utcnow()
    record = SLARecord(
        ticket_id=ticket.id,
        priority=ticket.priority,
        first_resp_hours=priority_config["first_resp_hours"],
        resolution_hours=priority_config["resolution_hours"],
        first_resp_due=now + timedelta(hours=priority_config["first_resp_hours"]),
        resolution_due=now + timedelta(hours=priority_config["resolution_hours"]),
    )
    db.add(record)
    await db.flush()
    return record
```

**事务边界**：`create_ticket()` 的调用方统一 `commit`，确保工单与 SLA 记录原子性。

### 5.2 首次响应时间捕获

在 `create_reply()` service 中，当非内部备注的客服回复时：

```python
if not is_internal and author.role in ("agent", "supervisor", "admin"):
    sla = await get_sla_record_by_ticket_id(db, ticket_id)
    if sla and sla.first_resp_at is None:
        sla.first_resp_at = datetime.utcnow()
```

### 5.3 解决时间捕获

在 `update_ticket_status()` service 中，状态变为 `resolved` 时：

```python
if new_status == "resolved":
    sla = await get_sla_record_by_ticket_id(db, ticket.id)
    if sla and sla.resolved_at is None:
        sla.resolved_at = datetime.utcnow()
```

---

## 六、Celery 定时扫描任务

### 6.1 扫描周期

每 5 分钟执行一次 `scan_sla_deadlines`。

### 6.2 扫描逻辑

对于**首次响应 SLA** 和**解决 SLA**，分别检查 4 个阶段：

```python
async def _async_scan():
    now = datetime.utcnow()

    async with AsyncSessionLocal() as db:
        # ========== 首次响应预警 / 超时 ==========
        await _scan_first_resp(db, now)
        # ========== 解决预警 / 超时 ==========
        await _scan_resolution(db, now)

        await db.commit()

async def _scan_first_resp(db, now):
    # --- 客服 3 小时提醒 ---
    stmt = select(SLARecord).where(
        SLARecord.first_resp_hours > 3,  # 只有 SLA > 3h 才需要此提醒
        SLARecord.first_resp_due > now,
        SLARecord.first_resp_due <= now + timedelta(hours=3),
        SLARecord.first_resp_at.is_(None),
        SLARecord.first_resp_warned_agent_3h.is_(False),
    )
    for record in (await db.execute(stmt)).scalars():
        record.first_resp_warned_agent_3h = True
        await notify_sla_warning(db, record, "first_resp", stage="agent_3h")

    # --- 客服 2 小时提醒 ---
    stmt = select(SLARecord).where(
        SLARecord.first_resp_hours > 2,
        SLARecord.first_resp_due > now,
        SLARecord.first_resp_due <= now + timedelta(hours=2),
        SLARecord.first_resp_at.is_(None),
        SLARecord.first_resp_warned_agent_2h.is_(False),
    )
    for record in (await db.execute(stmt)).scalars():
        record.first_resp_warned_agent_2h = True
        await notify_sla_warning(db, record, "first_resp", stage="agent_2h")

    # --- 主管 1 小时提醒 ---
    stmt = select(SLARecord).where(
        SLARecord.first_resp_hours > 1,
        SLARecord.first_resp_due > now,
        SLARecord.first_resp_due <= now + timedelta(hours=1),
        SLARecord.first_resp_at.is_(None),
        SLARecord.first_resp_warned_supervisor_1h.is_(False),
    )
    for record in (await db.execute(stmt)).scalars():
        record.first_resp_warned_supervisor_1h = True
        await notify_sla_warning(db, record, "first_resp", stage="supervisor_1h")

    # --- 超时 ---
    stmt = select(SLARecord).where(
        SLARecord.first_resp_due <= now,
        SLARecord.first_resp_at.is_(None),
        SLARecord.first_resp_breached.is_(False),
    )
    for record in (await db.execute(stmt)).scalars():
        record.first_resp_breached = True
        await notify_sla_breach(db, record, "first_resp")

async def _scan_resolution(db, now):
    # 逻辑同 _scan_first_resp，字段名替换为 resolution_*
    # ...（客服 3h / 2h、主管 1h、超时）
```

### 6.3 通知发送

```python
async def notify_sla_warning(db, sla: SLARecord, breach_type: str, stage: str):
    ticket = sla.ticket
    target_roles = []

    if stage in ("agent_3h", "agent_2h"):
        target_roles = ["agent"]
    elif stage == "supervisor_1h":
        target_roles = ["supervisor"]

    # 收集目标用户
    target_user_ids = set()
    if "agent" in target_roles and ticket.assignee_id:
        target_user_ids.add(ticket.assignee_id)
    if "supervisor" in target_roles:
        supervisors = await db.execute(select(User.id).where(User.role == "supervisor"))
        target_user_ids.update(supervisors.scalars().all())

    stage_label = {"agent_3h": "3小时", "agent_2h": "2小时", "supervisor_1h": "1小时"}[stage]
    type_label = "首次响应" if breach_type == "first_resp" else "解决"

    for user_id in target_user_ids:
        await create_notification(
            db,
            user_id=user_id,
            type="sla_warning",
            title=f"⚠️ 工单 #{ticket.ticket_no} 即将超时",
            message=f"{type_label}截止时间剩余不足 {stage_label}，请及时处理。",
            data={"ticket_id": ticket.id, "sla_record_id": sla.id, "stage": stage, "type": breach_type},
        )

async def notify_sla_breach(db, sla: SLARecord, breach_type: str):
    ticket = sla.ticket
    target_user_ids = set()

    if ticket.assignee_id:
        target_user_ids.add(ticket.assignee_id)
    supervisors = await db.execute(select(User.id).where(User.role == "supervisor"))
    target_user_ids.update(supervisors.scalars().all())

    type_label = "首次响应" if breach_type == "first_resp" else "解决"

    for user_id in target_user_ids:
        await create_notification(
            db,
            user_id=user_id,
            type="sla_breach",
            title=f"🚨 工单 #{ticket.ticket_no} SLA 已超时",
            message=f"{type_label}时间已超出规定时限（{sla.first_resp_hours if breach_type == 'first_resp' else sla.resolution_hours} 小时）。",
            data={"ticket_id": ticket.id, "sla_record_id": sla.id, "type": breach_type},
        )
```

---

## 七、通知服务与 API

### 7.1 Notification Service

```python
async def create_notification(db, user_id: int, type: str, title: str, message: str, data: dict | None = None) -> Notification:
    notif = Notification(
        user_id=user_id,
        type=type,
        title=title,
        message=message,
        data=data or {},
    )
    db.add(notif)
    await db.flush()
    return notif

async def get_unread_notifications(db, user_id: int, limit: int = 50) -> list[Notification]:
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == user_id)
        .order_by(Notification.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()

async def mark_notification_read(db, notification_id: int, user_id: int) -> bool:
    from sqlalchemy import update
    result = await db.execute(
        update(Notification)
        .where(Notification.id == notification_id, Notification.user_id == user_id)
        .values(is_read=True)
    )
    return result.rowcount > 0

async def mark_all_notifications_read(db, user_id: int) -> int:
    from sqlalchemy import update
    result = await db.execute(
        update(Notification)
        .where(Notification.user_id == user_id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    return result.rowcount
```

### 7.2 通知 API

| 方法 | 路径 | 说明 | 角色 |
|------|------|------|------|
| GET | `/api/v1/notifications` | 当前用户通知列表（默认最近 50 条） | 任意登录用户 |
| POST | `/api/v1/notifications/{id}/read` | 标记单条已读 | 任意登录用户 |
| POST | `/api/v1/notifications/read-all` | 标记全部已读 | 任意登录用户 |

**GET `/api/v1/notifications` 响应：**

```json
{
  "items": [
    {
      "id": 12,
      "type": "sla_warning",
      "title": "⚠️ 工单 #TK-20260809-0015 即将超时",
      "message": "首次响应截止时间剩余不足 1小时，请及时处理。",
      "data": {"ticket_id": 15, "sla_record_id": 8, "stage": "supervisor_1h"},
      "is_read": false,
      "created_at": "2026-08-09T14:30:00Z"
    }
  ],
  "unread_count": 3
}
```

---

## 八、SLA 查询 API

### 8.1 工单 SLA 详情

| 方法 | 路径 | 说明 | 角色 |
|------|------|------|------|
| GET | `/api/v1/tickets/{id}/sla` | 工单 SLA 完整详情 | 有权限查看该工单的用户 |

**响应：**

```json
{
  "ticket_id": 15,
  "priority": "P1",
  "first_resp_hours": 2,
  "resolution_hours": 8,
  "first_resp_due": "2026-08-09T16:30:00Z",
  "resolution_due": "2026-08-10T06:30:00Z",
  "first_resp_at": null,
  "resolved_at": null,
  "first_resp_breached": false,
  "resolution_breached": false
}
```

### 8.2 管理后台超时列表

| 方法 | 路径 | 说明 | 角色 |
|------|------|------|------|
| GET | `/api/v1/admin/sla/overdue` | 所有已超时工单 | admin / supervisor |

**Query Params：** `breach_type`（`first_resp` | `resolution` | 不传则全部）

### 8.3 工单列表/详情嵌入 SLA 摘要

与 `ARCHITECTURE.md` 保持一致，在 `GET /api/v1/tickets` 和 `GET /api/v1/tickets/{id}` 的响应中嵌入：

```json
{
  "id": 15,
  "ticket_no": "TK-20260809-0015",
  "sla": {
    "first_resp_due": "2026-08-09T16:30:00Z",
    "resolution_due": "2026-08-10T06:30:00Z",
    "first_resp_breached": false,
    "resolution_breached": false
  }
}
```

---

## 九、与现有代码的集成点

| 集成点 | 已有文件 | 扩展方式 |
|--------|----------|----------|
| 工单创建 | `app/services/ticket_service.py` | `create_ticket()` 中 `db.flush()` 后调用 `create_sla_record()` |
| 工单回复 | `app/services/ticket_service.py` | `create_reply()` 中检测首次客服回复，更新 `first_resp_at` |
| 状态流转 | `app/services/ticket_service.py` | `update_ticket_status()` 中 `resolved` 时更新 `resolved_at` |
| Celery Worker | `celery_worker.py` | 注册 `app.tasks.sla_tasks` |
| 主路由 | `app/main.py` | include `sla` router（如有）和 `notifications` router |
| 邮件发送 | `app/services/mailer.py` | 懒加载调用 `Mailer.send()`（可选，MVP 先站内信） |

---

## 十、测试策略

目标：**≥14 条后端测试**

| 维度 | 数量 | 示例 |
|------|------|------|
| P0 正向 — SLA 创建 | 2 | 分类有配置时按配置创建、分类无配置时用全局 fallback |
| P0 正向 — 时间捕获 | 2 | 首次回复记录 `first_resp_at`、标记 resolved 记录 `resolved_at` |
| P0 正向 — 扫描 | 3 | 3h 预警触发、1h 预警触发、超时标记触发 |
| P0 正向 — 通知 | 2 | 创建通知、标记已读、查询列表 |
| P0 异常 | 2 | 短 SLA（如 1h）不触发 3h 预警、重复扫描不重复通知 |
| P1 边界 | 2 | 刚好在边界上的工单、已关闭/已解决工单不再扫描 |
| P1 权限 | 1 | 用户只能标记自己的通知为已读 |

---

## 十一、验收标准

- [ ] 创建工单时自动生成 SLA 记录，截止时间正确
- [ ] 分类 SLA 配置为空时，使用全局 fallback
- [ ] 客服首次回复后，`first_resp_at` 被正确记录
- [ ] 工单标记 resolved 后，`resolved_at` 被正确记录
- [ ] Celery 扫描任务每 5 分钟运行，正确触发 3h/2h/1h 预警和超时标记
- [ ] 短 SLA（≤3h）不会触发不合理的提前预警
- [ ] 预警和超时通知正确写入 `notifications` 表
- [ ] 用户可通过 API 查询自己的通知列表并标记已读
- [ ] 后端测试 ≥14 条全部通过
