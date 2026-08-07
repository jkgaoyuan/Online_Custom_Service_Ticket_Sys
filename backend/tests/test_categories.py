# ===== P0 正向 =====

# API-CAT-001: 创建分类成功
async def test_create_category_success(client, admin_auth_headers, db):
    body = {"name": "故障报告", "code": "bug", "default_priority": "P1"}
    r = await client.post("/api/v1/admin/categories", headers=admin_auth_headers, json=body)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "故障报告"
    assert data["code"] == "bug"
    assert data["default_priority"] == "P1"


# API-CAT-004: 列表分类成功
async def test_list_categories_success(client, admin_auth_headers, db):
    create_r = await client.post(
        "/api/v1/admin/categories",
        headers=admin_auth_headers,
        json={"name": "故障报告", "code": "bug", "default_priority": "P1"},
    )
    assert create_r.status_code == 201
    created = create_r.json()

    r = await client.get("/api/v1/categories", headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any(
        c["id"] == created["id"]
        and c["name"] == created["name"]
        and c["code"] == created["code"]
        and c["default_priority"] == created["default_priority"]
        for c in data
    )


# API-CAT-005: 更新分类成功
async def test_update_category_success(client, admin_auth_headers, db):
    create_r = await client.post(
        "/api/v1/admin/categories",
        headers=admin_auth_headers,
        json={"name": "旧名称", "code": "old"},
    )
    cat_id = create_r.json()["id"]
    r = await client.put(
        f"/api/v1/admin/categories/{cat_id}",
        headers=admin_auth_headers,
        json={"name": "新名称"},
    )
    assert r.status_code == 200
    assert r.json()["name"] == "新名称"


# API-CAT-006: 删除不存在分类 404
async def test_delete_category_not_found_404(client, admin_auth_headers, db):
    r = await client.delete("/api/v1/admin/categories/99999", headers=admin_auth_headers)
    assert r.status_code == 404
    assert r.json()["detail"] == "分类不存在"


# API-CAT-007: 更新不存在分类 404
async def test_update_category_not_found_404(client, admin_auth_headers, db):
    r = await client.put(
        "/api/v1/admin/categories/99999",
        headers=admin_auth_headers,
        json={"name": "不存在"},
    )
    assert r.status_code == 404
    assert r.json()["detail"] == "分类不存在"


# API-CAT-008: 重复编码 409
async def test_create_category_duplicate_code_409(client, admin_auth_headers, db):
    body = {"name": "故障报告", "code": "dup_bug", "default_priority": "P1"}
    r1 = await client.post("/api/v1/admin/categories", headers=admin_auth_headers, json=body)
    assert r1.status_code == 201

    r2 = await client.post(
        "/api/v1/admin/categories",
        headers=admin_auth_headers,
        json={"name": "另一个", "code": "dup_bug", "default_priority": "P2"},
    )
    assert r2.status_code == 409
    assert r2.json()["detail"] == "分类编码已存在"


# API-CAT-009: 无效优先级 422
async def test_create_category_invalid_priority_422(client, admin_auth_headers, db):
    body = {"name": "无效优先级", "code": "invalid_pri", "default_priority": "P4"}
    r = await client.post("/api/v1/admin/categories", headers=admin_auth_headers, json=body)
    assert r.status_code == 422


# ===== P0 权限 =====

# API-CAT-002: 未认证创建分类 401
async def test_create_category_unauthorized_401(client, db):
    body = {"name": "故障报告", "code": "bug"}
    r = await client.post("/api/v1/admin/categories", json=body)
    assert r.status_code == 401
    assert r.json()["detail"] == "Not authenticated"


# API-CAT-003: 客户创建分类 403
async def test_create_category_forbidden_403(client, customer_auth_headers, db):
    body = {"name": "故障报告", "code": "bug"}
    r = await client.post("/api/v1/admin/categories", headers=customer_auth_headers, json=body)
    assert r.status_code == 403
    assert r.json()["detail"] == "需要角色: admin, supervisor"


# API-CAT-010: 主管创建分类 200
async def test_create_category_as_supervisor_200(client, supervisor_auth_headers, db):
    body = {"name": "咨询分类", "code": "supervisor_cat", "default_priority": "P2"}
    r = await client.post("/api/v1/admin/categories", headers=supervisor_auth_headers, json=body)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "咨询分类"
    assert data["code"] == "supervisor_cat"
    assert data["default_priority"] == "P2"
