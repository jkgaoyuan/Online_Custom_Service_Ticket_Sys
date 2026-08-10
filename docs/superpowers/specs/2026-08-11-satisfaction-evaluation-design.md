# M2-T12/T13 满意度评价系统设计文档

> 版本: v1.0  
> 日期: 2026-08-11  
> 状态: 设计评审  
> 对应任务: M2-T12（评价接口）、M2-T13（评价邀请触发）、M2-T19（前端评价弹窗）

---

## 一、设计目标

实现工单闭环反馈机制：

- 工单关闭后自动触发满意度评价邀请（站内通知 + 可选邮件）
- 客户可提交评价（满意/一般/不满意 + 可选文字反馈）
- 评价数据用于统计报表中的满意度指标和客服绩效评估
- 评价提交后不可修改（确保数据真实性）

---

## 二、范围与边界

**本设计包含：**

| 模块 | 说明 | 对应子任务 |
|------|------|-----------|
| 评价数据模型 | 复用 `tickets.satisfaction` / `satisfaction_note` 字段，无需新增表 | M2-T12 |
| 评价提交 API | 客户提交/更新评价的接口 | M2-T12 |
| 评价查询 API | 工单详情嵌入评价、管理后台满意度列表 | M2-T12 |
| 评价邀请触发 | 工单 `closed` 时自动创建通知 | M2-T13 |
| 前端评价弹窗 | 客户视角的评价提交界面 | M2-T19 |

**本设计不包含（留给后续任务）：**

- 邮件发送评价邀请（邮件通道已在 M2-T11 预留，MVP 先站内信）
- 评价提醒重发（如客户 3 天未评价，后续可扩展）
- 评价匿名/实名开关（默认实名，与 requester 关联）
- 评价 NPS 评分（仅需 3 档，不满足 NPS 需求）

---

## 三、关键决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 评价存储 | 复用 `tickets` 表字段 | ARCHITECTURE.md 已预留 `satisfaction` + `satisfaction_note`，零迁移 |
| 评价可修改 | 提交后不可修改 | 确保客服绩效数据真实性，避免客户事后修改 |
| 评价触发时机 | 状态流转至 `closed` 时 | 工单生命周期终点，自然触发点 |
| 通知类型 | 站内通知（`notification`） | 复用 M2-T10 已建立的通知基础设施 |
| 评价对象 | 整条工单（非单个客服） | 客户感知的是整体服务体验，简化实现 |
| 未评价处理 | 统计时按“未评价”排除，不参与平均 | 避免强制评价带来的失真 |

---

## 四、数据模型

### 4.1 复用 `tickets` 表已有字段

```sql
-- ARCHITECTURE.md 已定义，无需迁移
ALTER TABLE tickets  -- 仅文档说明，实际已存在
    ADD COLUMN satisfaction VARCHAR(20)
        CHECK (satisfaction IN ('satisfied','neutral','dissatisfied')),
    ADD COLUMN satisfaction_note TEXT,
    ADD COLUMN satisfaction_at TIMESTAMP;  -- 新增：记录评价时间
```

> **注意**：`satisfaction_at` 为本次设计新增字段，需 Alembic 迁移。

### 4.2 字段语义

| 字段 | 类型 | 说明 |
|------|------|------|
| `satisfaction` | `VARCHAR(20)` | `satisfied` / `neutral` / `dissatisfied` / `NULL`（未评价） |
| `satisfaction_note` | `TEXT` | 客户文字反馈，可选，最大 500 字 |
| `satisfaction_at` | `TIMESTAMP` | 评价提交时间，NULL 表示未评价 |

### 4.3 模型更新

```python
class Ticket(Base):
    __tablename__ = "tickets"

    # ... 现有字段 ...

    satisfaction: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
    )
    satisfaction_note: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    satisfaction_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )
```

---

## 五、业务逻辑

### 5.1 评价邀请触发

在 `transition_ticket_status()` service 中，当目标状态为 `closed` 时：

```python
async def transition_ticket_status(db, ticket_id, new_status, actor_id):
    # ... 现有状态校验逻辑 ...

    if new_status == "closed" and old_status != "closed":
        # 触发评价邀请
        await _trigger_satisfaction_invite(db, ticket)

    # ... 提交事务 ...

async def _trigger_satisfaction_invite(db, ticket: Ticket):
    """工单关闭时，向客户发送评价邀请通知。"""
    from app.services.notification_service import create_notification

    await create_notification(
        db,
        user_id=ticket.requester_id,
        type="satisfaction_invite",
        title=f"工单 #{ticket.ticket_no} 已关闭，请评价我们的服务",
        message="您的工单已处理完毕，点击评价本次服务体验。",
        data={
            "ticket_id": ticket.id,
            "ticket_no": ticket.ticket_no,
        },
    )
```

> 通知发送由 `transition_ticket_status` 的调用方（router）统一 `commit`，通知 service 只 `add` 不 `flush/commit`。

### 5.2 评价提交

```python
async def submit_satisfaction(db, ticket_id: int, user_id: int,
                               rating: str, note: str | None) -> Ticket:
    """
    客户提交满意度评价。
    约束：
      - 工单必须已关闭
      - 只能由 requester 本人评价
      - 已评价后不可修改（satisfaction_at 非空则拒绝）
    """
    from sqlalchemy import select

    result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id)
    )
    ticket = result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    if ticket.requester_id != user_id:
        raise HTTPException(status_code=403, detail="只能评价自己的工单")

    if ticket.status != "closed":
        raise HTTPException(status_code=400, detail="工单未关闭，无法评价")

    if ticket.satisfaction_at is not None:
        raise HTTPException(status_code=400, detail="该工单已评价，不可修改")

    if rating not in ("satisfied", "neutral", "dissatisfied"):
        raise HTTPException(status_code=400, detail="无效的评价等级")

    ticket.satisfaction = rating
    ticket.satisfaction_note = note[:500] if note else None
    ticket.satisfaction_at = datetime.utcnow()

    return ticket
```

### 5.3 评价查询

工单详情自动嵌入评价信息（扩展现有 `GET /tickets/{id}` 响应）：

```json
{
  "id": 15,
  "ticket_no": "TK-20260809-0015",
  "status": "closed",
  "satisfaction": {
    "rating": "satisfied",
    "note": "问题解决很及时，感谢！",
    "created_at": "2026-08-09T18:00:00Z"
  }
}
```

> 若 `satisfaction_at` 为 NULL，则 `satisfaction` 字段为 `null`。

---

## 六、API 设计

### 6.1 提交评价

| 方法 | 路径 | 说明 | 角色 |
|------|------|------|------|
| POST | `/api/v1/tickets/{id}/satisfaction` | 提交/更新评价（仅首次） | customer（仅本人工单） |

**Request:**
```json
{
  "rating": "satisfied",
  "note": "问题解决很及时，感谢！"
}
```

**Response (200):**
```json
{
  "id": 15,
  "ticket_no": "TK-20260809-0015",
  "satisfaction": {
    "rating": "satisfied",
    "note": "问题解决很及时，感谢！",
    "created_at": "2026-08-09T18:00:00Z"
  }
}
```

**错误码：**
- `400` — 工单未关闭 / 已评价 / 无效 rating
- `403` — 非本人工单
- `404` — 工单不存在

### 6.2 管理后台满意度列表（供报表调用）

报表统计接口中，满意度维度从 `tickets` 表直接聚合：

```sql
SELECT
    satisfaction,
    COUNT(*) AS count
FROM tickets
WHERE satisfaction IS NOT NULL
  AND closed_at BETWEEN :start AND :end
GROUP BY satisfaction;
```

平均满意度（映射为 3/2/1 分）：
```sql
SELECT AVG(CASE satisfaction
    WHEN 'satisfied' THEN 3
    WHEN 'neutral' THEN 2
    WHEN 'dissatisfied' THEN 1
END) AS avg_score
FROM tickets
WHERE satisfaction IS NOT NULL
  AND closed_at BETWEEN :start AND :end;
```

---

## 七、与现有代码的集成点

| 集成点 | 已有文件 | 扩展方式 |
|--------|----------|----------|
| 工单状态流转 | `app/services/ticket_service.py` | `transition_ticket_status()` 中增加 `closed` 触发评价邀请逻辑 |
| 通知创建 | `app/services/notification_service.py` | 复用 `create_notification()` |
| 工单详情响应 | `app/routers/tickets.py` | `GET /tickets/{id}` 序列化中增加 `satisfaction` 对象 |
| 评价提交 | 新增 | 在 `tickets.py` router 中新增 `POST /tickets/{id}/satisfaction` |
| 报表统计 | `app/services/report_service.py` | 满意度统计从 `tickets` 表直接聚合 |
| Alembic 迁移 | `alembic/versions/` | 新增 `satisfaction_at` 字段迁移 |

---

## 八、测试策略

目标：**≥8 条后端测试**

| 维度 | 数量 | 示例 |
|------|------|------|
| P0 正向 — 提交评价 | 2 | 有效 rating 提交成功；note 为空也可提交 |
| P0 正向 — 触发邀请 | 2 | 流转至 closed 时创建通知；通知内容含 ticket_no |
| P0 异常 | 3 | 未关闭工单提交评价 400；非本人工单 403；已评价再次提交 400；无效 rating 400 |
| P1 边界 | 1 | note 超长自动截断至 500 字 |

---

## 九、验收标准

- [ ] 工单关闭时，requester 收到站内评价邀请通知
- [ ] 客户可对已关闭工单提交满意/一般/不满意评价 + 文字反馈
- [ ] 已评价工单不可再次评价（返回 400）
- [ ] 未关闭工单不可评价（返回 400）
- [ ] 非本人工单不可评价（返回 403）
- [ ] 工单详情 API 返回嵌入满意度信息
- [ ] 报表统计中满意度数据按实际评价聚合
- [ ] 后端测试 ≥8 条全部通过
- [ ] 前端评价弹窗可正常提交并显示成功状态

---

## 十、前端设计（M2-T19）

### 10.1 评价弹窗组件

在客户 **工单详情页**（`TicketDetailView`）中，当工单状态为 `closed` 且 `satisfaction` 为 `null` 时：

- 页面底部显示评价邀请卡片（非弹窗，嵌入页面）
- 三档按钮：😊 满意 / 😐 一般 / 😞 不满意
- 选中后展开文字反馈文本域（可选，最多 500 字）
- 提交按钮，成功后显示评价结果摘要，隐藏表单

### 10.2 已评价展示

若工单已评价，详情页底部显示评价卡片：
- 评价等级（带图标）
- 文字反馈（如有）
- 评价时间

### 10.3 通知中心跳转

客户从通知中心点击评价邀请通知，直接跳转至对应工单详情页，并自动滚动到评价区域。

