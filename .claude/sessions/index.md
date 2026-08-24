# 历史进度索引

- **2026-08-23 13:40** — 修复前后端接口不一致（categories / sla / agentSkills 路径与字段对齐），补充 admin agent-skills 返回字段与 /admin/sla/rules 路由；修复测试环境 PostgreSQL DDL 竞态（`pg_type_typname_nsp_index` 冲突 + `Event loop is closed`），`conftest.py` 采用全局标志 + TRUNCATE + `engine.dispose()` 方案；后端 363 测试全部通过；10 个文件修改未提交。
- **2026-08-22 00:15** — 执行 M2-T23 后端单元测试覆盖核心业务≥80%：修复 collaboration_service ValidationException 导入和异常类型，新增 5 个测试文件共 89 个用例（agent_skills router 38 + auth_service 18 + user_service 15 + email_tasks 4 + security 14），关键模块覆盖率大幅提升（auth_service 44%→91%、user_service 42%→93%、email_tasks 76%→100%、security 90%→100%），总体覆盖率 75%→80%；1 个 commit 已提交。
- **2026-08-21 20:50** — 检查 M1 前端页面完成状态，修复客户 TODO 仪表盘（登录后重定向到「我的工单」）、全角色布局增加退出登录按钮、客户工单详情页补充回复框；客服工作台从 TODO 实现为完整统计卡片+最近工单；1 个 commit 已提交，待用户手动推送。
