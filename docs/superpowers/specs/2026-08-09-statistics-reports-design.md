# T007 统计报表与导出 — 后端设计文档

> 版本: v1.0  
> 日期: 2026-08-09  
> 状态: 已确认  
> 对应任务: T007（统计报表与导出）

---

## 一、设计目标

实现工单系统的统计聚合查询与报表导出功能（后端部分），覆盖：
- 综合概览（工单总量、状态分布、SLA 达标率、满意度）
- 客服绩效（工单量、平均首次响应时长、平均解决时长）
- 分类分布（各分类工单量占比）
- 时段趋势（按日/周/月统计工单创建/解决趋势）
- 满意度统计（整体分布与参与率）
- 异步 Excel/CSV 导出

---

## 二、范围与边界

**包含（T007 后端范围）：**
| 模块 | 说明 |
|------|------|
| 统计聚合 API | 5 个查询端点，全部在 PostgreSQL 层聚合 |
| 报表导出 API | 提交异步任务 + 查询状态/下载 |
| Celery 导出任务 | pandas + openpyxl 生成文件 |

**不包含（后续扩展）：**
- 前端仪表盘 / 报表页面（T007-Frontend）
- 导出文件自动清理（M3 按需扩展）
- 报表缓存 / 物化视图（数据量增大后评估）

---

## 三、技术方案

**聚合方式：** SQL 原生聚合（`COUNT/AVG/DATE_TRUNC/FILTER`），通过 SQLAlchemy 直接查询。  
**导出方式：** Celery 异步任务，pandas DataFrame → `.xlsx` / `.csv`。  
**文件存储：** 本地文件系统（`settings.EXPORT_DIR`，默认 `./exports`），24h 内有效，暂不自动清理。

---

## 四、数据模型

复用现有模型，不新增表：

- `tickets` — 工单主体（`status`, `priority`, `category_id`, `assignee_id`, `created_at`, `resolved_at`, `satisfaction`）
- `sla_records` — SLA 记录（`first_resp_at`, `first_resp_breached`, `resolution_breached`）
- `ticket_replies` — 回复记录（`author_id`, `created_at`, `is_internal`）
- `categories` — 分类信息（`name`）
- `users` — 用户信息（`username`）

**关键设计决策：客服绩效的「首次响应」归属**  
`SLARecord.first_resp_at` 只记录时间，不记录回复人。为避免归属错误（A 分配但 B 先回复），**首次响应时间从 `ticket_replies` 计算** — 取每个 ticket 最早的非内部回复，按 `author_id` 分组。解决/分配数量仍按 `assignee_id`。

---

## 五、API 设计

所有接口统一前缀 `/api/v1/admin/reports`，权限要求 `supervisor` 或 `admin`。

### 5.1 GET /overview

综合概览，默认统计全部时间范围（不限制日期）。

**响应：**
```json
{
  "total_tickets": 1250,
  "today_new": 12,
  "week_new": 87,
  "month_new": 342,
  "status_distribution": {
    "open": 45,
    "in_progress": 120,
    "waiting": 30,
    "resolved": 800,
    "closed": 255
  },
  "sla_compliance_rate": 0.92,
  "avg_satisfaction": 4.2
}
```

### 5.2 GET /agent-performance

客服绩效统计。

**Query：** `start_date`（ISO 日期，含）、`end_date`（ISO 日期，含），默认最近 30 天。  
**限制：** 单次查询最大日期范围 1 年，超出返回 422。

**响应：**
```json
[
  {
    "agent_id": 3,
    "agent_name": "alice",
    "total_assigned": 45,
    "resolved_count": 38,
    "avg_first_resp_hours": 2.5,
    "avg_resolution_hours": 18.3
  }
]
```

**首次响应 SQL 逻辑：**
```sql
WITH first_replies AS (
  SELECT DISTINCT ON (ticket_id) ticket_id, author_id, created_at
  FROM ticket_replies
  WHERE is_internal = false
  ORDER BY ticket_id, created_at ASC
)
SELECT 
  fr.author_id,
  AVG(EXTRACT(EPOCH FROM (fr.created_at - t.created_at))/3600) as avg_first_resp_hours
FROM first_replies fr
JOIN tickets t ON fr.ticket_id = t.id
WHERE t.created_at BETWEEN :start AND :end
GROUP BY fr.author_id
```

### 5.3 GET /category-distribution

分类工单量分布。

**Query：** 同 5.2。

**响应：**
```json
[
  {
    "category_id": 1,
    "category_name": "故障",
    "count": 320,
    "percentage": 0.256
  }
]
```

### 5.4 GET /trend

时段趋势。

**Query：** `granularity`（`day`/`week`/`month`，默认 `day`）、`start_date`、`end_date`。  
**限制：** `granularity` 严格白名单，否则 422。

**响应：**
```json
[
  {
    "bucket": "2026-08-01",
    "created": 15,
    "resolved": 12
  }
]
```

**SQL 策略：** 使用 `generate_series` 生成完整时间轴，LEFT JOIN `tickets` 的 created/resolved 子查询，确保无数据日期返回 0。

### 5.5 GET /satisfaction

满意度统计。

**Query：** 同 5.2。

**响应：**
```json
{
  "distribution": {
    "satisfied": 120,
    "neutral": 30,
    "dissatisfied": 10
  },
  "avg_score": 4.15,
  "participation_rate": 0.35,
  "total_rated": 160,
  "total_in_range": 450
}
```

**注意：** `participation_rate = total_rated / total_in_range`，`total_in_range` 为时间范围内已关闭工单总数（`status='closed'` 或 `closed_at IS NOT NULL`）。

### 5.6 POST /export

提交导出任务。

**Body：**
```json
{
  "report_type": "agent_performance",
  "format": "xlsx",
  "start_date": "2026-07-01",
  "end_date": "2026-07-31",
  "filters": {}
}
```

- `report_type`：枚举 `overview`, `agent_performance`, `category_distribution`, `trend`, `satisfaction`
- `format`：枚举 `xlsx`, `csv`
- `filters`：预留，暂不实现复杂筛选

**响应：**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "pending"
}
```

### 5.7 GET /export/{task_id}

查询导出任务状态。

**响应（pending）：**
```json
{
  "task_id": "a1b2c3d4-...",
  "status": "pending",
  "download_url": null
}
```

**响应（completed）：**
```json
{
  "task_id": "a1b2c3d4-...",
  "status": "completed",
  "download_url": "/api/v1/admin/reports/exports/download/a1b2c3d4-..."
}
```

### 5.8 GET /exports/download/{task_id}

下载导出的文件。

- `task_id` 严格校验 UUID4 格式
- 返回 `FileResponse`，完成后文件流式传输
- 需要 supervisor/admin 权限

---

## 六、服务层设计

### 6.1 `app/services/report_service.py`

函数清单：

| 函数 | 说明 |
|------|------|
| `get_overview(db)` | 综合概览聚合 |
| `get_agent_performance(db, start_date, end_date)` | 客服绩效 |
| `get_category_distribution(db, start_date, end_date)` | 分类分布 |
| `get_trend(db, granularity, start_date, end_date)` | 时段趋势 |
| `get_satisfaction_stats(db, start_date, end_date)` | 满意度统计 |
| `validate_date_range(start_date, end_date, max_days=365)` | 日期范围校验 |

### 6.2 `app/tasks/export_tasks.py`

- `@shared_task(name="tasks.generate_report_export")`
- 根据 `report_type` 调用对应的 report_service 函数
- pandas DataFrame 组装数据
- `to_excel()` / `to_csv()` 写入 `settings.EXPORT_DIR / {task_id}.{format}`
- **公式注入防护：** 导出前遍历文本字段，若值以 `= + - @` 开头，前置单引号 `'`

### 6.3 `app/routers/reports.py`

- 注册 `/api/v1/admin/reports` 路由
- 使用 `require_role(["supervisor", "admin"])` 权限依赖
- `POST /export` 提交 Celery 任务，返回 `task_id`

---

## 七、配置变更

`app/config.py` 新增：
```python
EXPORT_DIR: str = "./exports"
```

`backend/.gitignore` 新增：
```gitignore
/exports/
```

`app/main.py` 注册 `reports` router。

---

## 八、安全设计

| 风险 | 防护措施 |
|------|----------|
| 路径遍历 | `task_id` 强制 UUID4，下载接口正则校验 `^[a-f0-9\-]{36}$` |
| 公式注入 | 导出时文本字段前缀清洗（`= + - @` → 加 `'`） |
| 权限绕过 | 所有接口使用 `require_role(["supervisor", "admin"])` |
| 资源耗尽 | 日期范围上限 1 年；导出文件大小由查询范围间接限制 |
| SQL 注入 | `granularity` 严格白名单；其他参数使用 SQLAlchemy bind param |

---

## 九、测试策略

目标：后端 ≥15 条测试。

### `tests/test_reports.py`

| 编号 | 用例 | 维度 |
|------|------|------|
| API-RPT-101 | overview 正常返回 | P0 正向 |
| API-RPT-102 | agent-performance 正常返回 | P0 正向 |
| API-RPT-103 | category-distribution 正常返回 | P0 正向 |
| API-RPT-104 | trend (day) 正常返回 | P0 正向 |
| API-RPT-105 | satisfaction 正常返回 | P0 正向 |
| API-RPT-201 | 空数据返回零值/空列表 | P1 边界 |
| API-RPT-202 | start_date > end_date 返回 422 | P1 边界 |
| API-RPT-203 | 日期范围 > 1 年返回 422 | P1 边界 |
| API-RPT-204 | granularity 非法值返回 422 | P1 边界 |
| API-RPT-301 | customer 访问报表接口 403 | P1 权限 |
| API-RPT-302 | agent 访问报表接口 403 | P1 权限 |

### `tests/test_export.py`

| 编号 | 用例 | 维度 |
|------|------|------|
| API-EXP-101 | 提交 xlsx 导出并成功下载 | P0 正向 |
| API-EXP-102 | 提交 csv 导出 | P0 正向 |
| API-EXP-201 | 无效 report_type 返回 422 | P1 边界 |
| API-EXP-202 | 任务完成前查询状态返回 pending | P1 边界 |

---

## 十、与现有代码的集成点

| 集成点 | 已有文件 | 扩展方式 |
|--------|----------|----------|
| 配置 | `app/config.py` | 新增 `EXPORT_DIR` |
| 路由注册 | `app/main.py` | `include_router(reports.router)` |
| 认证依赖 | `app/dependencies.py` | 复用 `get_current_user`, `require_role` |
| Celery Worker | `celery_worker.py` | 无需新增 beat_schedule |
| 测试工厂 | `tests/conftest.py` | 新增 `_create_resolved_ticket` 辅助函数 |

---

## 十一、关键决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 首次响应归属 | 从 `ticket_replies` 计算，不按 `assignee_id` | `SLARecord` 未存回复人，避免归属错误 |
| 聚合方式 | SQL 原生聚合 | 性能最优，代码简洁，与现有技术栈一致 |
| 导出存储 | 本地文件系统 | YAGNI，M3 再评估对象存储 |
| 文件清理 | 暂不实现 | MVP 阶段，部署环境可临时处理 |
| 缓存 | 暂不加 Redis 缓存 | 报表数据量小，SQL 聚合在 MVP 规模足够快 |

---

## 十二、验收标准

- [ ] 5 个统计接口返回正确聚合数据
- [ ] 日期范围校验、granularity 白名单、权限隔离正常工作
- [ ] Excel/CSV 导出可提交、可下载、内容正确
- [ ] 导出文件对公式注入有防护
- [ ] 后端测试 ≥15 条通过
- [ ] 零 T007 引入的回归失败
