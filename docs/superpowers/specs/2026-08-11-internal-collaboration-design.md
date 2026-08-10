# M2-T6 内部协作（转交/协助）设计文档

> 版本: v1.0  
> 日期: 2026-08-11  
> 状态: 设计评审  
> 对应任务: M2-T6（转交/协助接口）、M2-T21（前端转交/协助 UI）

---

## 一、设计目标

实现工单内部协作机制：

- 客服可将工单转交给其他客服（记录转交原因），原客服仍可查看
- 客服可请求协助（@其他客服），被协助人参与处理但不改变主负责人
- 所有协作行为记录到协作历史，便于追溯和绩效考核
- 主管可手动调整工单负责人

---

## 二、范围与边界

**本设计包含：**

| 模块 | 说明 | 对应子任务 |
|------|------|-----------|
| 协作记录模型 | `ticket_collaborations` 表 | M2-T6 |
| 工单转交 API | 变更负责人 + 记录原因 | M2-T6 |
| 协助请求 API | 添加协助人 + 记录说明 | M2-T6 |
| 协作历史查询 | 工单详情嵌入协作记录 | M2-T6 |
| 前端转交 UI | 转交弹窗（选择客服 + 填写原因） | M2-T21 |
| 前端协助 UI | 协助请求弹窗（@客服 + 说明） | M2-T21 |

**本设计不包含（留给后续任务）：**

- 协助人权限细粒度控制（协助人是否可回复、仅可见等）
- 协作实时通知（WebSocket，MVP 先站内通知）
- 强制转交（主管绕过目标客服确认）
- 转交工作流审批（如主管审批后才能转交）

---

## 三、关键决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 转交 vs 指派 | 转交 = 变更 `assignee_id` + 记录原因；指派 = 直接设置 | 区分主动协作（转交）和系统行为（自动分派/主管指派） |
| 协助人存储 | 独立 `ticket_collaborations` 表，N:1 关联 ticket | 支持多协助人，不影响主工单表结构 |
| 转交后原客服可见 | 保留查看权限（通过角色数据范围） | 原客服可能需交接说明，且 `ticket_replies` 有作者记录 |
| 协作历史展示 | 嵌入工单详情时间线 | 与客户回复时间线合并，保持上下文一致 |
| 协助人回复权限 | 协助人 = agent 角色，可创建回复 | 简化权限，依赖现有角色校验 |

---

## 四、数据模型

### 4.1 `ticket_collaborations` — 协作记录表

```sql
CREATE TABLE ticket_collaborations (
    id              SERIAL PRIMARY KEY,
    ticket_id       INTEGER NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    type            VARCHAR(20) NOT NULL CHECK (type IN ('transfer', 'assist')),
    from_user_id    INTEGER REFERENCES users(id),  -- 发起者（转交人/请求人）
    to_user_id      INTEGER NOT NULL REFERENCES users(id),  -- 目标客服（接收人/协助人）
    reason          TEXT,  -- 转交原因 / 协助说明
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_collaborations_ticket ON ticket_collaborations(ticket_id);
CREATE INDEX idx_collaborations_to_user ON ticket_collaborations(to_user_id);
```

### 4.2 模型定义

```python
class TicketCollaboration(Base):
    __tablename__ = "ticket_collaborations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    ticket_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False
    )
    type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # "transfer" | "assist"
    from_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    to_user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    ticket: Mapped["Ticket"] = relationship("Ticket")
    from_user: Mapped["User | None"] = relationship("User", foreign_keys=[from_user_id])
    to_user: Mapped["User"] = relationship("User", foreign_keys=[to_user_id])
```

### 4.3 协作记录与工单的关系

```
tickets
  └── 1:N ticket_collaborations
        ├── transfer: from_user_id → to_user_id，同步更新 tickets.assignee_id
        └── assist: from_user_id → to_user_id，不改变 tickets.assignee_id
```

---

## 五、业务逻辑

### 5.1 工单转交

```python
async def transfer_ticket(db, ticket_id: int, from_user_id: int,
                         to_user_id: int, reason: str | None) -> Ticket:
    """
    将工单转交给另一名客服。
    约束：
      - 目标客服必须是 agent 角色
      - 目标客服不能是当前负责人
      - 记录转交原因到协作历史
    """
    from sqlalchemy import select

    ticket_result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id)
    )
    ticket = ticket_result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    # 校验目标客服
    target_result = await db.execute(
        select(User).where(User.id == to_user_id, User.role == "agent", User.is_active == True)
    )
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=400, detail="目标客服不存在或不可用")

    if ticket.assignee_id == to_user_id:
        raise HTTPException(status_code=400, detail="该客服已是当前负责人")

    # 创建协作记录
    collab = TicketCollaboration(
        ticket_id=ticket_id,
        type="transfer",
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        reason=reason[:500] if reason else None,
    )
    db.add(collab)

    # 更新工单负责人
    old_assignee = ticket.assignee_id
    ticket.assignee_id = to_user_id

    # 状态自动流转：若原状态非 in_progress，转为 in_progress
    if ticket.status == "open":
        ticket.status = "in_progress"

    # 通知新负责人（复用通知系统）
    from app.services.notification_service import create_notification
    await create_notification(
        db,
        user_id=to_user_id,
        type="ticket_transferred",
        title=f"工单 #{ticket.ticket_no} 已转交给你",
        message=f"来自 {old_assignee or '系统'} 的转交，原因：{reason or '无'}"[:200],
        data={"ticket_id": ticket.id, "ticket_no": ticket.ticket_no},
    )

    return ticket
```

### 5.2 协助请求

```python
async def request_assistance(db, ticket_id: int, from_user_id: int,
                            to_user_id: int, reason: str | None) -> TicketCollaboration:
    """
    请求另一名客服协助处理工单。
    约束：
      - 目标客服必须是 agent 角色
      - 同一协助人同一工单只能有一条未完成的 assist 记录
    """
    from sqlalchemy import select, and_

    ticket_result = await db.execute(
        select(Ticket).where(Ticket.id == ticket_id)
    )
    ticket = ticket_result.scalar_one_or_none()
    if not ticket:
        raise HTTPException(status_code=404, detail="工单不存在")

    # 校验目标客服
    target_result = await db.execute(
        select(User).where(User.id == to_user_id, User.role == "agent", User.is_active == True)
    )
    target = target_result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=400, detail="目标客服不存在或不可用")

    # 检查重复协助
    dup_result = await db.execute(
        select(TicketCollaboration).where(
            and_(
                TicketCollaboration.ticket_id == ticket_id,
                TicketCollaboration.type == "assist",
                TicketCollaboration.to_user_id == to_user_id,
            )
        )
    )
    if dup_result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="该客服已在协助此工单")

    collab = TicketCollaboration(
        ticket_id=ticket_id,
        type="assist",
        from_user_id=from_user_id,
        to_user_id=to_user_id,
        reason=reason[:500] if reason else None,
    )
    db.add(collab)

    # 通知协助人
    from app.services.notification_service import create_notification
    await create_notification(
        db,
        user_id=to_user_id,
        type="assistance_requested",
        title=f"协助请求：工单 #{ticket.ticket_no}",
        message=f"请求协助原因：{reason or '无'}"[:200],
        data={"ticket_id": ticket.id, "ticket_no": ticket.ticket_no},
    )

    return collab
```

### 5.3 协作历史查询

```python
async def get_collaboration_history(db, ticket_id: int) -> list[TicketCollaboration]:
    result = await db.execute(
        select(TicketCollaboration)
        .options(
            selectinload(TicketCollaboration.from_user),
            selectinload(TicketCollaboration.to_user),
        )
        .where(TicketCollaboration.ticket_id == ticket_id)
        .order_by(TicketCollaboration.created_at.desc())
    )
    return result.scalars().all()
```

---

## 六、API 设计

### 6.1 转交工单

| 方法 | 路径 | 说明 | 角色 |
|------|------|------|------|
| POST | `/api/v1/tickets/{id}/transfer` | 转交工单给指定客服 | agent / supervisor / admin |

**Request:**
```json
{
  "to_user_id": 3,
  "reason": "该客户需要技术专家支持，超出我当前能力范围"
}
```

**Response (200):**
```json
{
  "id": 15,
  "ticket_no": "TK-20260809-0015",
  "assignee_id": 3,
  "status": "in_progress",
  "collaboration": {
    "id": 7,
    "type": "transfer",
    "from_user": {"id": 2, "username": "agent01"},
    "to_user": {"id": 3, "username": "agent02"},
    "reason": "该客户需要技术专家支持...",
    "created_at": "2026-08-09T15:30:00Z"
  }
}
```

### 6.2 请求协助

| 方法 | 路径 | 说明 | 角色 |
|------|------|------|------|
| POST | `/api/v1/tickets/{id}/assist` | 请求指定客服协助 | agent / supervisor / admin |

**Request:**
```json
{
  "to_user_id": 4,
  "reason": "需要帮忙确认数据库配置"
}
```

**Response (201):**
```json
{
  "id": 8,
  "type": "assist",
  "from_user": {"id": 2, "username": "agent01"},
  "to_user": {"id": 4, "username": "agent03"},
  "reason": "需要帮忙确认数据库配置",
  "created_at": "2026-08-09T15:35:00Z"
}
```

### 6.3 工单详情嵌入协作历史

扩展 `GET /api/v1/tickets/{id}` 响应，增加 `collaborations` 数组：

```json
{
  "id": 15,
  "ticket_no": "TK-20260809-0015",
  "collaborations": [
    {
      "id": 7,
      "type": "transfer",
      "from_user": {"id": 2, "username": "agent01"},
      "to_user": {"id": 3, "username": "agent02"},
      "reason": "...",
      "created_at": "2026-08-09T15:30:00Z"
    },
    {
      "id": 8,
      "type": "assist",
      "from_user": {"id": 3, "username": "agent02"},
      "to_user": {"id": 4, "username": "agent03"},
      "reason": "...",
      "created_at": "2026-08-09T16:00:00Z"
    }
  ]
}
```

---

## 七、与现有代码的集成点

| 集成点 | 已有文件 | 扩展方式 |
|--------|----------|----------|
| 工单详情 | `app/routers/tickets.py` | `GET /tickets/{id}` 增加 `collaborations` 序列化 |
| 转交/协助 | `app/routers/tickets.py` | 新增 `POST /tickets/{id}/transfer` 和 `POST /tickets/{id}/assist` |
| 通知系统 | `app/services/notification_service.py` | 复用 `create_notification()` 通知目标客服 |
| 数据范围 | `app/services/ticket_service.py` | 协助人（to_user_id）应有工单读取权限，扩展查询条件 |
| Alembic 迁移 | `alembic/versions/` | 新增 `ticket_collaborations` 表迁移 |

---

## 八、测试策略

目标：**≥10 条后端测试**

| 维度 | 数量 | 示例 |
|------|------|------|
| P0 正向 — 转交 | 2 | 成功转交，assignee_id 变更；转交原因正确记录 |
| P0 正向 — 协助 | 2 | 成功创建 assist 记录；通知目标客服 |
| P0 异常 — 转交 | 3 | 目标非 agent 400；转交给自己 400；工单不存在 404 |
| P0 异常 — 协助 | 2 | 重复协助 400；目标非 agent 400 |
| P1 权限 | 1 | customer 角色调用转交/协助 403 |

---

## 九、验收标准

- [ ] 客服可将工单转交给其他客服，记录转交原因
- [ ] 转交后工单负责人变更为目标客服，通知新负责人
- [ ] 客服可请求其他客服协助，同一工单同一协助人不可重复
- [ ] 协助请求发送通知给被协助人
- [ ] 工单详情页展示完整协作历史（转交 + 协助）
- [ ] 协助人可见被协助工单（数据范围扩展）
- [ ] 转交时若工单状态为 open，自动变为 in_progress
- [ ] 后端测试 ≥10 条全部通过
- [ ] 前端转交/协助弹窗可正常使用

---

## 十、前端设计（M2-T21）

### 10.1 转交弹窗

在 **客服工单详情页**（`AgentTicketDetailView`）的「操作」区域增加「转交」按钮：

- 点击后弹出 Element Plus `Dialog`
- 选择目标客服：下拉列表（`GET /admin/agent-skills` 或专门的客服列表接口）
- 转交原因：文本域，最多 500 字，提示"请说明转交原因..."
- 确认按钮，提交后刷新工单详情

### 10.2 协助请求弹窗

在同一「操作」区域增加「请求协助」按钮：

- 弹窗中选择目标客服（可多选？MVP 单选）
- 协助说明：文本域，最多 500 字
- 提交后显示成功提示，协助人出现在工单详情协作历史中

### 10.3 协作历史展示

在工单详情页的时间线中，**协作记录与客户回复混合展示**，按时间排序：
- 转交记录：显示 "🔄 agent01 转交给 agent02：原因..."
- 协助记录：显示 "🤝 agent01 请求 agent03 协助：说明..."
- 使用不同图标和颜色区分回复与协作记录

