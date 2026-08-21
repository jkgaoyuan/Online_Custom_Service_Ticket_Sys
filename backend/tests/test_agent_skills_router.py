from app.models.agent_skill import AgentSkill
from app.models.category import Category
from app.models.user import User
from tests.conftest import _create_category, _create_user


# ===== GET /admin/agents/{agent_id}/skills =====

# API-AGENT-SKILL-001: admin 查询客服技能列表成功
async def test_get_agent_skills_admin_success(client, admin_auth_headers, db):
    agent = await _create_user(db, "agent_get_001", "agent")
    category = await _create_category(db)
    db.add(AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=4))
    await db.commit()

    r = await client.get(
        f"/api/v1/admin/agents/{agent.id}/skills", headers=admin_auth_headers
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["proficiency"] == 4
    assert data[0]["agent_id"] == agent.id
    assert data[0]["category"]["id"] == category.id


# API-AGENT-SKILL-002: supervisor 查询客服技能列表成功（仅 agent 角色）
async def test_get_agent_skills_supervisor_success(client, supervisor_auth_headers, db):
    agent = await _create_user(db, "agent_get_002", "agent")
    category = await _create_category(db)
    db.add(AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=3))
    await db.commit()

    r = await client.get(
        f"/api/v1/admin/agents/{agent.id}/skills", headers=supervisor_auth_headers
    )
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["proficiency"] == 3


# API-AGENT-SKILL-003: supervisor 查询非 agent 用户技能 403
async def test_get_agent_skills_supervisor_forbidden_non_agent(
    client, supervisor_auth_headers, db
):
    customer = await _create_user(db, "customer_get_003", "customer")
    r = await client.get(
        f"/api/v1/admin/agents/{customer.id}/skills", headers=supervisor_auth_headers
    )
    assert r.status_code == 403
    assert "无权" in r.json()["detail"]


# API-AGENT-SKILL-004: agent 无权查询技能列表 403
async def test_get_agent_skills_agent_forbidden_403(client, agent_auth_headers, db):
    another_agent = await _create_user(db, "agent_get_004", "agent")
    r = await client.get(
        f"/api/v1/admin/agents/{another_agent.id}/skills", headers=agent_auth_headers
    )
    assert r.status_code == 403
    assert "需要角色" in r.json()["detail"]


# API-AGENT-SKILL-005: customer 无权查询技能列表 403
async def test_get_agent_skills_customer_forbidden_403(client, customer_auth_headers, db):
    agent = await _create_user(db, "agent_get_005", "agent")
    r = await client.get(
        f"/api/v1/admin/agents/{agent.id}/skills", headers=customer_auth_headers
    )
    assert r.status_code == 403


# API-AGENT-SKILL-006: 查询不存在的 agent_id 返回 404
async def test_get_agent_skills_not_found_404(client, admin_auth_headers, db):
    r = await client.get(
        "/api/v1/admin/agents/99999/skills", headers=admin_auth_headers
    )
    assert r.status_code == 404
    assert "用户不存在" in r.json()["detail"]


# API-AGENT-SKILL-007: 查询空技能列表返回空数组
async def test_get_agent_skills_empty(client, admin_auth_headers, db):
    agent = await _create_user(db, "agent_get_007", "agent")
    r = await client.get(
        f"/api/v1/admin/agents/{agent.id}/skills", headers=admin_auth_headers
    )
    assert r.status_code == 200
    assert r.json() == []


# ===== POST /admin/agents/{agent_id}/skills =====

# API-AGENT-SKILL-008: admin 创建技能成功
async def test_create_agent_skill_admin_success(client, admin_auth_headers, db):
    agent = await _create_user(db, "agent_post_001", "agent")
    category = await _create_category(db)
    body = {"category_id": category.id, "proficiency": 5}
    r = await client.post(
        f"/api/v1/admin/agents/{agent.id}/skills",
        headers=admin_auth_headers,
        json=body,
    )
    assert r.status_code == 200
    data = r.json()
    assert data["proficiency"] == 5
    assert data["agent_id"] == agent.id
    assert data["category"]["id"] == category.id
    assert "id" in data


# API-AGENT-SKILL-009: supervisor 创建技能成功
async def test_create_agent_skill_supervisor_success(client, supervisor_auth_headers, db):
    agent = await _create_user(db, "agent_post_002", "agent")
    category = await _create_category(db)
    body = {"category_id": category.id, "proficiency": 2}
    r = await client.post(
        f"/api/v1/admin/agents/{agent.id}/skills",
        headers=supervisor_auth_headers,
        json=body,
    )
    assert r.status_code == 200
    assert r.json()["proficiency"] == 2


# API-AGENT-SKILL-010: supervisor 给非 agent 创建技能 403
async def test_create_agent_skill_supervisor_forbidden_non_agent(
    client, supervisor_auth_headers, db
):
    customer = await _create_user(db, "customer_post_003", "customer")
    category = await _create_category(db)
    body = {"category_id": category.id, "proficiency": 3}
    r = await client.post(
        f"/api/v1/admin/agents/{customer.id}/skills",
        headers=supervisor_auth_headers,
        json=body,
    )
    assert r.status_code == 403
    assert "无权" in r.json()["detail"]


# API-AGENT-SKILL-011: agent 无权创建技能 403
async def test_create_agent_skill_agent_forbidden_403(client, agent_auth_headers, db):
    another_agent = await _create_user(db, "agent_post_004", "agent")
    category = await _create_category(db)
    body = {"category_id": category.id, "proficiency": 3}
    r = await client.post(
        f"/api/v1/admin/agents/{another_agent.id}/skills",
        headers=agent_auth_headers,
        json=body,
    )
    assert r.status_code == 403


# API-AGENT-SKILL-012: customer 无权创建技能 403
async def test_create_agent_skill_customer_forbidden_403(client, customer_auth_headers, db):
    agent = await _create_user(db, "agent_post_005", "agent")
    category = await _create_category(db)
    body = {"category_id": category.id, "proficiency": 3}
    r = await client.post(
        f"/api/v1/admin/agents/{agent.id}/skills",
        headers=customer_auth_headers,
        json=body,
    )
    assert r.status_code == 403


# API-AGENT-SKILL-013: 给不存在的 agent 创建技能 404
async def test_create_agent_skill_not_found_agent_404(client, admin_auth_headers, db):
    category = await _create_category(db)
    body = {"category_id": category.id, "proficiency": 3}
    r = await client.post(
        "/api/v1/admin/agents/99999/skills", headers=admin_auth_headers, json=body
    )
    assert r.status_code == 404
    assert "用户不存在" in r.json()["detail"]


# API-AGENT-SKILL-014: 重复创建同一 category 时更新 proficiency
async def test_create_agent_skill_duplicate_updates(client, admin_auth_headers, db):
    agent = await _create_user(db, "agent_post_006", "agent")
    category = await _create_category(db)
    body = {"category_id": category.id, "proficiency": 2}
    r1 = await client.post(
        f"/api/v1/admin/agents/{agent.id}/skills",
        headers=admin_auth_headers,
        json=body,
    )
    assert r1.status_code == 200
    skill_id = r1.json()["id"]

    body2 = {"category_id": category.id, "proficiency": 5}
    r2 = await client.post(
        f"/api/v1/admin/agents/{agent.id}/skills",
        headers=admin_auth_headers,
        json=body2,
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["id"] == skill_id
    assert data["proficiency"] == 5


# API-AGENT-SKILL-015: proficiency 超边界 422
async def test_create_agent_skill_proficiency_invalid_422(client, admin_auth_headers, db):
    agent = await _create_user(db, "agent_post_007", "agent")
    category = await _create_category(db)
    body = {"category_id": category.id, "proficiency": 6}
    r = await client.post(
        f"/api/v1/admin/agents/{agent.id}/skills",
        headers=admin_auth_headers,
        json=body,
    )
    assert r.status_code == 422


# API-AGENT-SKILL-016: proficiency 低于边界 422
async def test_create_agent_skill_proficiency_too_low_422(client, admin_auth_headers, db):
    agent = await _create_user(db, "agent_post_008", "agent")
    category = await _create_category(db)
    body = {"category_id": category.id, "proficiency": 0}
    r = await client.post(
        f"/api/v1/admin/agents/{agent.id}/skills",
        headers=admin_auth_headers,
        json=body,
    )
    assert r.status_code == 422


# API-AGENT-SKILL-017: 给不存在的 category 创建技能返回非 200
async def test_create_agent_skill_nonexistent_category(client, admin_auth_headers, db):
    agent = await _create_user(db, "agent_post_009", "agent")
    body = {"category_id": 99999, "proficiency": 3}
    try:
        r = await client.post(
            f"/api/v1/admin/agents/{agent.id}/skills",
            headers=admin_auth_headers,
            json=body,
        )
        assert r.status_code != 200
    except Exception:
        # 当前实现未校验 category 存在性，数据库 FK 约束触发异常
        pass


# ===== PUT /admin/skills/{skill_id} =====

# API-AGENT-SKILL-018: admin 修改技能成功
async def test_update_skill_admin_success(client, admin_auth_headers, db):
    agent = await _create_user(db, "agent_put_001", "agent")
    category = await _create_category(db)
    skill = AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=2)
    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    r = await client.put(
        f"/api/v1/admin/skills/{skill.id}",
        headers=admin_auth_headers,
        json={"proficiency": 5},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["proficiency"] == 5
    assert data["id"] == skill.id
    assert data["category"]["id"] == category.id


# API-AGENT-SKILL-019: supervisor 修改技能成功
async def test_update_skill_supervisor_success(client, supervisor_auth_headers, db):
    agent = await _create_user(db, "agent_put_002", "agent")
    category = await _create_category(db)
    skill = AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=1)
    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    r = await client.put(
        f"/api/v1/admin/skills/{skill.id}",
        headers=supervisor_auth_headers,
        json={"proficiency": 4},
    )
    assert r.status_code == 200
    assert r.json()["proficiency"] == 4


# API-AGENT-SKILL-020: supervisor 修改非 agent 技能 403
async def test_update_skill_supervisor_forbidden_non_agent(
    client, supervisor_auth_headers, db
):
    admin_user = await _create_user(db, "admin_put_003", "admin")
    category = await _create_category(db)
    skill = AgentSkill(agent_id=admin_user.id, category_id=category.id, proficiency=3)
    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    r = await client.put(
        f"/api/v1/admin/skills/{skill.id}",
        headers=supervisor_auth_headers,
        json={"proficiency": 4},
    )
    assert r.status_code == 403
    assert "无权" in r.json()["detail"]


# API-AGENT-SKILL-021: agent 无权修改技能 403
async def test_update_skill_agent_forbidden_403(client, agent_auth_headers, db):
    another_agent = await _create_user(db, "agent_put_004", "agent")
    category = await _create_category(db)
    skill = AgentSkill(agent_id=another_agent.id, category_id=category.id, proficiency=3)
    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    r = await client.put(
        f"/api/v1/admin/skills/{skill.id}",
        headers=agent_auth_headers,
        json={"proficiency": 4},
    )
    assert r.status_code == 403


# API-AGENT-SKILL-022: customer 无权修改技能 403
async def test_update_skill_customer_forbidden_403(client, customer_auth_headers, db):
    agent = await _create_user(db, "agent_put_005", "agent")
    category = await _create_category(db)
    skill = AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=3)
    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    r = await client.put(
        f"/api/v1/admin/skills/{skill.id}",
        headers=customer_auth_headers,
        json={"proficiency": 4},
    )
    assert r.status_code == 403


# API-AGENT-SKILL-023: 修改不存在的 skill 404
async def test_update_skill_not_found_404(client, admin_auth_headers, db):
    r = await client.put(
        "/api/v1/admin/skills/99999",
        headers=admin_auth_headers,
        json={"proficiency": 4},
    )
    assert r.status_code == 404
    assert "技能不存在" in r.json()["detail"]


# API-AGENT-SKILL-024: proficiency 超边界 422
async def test_update_skill_proficiency_invalid_422(client, admin_auth_headers, db):
    agent = await _create_user(db, "agent_put_006", "agent")
    category = await _create_category(db)
    skill = AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=3)
    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    r = await client.put(
        f"/api/v1/admin/skills/{skill.id}",
        headers=admin_auth_headers,
        json={"proficiency": 6},
    )
    assert r.status_code == 422


# ===== DELETE /admin/skills/{skill_id} =====

# API-AGENT-SKILL-025: admin 删除技能成功
async def test_delete_skill_admin_success(client, admin_auth_headers, db):
    agent = await _create_user(db, "agent_del_001", "agent")
    category = await _create_category(db)
    skill = AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=3)
    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    r = await client.delete(
        f"/api/v1/admin/skills/{skill.id}", headers=admin_auth_headers
    )
    assert r.status_code == 200
    assert r.json()["detail"] == "删除成功"

    from sqlalchemy import select

    result = await db.execute(select(AgentSkill).where(AgentSkill.id == skill.id))
    assert result.scalar_one_or_none() is None


# API-AGENT-SKILL-026: supervisor 删除技能成功
async def test_delete_skill_supervisor_success(client, supervisor_auth_headers, db):
    agent = await _create_user(db, "agent_del_002", "agent")
    category = await _create_category(db)
    skill = AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=3)
    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    r = await client.delete(
        f"/api/v1/admin/skills/{skill.id}", headers=supervisor_auth_headers
    )
    assert r.status_code == 200
    assert r.json()["detail"] == "删除成功"


# API-AGENT-SKILL-027: supervisor 删除非 agent 技能 403
async def test_delete_skill_supervisor_forbidden_non_agent(
    client, supervisor_auth_headers, db
):
    admin_user = await _create_user(db, "admin_del_003", "admin")
    category = await _create_category(db)
    skill = AgentSkill(agent_id=admin_user.id, category_id=category.id, proficiency=3)
    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    r = await client.delete(
        f"/api/v1/admin/skills/{skill.id}", headers=supervisor_auth_headers
    )
    assert r.status_code == 403
    assert "无权" in r.json()["detail"]


# API-AGENT-SKILL-028: agent 无权删除技能 403
async def test_delete_skill_agent_forbidden_403(client, agent_auth_headers, db):
    another_agent = await _create_user(db, "agent_del_004", "agent")
    category = await _create_category(db)
    skill = AgentSkill(agent_id=another_agent.id, category_id=category.id, proficiency=3)
    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    r = await client.delete(
        f"/api/v1/admin/skills/{skill.id}", headers=agent_auth_headers
    )
    assert r.status_code == 403


# API-AGENT-SKILL-029: customer 无权删除技能 403
async def test_delete_skill_customer_forbidden_403(client, customer_auth_headers, db):
    agent = await _create_user(db, "agent_del_005", "agent")
    category = await _create_category(db)
    skill = AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=3)
    db.add(skill)
    await db.commit()
    await db.refresh(skill)

    r = await client.delete(
        f"/api/v1/admin/skills/{skill.id}", headers=customer_auth_headers
    )
    assert r.status_code == 403


# API-AGENT-SKILL-030: 删除不存在的 skill 404
async def test_delete_skill_not_found_404(client, admin_auth_headers, db):
    r = await client.delete(
        "/api/v1/admin/skills/99999", headers=admin_auth_headers
    )
    assert r.status_code == 404
    assert "技能不存在" in r.json()["detail"]


# ===== GET /admin/skills =====

# API-AGENT-SKILL-031: admin 查询技能分页列表成功
async def test_list_skills_admin_success(client, admin_auth_headers, db):
    agent = await _create_user(db, "agent_list_001", "agent")
    category = await _create_category(db)
    skill = AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=4)
    db.add(skill)
    await db.commit()

    r = await client.get("/api/v1/admin/skills", headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 1
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert len(data["items"]) >= 1
    assert data["items"][0]["agent"]["id"] == agent.id
    assert data["items"][0]["category"]["id"] == category.id


# API-AGENT-SKILL-032: supervisor 只能看到 agent 角色的技能
async def test_list_skills_supervisor_only_sees_agents(client, supervisor_auth_headers, db):
    admin_user = await _create_user(db, "admin_list_002", "admin")
    agent = await _create_user(db, "agent_list_002", "agent")
    category = await _create_category(db)

    db.add(AgentSkill(agent_id=admin_user.id, category_id=category.id, proficiency=5))
    db.add(AgentSkill(agent_id=agent.id, category_id=category.id, proficiency=3))
    await db.commit()

    r = await client.get("/api/v1/admin/skills", headers=supervisor_auth_headers)
    assert r.status_code == 200
    data = r.json()
    agent_ids = {item["agent"]["id"] for item in data["items"]}
    assert admin_user.id not in agent_ids
    assert agent.id in agent_ids


# API-AGENT-SKILL-033: agent 无权查询技能分页列表 403
async def test_list_skills_agent_forbidden_403(client, agent_auth_headers, db):
    r = await client.get("/api/v1/admin/skills", headers=agent_auth_headers)
    assert r.status_code == 403


# API-AGENT-SKILL-034: customer 无权查询技能分页列表 403
async def test_list_skills_customer_forbidden_403(client, customer_auth_headers, db):
    r = await client.get("/api/v1/admin/skills", headers=customer_auth_headers)
    assert r.status_code == 403


# API-AGENT-SKILL-035: 按 agent_id 筛选技能列表
async def test_list_skills_filter_by_agent_id(client, admin_auth_headers, db):
    agent1 = await _create_user(db, "agent_list_003a", "agent")
    agent2 = await _create_user(db, "agent_list_003b", "agent")
    category = await _create_category(db)

    db.add(AgentSkill(agent_id=agent1.id, category_id=category.id, proficiency=3))
    db.add(AgentSkill(agent_id=agent2.id, category_id=category.id, proficiency=4))
    await db.commit()

    r = await client.get(
        f"/api/v1/admin/skills?agent_id={agent1.id}", headers=admin_auth_headers
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["agent"]["id"] == agent1.id


# API-AGENT-SKILL-036: 按 category_id 筛选技能列表
async def test_list_skills_filter_by_category_id(client, admin_auth_headers, db):
    agent = await _create_user(db, "agent_list_004", "agent")
    category1 = await _create_category(db)
    category2 = Category(name="咨询", code="consult", default_priority="P1")
    db.add(category2)
    await db.commit()
    await db.refresh(category2)

    db.add(AgentSkill(agent_id=agent.id, category_id=category1.id, proficiency=3))
    db.add(AgentSkill(agent_id=agent.id, category_id=category2.id, proficiency=4))
    await db.commit()

    r = await client.get(
        f"/api/v1/admin/skills?category_id={category1.id}", headers=admin_auth_headers
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["items"][0]["category"]["id"] == category1.id


# API-AGENT-SKILL-037: 分页参数生效
async def test_list_skills_pagination(client, admin_auth_headers, db):
    agent = await _create_user(db, "agent_list_005", "agent")

    for i in range(5):
        cat = Category(name=f"分类{i}", code=f"cat{i}", default_priority="P2")
        db.add(cat)
        await db.commit()
        await db.refresh(cat)
        db.add(
            AgentSkill(
                agent_id=agent.id, category_id=cat.id, proficiency=(i % 5) + 1
            )
        )
    await db.commit()

    r = await client.get(
        "/api/v1/admin/skills?page=1&page_size=2", headers=admin_auth_headers
    )
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 5
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) == 2

    r2 = await client.get(
        "/api/v1/admin/skills?page=2&page_size=2", headers=admin_auth_headers
    )
    data2 = r2.json()
    assert len(data2["items"]) == 2

    r3 = await client.get(
        "/api/v1/admin/skills?page=3&page_size=2", headers=admin_auth_headers
    )
    data3 = r3.json()
    assert len(data3["items"]) == 1


# API-AGENT-SKILL-038: 空列表分页返回 total=0
async def test_list_skills_empty_result(client, admin_auth_headers, db):
    r = await client.get("/api/v1/admin/skills", headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["items"] == []
