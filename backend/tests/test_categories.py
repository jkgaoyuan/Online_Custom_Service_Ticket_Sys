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
    r = await client.get("/api/v1/categories", headers=admin_auth_headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


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


# ===== P0 异常 =====

# API-CAT-006: 删除不存在分类 404
async def test_delete_category_not_found_404(client, admin_auth_headers, db):
    r = await client.delete("/api/v1/admin/categories/99999", headers=admin_auth_headers)
    assert r.status_code == 404


# ===== P0 权限 =====

# API-CAT-002: 未认证创建分类 401
async def test_create_category_unauthorized_401(client, db):
    body = {"name": "故障报告", "code": "bug"}
    r = await client.post("/api/v1/admin/categories", json=body)
    assert r.status_code == 401


# API-CAT-003: 客户创建分类 403
async def test_create_category_forbidden_403(client, customer_auth_headers, db):
    body = {"name": "故障报告", "code": "bug"}
    r = await client.post("/api/v1/admin/categories", headers=customer_auth_headers, json=body)
    assert r.status_code == 403
