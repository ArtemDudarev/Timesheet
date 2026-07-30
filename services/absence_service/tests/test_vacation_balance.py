from tests.conftest import EMPLOYEE_ID, SICK_TYPE_ID, VACATION_TYPE_ID


async def _create_and_approve(client, employee_token, manager_token, date_from, date_to,
                              type_id=VACATION_TYPE_ID):
    absence_id = (await client.post(
        "/absences/",
        json={
            "type_id": str(type_id),
            "date_from": date_from,
            "date_to": date_to,
            "submit": True,
        },
        headers={"Authorization": f"Bearer {employee_token}"},
    )).json()["id"]
    await client.post(
        f"/absences/{absence_id}/approve",
        json={},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    return absence_id


async def test_vacation_balance(client, employee_token, manager_token,
                                test_employee, absence_types):
    # Согласованный отпуск: 7-11 сентября (5 рабочих дней)
    await _create_and_approve(client, employee_token, manager_token, "2026-09-07", "2026-09-11")
    # PENDING отпуск: 5-9 октября (5 рабочих дней)
    await client.post(
        "/absences/",
        json={
            "type_id": str(VACATION_TYPE_ID),
            "date_from": "2026-10-05",
            "date_to": "2026-10-09",
            "submit": True,
        },
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    # Больничный не влияет на баланс отпуска
    await _create_and_approve(
        client, employee_token, manager_token, "2026-11-02", "2026-11-03", type_id=SICK_TYPE_ID
    )

    response = await client.get(
        f"/employees/{EMPLOYEE_ID}/vacation-balance?year=2026",
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["entitled_days"] == 28
    assert body["used_days"] == 5
    assert body["pending_days"] == 5
    assert body["remaining_days"] == 18


async def test_vacation_balance_foreign_forbidden(client, outsider_token, test_employee,
                                                  test_outsider, absence_types):
    response = await client.get(
        f"/employees/{EMPLOYEE_ID}/vacation-balance?year=2026",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert response.status_code == 403
