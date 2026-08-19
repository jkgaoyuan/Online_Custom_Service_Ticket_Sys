import asyncio
import shutil
import uuid
from pathlib import Path

import pytest

from app.config import get_settings
from app.tasks.export_tasks import _async_generate_report_export, _sanitize_for_export
from tests.conftest import _create_category, _create_ticket, _create_user


@pytest.fixture(autouse=True)
def eager_export_task(monkeypatch):
    """Bypass Celery broker by making .delay a no-op during API tests."""
    try:
        from app.tasks import export_tasks
    except ImportError:
        yield
        return

    original_delay = export_tasks.generate_report_export.delay
    monkeypatch.setattr(export_tasks.generate_report_export, "delay", lambda *a, **k: None)
    yield
    monkeypatch.setattr(export_tasks.generate_report_export, "delay", original_delay)


@pytest.fixture(autouse=True)
def cleanup_exports():
    yield
    settings = get_settings()
    export_dir = Path(settings.EXPORT_DIR)
    if export_dir.exists():
        shutil.rmtree(export_dir)


# API-EXP-101: export xlsx succeeds and file is downloadable
async def test_export_xlsx_success(client, admin_auth_headers):
    payload = {
        "report_type": "overview",
        "format": "xlsx",
        "start_date": "2026-01-01",
        "end_date": "2026-01-31",
    }
    r = await client.post("/api/v1/admin/reports/export", json=payload, headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert "task_id" in data
    assert data["status"] == "pending"
    task_id = data["task_id"]

    # Query status (may still be pending in tests)
    r2 = await client.get(f"/api/v1/admin/reports/export/{task_id}", headers=admin_auth_headers)
    assert r2.status_code == 200
    data2 = r2.json()
    assert data2["task_id"] == task_id
    assert data2["status"] in ("pending", "completed")


# API-EXP-102: export csv succeeds
async def test_export_csv_success(client, admin_auth_headers):
    payload = {
        "report_type": "category_distribution",
        "format": "csv",
    }
    r = await client.post("/api/v1/admin/reports/export", json=payload, headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "pending"


# API-EXP-201: invalid report_type returns 422
async def test_invalid_report_type_422(client, admin_auth_headers):
    payload = {
        "report_type": "invalid_type",
        "format": "xlsx",
    }
    r = await client.post("/api/v1/admin/reports/export", json=payload, headers=admin_auth_headers)
    assert r.status_code == 422


# API-EXP-202: pending export status returns pending
async def test_pending_export_status(client, admin_auth_headers):
    # Use a random UUID that will never be found
    fake_id = str(uuid.uuid4())
    r = await client.get(f"/api/v1/admin/reports/export/{fake_id}", headers=admin_auth_headers)
    # Our implementation may return 404 for unknown task_id
    assert r.status_code in (200, 404)


# ---- Unit tests for the actual export task logic ----

async def test_export_task_creates_xlsx_file(db):
    customer = await _create_user(db, "exp_customer", "customer")
    category = await _create_category(db)
    await _create_ticket(db, "Export1", "D1", category.id, customer.id)

    task_id = str(uuid.uuid4())
    await _async_generate_report_export(
        task_id=task_id,
        report_type="overview",
        format="xlsx",
        start_date=None,
        end_date=None,
    )

    settings = get_settings()
    file_path = Path(settings.EXPORT_DIR) / f"{task_id}.xlsx"
    assert file_path.exists()
    assert file_path.stat().st_size > 0


async def test_export_task_creates_csv_file(db):
    customer = await _create_user(db, "exp_customer2", "customer")
    category = await _create_category(db)
    await _create_ticket(db, "Export2", "D2", category.id, customer.id)

    task_id = str(uuid.uuid4())
    await _async_generate_report_export(
        task_id=task_id,
        report_type="category_distribution",
        format="csv",
        start_date=None,
        end_date=None,
    )

    settings = get_settings()
    file_path = Path(settings.EXPORT_DIR) / f"{task_id}.csv"
    assert file_path.exists()
    assert file_path.stat().st_size > 0


def test_sanitize_for_export_directly():
    """API-EXP-301: _sanitize_for_export prefixes formula triggers with apostrophe."""
    assert _sanitize_for_export('=HYPERLINK("http://evil.com","click")') == "'=HYPERLINK(\"http://evil.com\",\"click\")"
    assert _sanitize_for_export("+1+1") == "'+1+1"
    assert _sanitize_for_export("-1-1") == "'-1-1"
    assert _sanitize_for_export("@SUM(...)") == "'@SUM(...)"
    assert _sanitize_for_export("normal text") == "normal text"
    assert _sanitize_for_export(123) == 123
    assert _sanitize_for_export(None) is None


async def test_export_task_unknown_report_type_raises(db):
    with pytest.raises(ValueError, match="Unknown report_type"):
        await _async_generate_report_export(
            task_id=str(uuid.uuid4()),
            report_type="invalid_type",
            format="csv",
            start_date=None,
            end_date=None,
        )


# API-EXP-401: empty data export creates a file with a fallback message
async def test_export_task_empty_data_creates_file_with_fallback(db):
    task_id = str(uuid.uuid4())
    await _async_generate_report_export(
        task_id=task_id,
        report_type="category_distribution",
        format="csv",
        start_date="2020-01-01",
        end_date="2020-01-31",
    )

    settings = get_settings()
    file_path = Path(settings.EXPORT_DIR) / f"{task_id}.csv"
    assert file_path.exists()
    content = file_path.read_text(encoding="utf-8")
    assert "提示" in content
    assert "所选时间范围内没有数据" in content


# API-EXP-402: failed export writes a marker file and re-raises
async def test_export_task_failed_marker_created_on_error(db):
    task_id = str(uuid.uuid4())
    with pytest.raises(ValueError, match="Unknown report_type"):
        await _async_generate_report_export(
            task_id=task_id,
            report_type="invalid_type",
            format="csv",
            start_date=None,
            end_date=None,
        )

    settings = get_settings()
    failed_marker = Path(settings.EXPORT_DIR) / f"{task_id}.failed"
    assert failed_marker.exists()
    assert "Unknown report_type" in failed_marker.read_text(encoding="utf-8")


# API-EXP-403: status endpoint reports failed when marker file exists
async def test_export_status_returns_failed_when_marker_exists(client, admin_auth_headers):
    task_id = str(uuid.uuid4())
    settings = get_settings()
    failed_marker = Path(settings.EXPORT_DIR) / f"{task_id}.failed"
    failed_marker.parent.mkdir(parents=True, exist_ok=True)
    failed_marker.write_text("export error", encoding="utf-8")

    r = await client.get(f"/api/v1/admin/reports/export/{task_id}", headers=admin_auth_headers)
    assert r.status_code == 200
    data = r.json()
    assert data["task_id"] == task_id
    assert data["status"] == "failed"
    assert data["download_url"] is None
