# ===== P0 正向 =====

# API-DISPATCH-001: 创建技能成功
async def test_create_agent_skill_success(client, admin_auth_headers, db):
    from tests.conftest import _create_category, _create_user

    agent = await _create_user(db, "agent_for_skill", "agent")
    category = await _create_category(db)
    body = {"agent_id": agent.id, "category_id": category.id, "proficiency": 5}
    r = await client.post(
        "/api/v1/admin/agent-skills", headers=admin_auth_headers, json=body
    )
    assert r.status_code == 201
    data = r.json()
    assert data["proficiency"] == 5
    assert data["agent_id"] == agent.id
    assert data["category_id"] == category.id
    assert "id" in data


# API-DISPATCH-002: 非 admin/supervisor 创建技能 403
async def test_create_agent_skill_forbidden_403(client, agent_auth_headers, db):
    from tests.conftest import _create_category, _create_user

    agent = await _create_user(db, "agent_for_skill2", "agent")
    category = await _create_category(db)
    body = {"agent_id": agent.id, "category_id": category.id, "proficiency": 5}
    r = await client.post(
        "/api/v1/admin/agent-skills", headers=agent_auth_headers, json=body
    )
    assert r.status_code == 403


# API-DISPATCH-003: proficiency 超边界 422
async def test_create_agent_skill_proficiency_invalid_422(
    client, admin_auth_headers, db
):
    from tests.conftest import _create_category, _create_user

    agent = await _create_user(db, "agent_for_skill3", "agent")
    category = await _create_category(db)
    body = {"agent_id": agent.id, "category_id": category.id, "proficiency": 6}
    r = await client.post(
        "/api/v1/admin/agent-skills", headers=admin_auth_headers, json=body
    )
    assert r.status_code == 422


# API-DISPATCH-004: 删除技能成功
async def test_delete_agent_skill_success(client, admin_auth_headers, db):
    from tests.conftest import _create_category, _create_user

    agent = await _create_user(db, "agent_for_skill4", "agent")
    category = await _create_category(db)
    create_r = await client.post(
        "/api/v1/admin/agent-skills",
        headers=admin_auth_headers,
        json={"agent_id": agent.id, "category_id": category.id, "proficiency": 4},
    )
    skill_id = create_r.json()["id"]
    r = await client.delete(
        f"/api/v1/admin/agent-skills/{skill_id}", headers=admin_auth_headers
    )
    assert r.status_code == 204


# API-DISPATCH-005: 查询 agent 技能列表
async def test_list_agent_skills_success(client, admin_auth_headers, db):
    from tests.conftest import _create_category, _create_user

    agent = await _create_user(db, "agent_for_skill5", "agent")
    category = await _create_category(db)
    await client.post(
        "/api/v1/admin/agent-skills",
        headers=admin_auth_headers,
        json={"agent_id": agent.id, "category_id": category.id, "proficiency": 4},
    )
    r = await client.get(
        f"/api/v1/admin/agent-skills?agent_id={agent.id}",
        headers=admin_auth_headers,
    )
    assert r.status_code == 200
    assert len(r.json()) == 1


# API-DISPATCH-006: 更新技能成功
async def test_update_agent_skill_success(client, admin_auth_headers, db):
    from tests.conftest import _create_category, _create_user

    agent = await _create_user(db, "agent_for_skill6", "agent")
    category = await _create_category(db)
    create_r = await client.post(
        "/api/v1/admin/agent-skills",
        headers=admin_auth_headers,
        json={"agent_id": agent.id, "category_id": category.id, "proficiency": 2},
    )
    skill_id = create_r.json()["id"]
    r = await client.put(
        f"/api/v1/admin/agent-skills/{skill_id}",
        headers=admin_auth_headers,
        json={"proficiency": 5},
    )
    assert r.status_code == 200
    assert r.json()["proficiency"] == 5


# API-DISPATCH-007: 更新不存在技能 404
async def test_update_agent_skill_not_found_404(client, admin_auth_headers, db):
    r = await client.put(
        "/api/v1/admin/agent-skills/99999",
        headers=admin_auth_headers,
        json={"proficiency": 5},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "技能记录不存在"


# API-DISPATCH-008: 删除不存在技能 404
async def test_delete_agent_skill_not_found_404(client, admin_auth_headers, db):
    r = await client.delete(
        "/api/v1/admin/agent-skills/99999", headers=admin_auth_headers
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "技能记录不存在"


# API-DISPATCH-009: 未认证创建技能 401
async def test_create_agent_skill_unauthorized_401(client, db):
    body = {"agent_id": 1, "category_id": 1, "proficiency": 5}
    r = await client.post("/api/v1/admin/agent-skills", json=body)
    assert r.status_code == 401


# API-DISPATCH-010: 客户创建技能 403
async def test_create_agent_skill_customer_forbidden_403(
    client, customer_auth_headers, db
):
    body = {"agent_id": 1, "category_id": 1, "proficiency": 5}
    r = await client.post(
        "/api/v1/admin/agent-skills", headers=customer_auth_headers, json=body
    )
    assert r.status_code == 403


# API-DISPATCH-011: 主管可以操作技能
async def test_create_agent_skill_as_supervisor_200(
    client, supervisor_auth_headers, db
):
    from tests.conftest import _create_category, _create_user

    agent = await _create_user(db, "agent_for_skill7", "agent")
    category = await _create_category(db)
    body = {"agent_id": agent.id, "category_id": category.id, "proficiency": 3}
    r = await client.post(
        "/api/v1/admin/agent-skills", headers=supervisor_auth_headers, json=body
    )
    assert r.status_code == 201
    data = r.json()
    assert data["proficiency"] == 3


# API-DISPATCH-012: 查询全部技能列表
async def test_list_all_agent_skills_success(client, admin_auth_headers, db):
    from tests.conftest import _create_category, _create_user

    agent = await _create_user(db, "agent_for_skill8", "agent")
    category = await _create_category(db)
    await client.post(
        "/api/v1/admin/agent-skills",
        headers=admin_auth_headers,
        json={"agent_id": agent.id, "category_id": category.id, "proficiency": 4},
    )
    r = await client.get("/api/v1/admin/agent-skills", headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1


# API-DISPATCH-013: proficiency 低于边界 422
async def test_create_agent_skill_proficiency_too_low_422(
    client, admin_auth_headers, db
):
    from tests.conftest import _create_category, _create_user

    agent = await _create_user(db, "agent_for_skill9", "agent")
    category = await _create_category(db)
    body = {"agent_id": agent.id, "category_id": category.id, "proficiency": 0}
    r = await client.post(
        "/api/v1/admin/agent-skills", headers=admin_auth_headers, json=body
    )
    assert r.status_code == 422
