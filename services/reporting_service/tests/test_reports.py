import io

from openpyxl import load_workbook

# Июнь 2026: 22 рабочих дня × 8 = 176 ч нормы
JUNE_NORM = 176.0


async def test_utilization(client, reader_token, test_entries):
    response = await client.get(
        "/reports/utilization?period=2026-06",
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert response.status_code == 200
    rows = {r["full_name"]: r for r in response.json()}
    assert rows["Иван Петров"]["logged_hours"] == 16.0
    assert rows["Иван Петров"]["norm_hours"] == JUNE_NORM
    assert rows["Иван Петров"]["utilization_pct"] == round(16 / JUNE_NORM * 100, 1)
    # Больничный не считается загрузкой
    assert rows["Анна Смирнова"]["logged_hours"] == 8.0


async def test_utilization_bad_period(client, reader_token):
    response = await client.get(
        "/reports/utilization?period=июнь",
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert response.status_code == 422


async def test_utilization_requires_permission(client, employee_token):
    response = await client.get(
        "/reports/utilization?period=2026-06",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


async def test_projects(client, reader_token, test_entries):
    response = await client.get(
        "/reports/projects?period=2026-06",
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["name"] == "Омниканальная платформа"
    assert row["spent_hours"] == 16.0
    assert row["budget_hours"] == 100.0
    assert row["progress_pct"] == 16.0


async def test_plan_fact(client, reader_token, test_entries, test_plan):
    response = await client.get(
        "/reports/plan-fact?period=2026-06",
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["department_name"] == "Разработка"
    assert rows[0]["plan_hours"] == 160.0
    assert rows[0]["fact_hours"] == 24.0  # 16 + 8, больничный не в счёт


async def test_summary(client, reader_token, test_entries, test_plan):
    response = await client.get(
        "/reports/summary?period=2026-06",
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total_logged_hours"] == 24.0
    assert body["budget_used_pct"] == 16.0
    assert body["at_risk_projects_count"] == 0  # бюджет не превышен, дедлайн не прошёл


async def test_export_xlsx(client, reader_token, test_entries):
    response = await client.get(
        "/reports/export?type=utilization&period=2026-06",
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert response.status_code == 200
    assert "spreadsheetml" in response.headers["content-type"]
    assert "report_utilization_2026-06.xlsx" in response.headers["content-disposition"]

    wb = load_workbook(io.BytesIO(response.content))
    ws = wb.active
    values = [row[0] for row in ws.iter_rows(min_col=1, max_col=1, values_only=True)]
    assert "Иван Петров" in values


async def test_export_unknown_type(client, reader_token):
    response = await client.get(
        "/reports/export?type=everything&period=2026-06",
        headers={"Authorization": f"Bearer {reader_token}"},
    )
    assert response.status_code == 422
