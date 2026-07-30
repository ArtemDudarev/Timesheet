from tests.conftest import SICK_TYPE_ID, VACATION_TYPE_ID

# 2026-09-07 (пн) — 2026-09-13 (вс): 5 рабочих дней


async def _create(client, token, submit=False, date_from="2026-09-07", date_to="2026-09-13",
                  type_id=VACATION_TYPE_ID):
    response = await client.post(
        "/absences/",
        json={
            "type_id": str(type_id),
            "date_from": date_from,
            "date_to": date_to,
            "comment": "Плановый отпуск",
            "submit": submit,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    return response


async def test_create_draft_counts_working_days(client, employee_token, test_employee, absence_types):
    response = await _create(client, employee_token)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "Черновик"
    assert body["days_count"] == 5  # выходные исключены
    assert body["absence_type"]["code"] == "VACATION"


async def test_create_with_submit(client, employee_token, test_employee, absence_types):
    response = await _create(client, employee_token, submit=True)
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "На согласовании"
    assert body["submitted_at"] is not None


async def test_create_weekend_only_range(client, employee_token, test_employee, absence_types):
    response = await _create(client, employee_token, date_from="2026-09-12", date_to="2026-09-13")
    assert response.status_code == 400  # суббота-воскресенье, 0 рабочих дней


async def test_create_invalid_dates(client, employee_token, test_employee, absence_types):
    response = await _create(client, employee_token, date_from="2026-09-13", date_to="2026-09-07")
    assert response.status_code == 422


async def test_update_draft(client, employee_token, test_employee, absence_types):
    absence_id = (await _create(client, employee_token)).json()["id"]
    response = await client.patch(
        f"/absences/{absence_id}",
        json={"date_to": "2026-09-08"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    assert response.json()["days_count"] == 2  # пн-вт


async def test_update_pending_conflict(client, employee_token, test_employee, absence_types):
    absence_id = (await _create(client, employee_token, submit=True)).json()["id"]
    response = await client.patch(
        f"/absences/{absence_id}",
        json={"date_to": "2026-09-08"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 409


async def test_update_foreign_forbidden(client, employee_token, outsider_token, test_employee,
                                        test_outsider, absence_types):
    absence_id = (await _create(client, employee_token)).json()["id"]
    response = await client.patch(
        f"/absences/{absence_id}",
        json={"comment": "чужое"},
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert response.status_code == 403


async def test_withdraw_draft_deletes(client, employee_token, test_employee, absence_types):
    absence_id = (await _create(client, employee_token)).json()["id"]
    response = await client.delete(
        f"/absences/{absence_id}", headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 204
    response = await client.get(
        f"/absences/{absence_id}", headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 404


async def test_withdraw_pending_cancels(client, employee_token, test_employee, absence_types):
    absence_id = (await _create(client, employee_token, submit=True)).json()["id"]
    response = await client.delete(
        f"/absences/{absence_id}", headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 204
    response = await client.get(
        f"/absences/{absence_id}", headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.json()["status"] == "Отменена"


async def test_submit_then_approve_by_teamlead(client, employee_token, teamlead_token,
                                               test_employee, absence_types):
    absence_id = (await _create(client, employee_token)).json()["id"]
    response = await client.post(
        f"/absences/{absence_id}/submit", headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 200

    response = await client.post(
        f"/absences/{absence_id}/approve",
        json={},
        headers={"Authorization": f"Bearer {teamlead_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "Согласована"
    assert body["approver_id"] is not None


async def test_approve_foreign_team_forbidden(client, outsider_token, teamlead_token,
                                              test_outsider, absence_types):
    absence_id = (await _create(client, outsider_token, submit=True)).json()["id"]
    response = await client.post(
        f"/absences/{absence_id}/approve",
        json={},
        headers={"Authorization": f"Bearer {teamlead_token}"},
    )
    assert response.status_code == 403


async def test_approve_by_manager_any(client, outsider_token, manager_token,
                                      test_outsider, absence_types):
    absence_id = (await _create(client, outsider_token, submit=True)).json()["id"]
    response = await client.post(
        f"/absences/{absence_id}/approve",
        json={},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200


async def test_approve_by_employee_forbidden(client, employee_token, test_employee, absence_types):
    absence_id = (await _create(client, employee_token, submit=True)).json()["id"]
    response = await client.post(
        f"/absences/{absence_id}/approve",
        json={},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 403


async def test_reject_requires_comment(client, employee_token, manager_token,
                                       test_employee, absence_types):
    absence_id = (await _create(client, employee_token, submit=True)).json()["id"]
    response = await client.post(
        f"/absences/{absence_id}/reject",
        json={},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 422


async def test_reject_then_resubmit(client, employee_token, manager_token,
                                    test_employee, absence_types):
    absence_id = (await _create(client, employee_token, submit=True)).json()["id"]
    response = await client.post(
        f"/absences/{absence_id}/reject",
        json={"comment": "Перенесите на октябрь"},
        headers={"Authorization": f"Bearer {manager_token}"},
    )
    assert response.status_code == 200
    assert response.json()["rejection_comment"] == "Перенесите на октябрь"

    # Отклонённую можно исправить и снова отправить
    response = await client.patch(
        f"/absences/{absence_id}",
        json={"date_from": "2026-10-05", "date_to": "2026-10-09"},
        headers={"Authorization": f"Bearer {employee_token}"},
    )
    assert response.status_code == 200
    response = await client.post(
        f"/absences/{absence_id}/submit", headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 200
    assert response.json()["rejection_comment"] is None


async def test_list_self_scoped(client, employee_token, outsider_token, test_employee,
                                test_outsider, absence_types):
    await _create(client, employee_token)
    await _create(client, outsider_token)
    response = await client.get(
        "/absences/", headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert len(response.json()) == 1


async def test_list_team_scoped(client, employee_token, outsider_token, teamlead_token,
                                test_employee, test_outsider, absence_types):
    await _create(client, employee_token)   # в команде тимлида
    await _create(client, outsider_token)   # не в команде
    response = await client.get(
        "/absences/", headers={"Authorization": f"Bearer {teamlead_token}"}
    )
    assert len(response.json()) == 1


async def test_absence_types_list(client, employee_token, absence_types):
    response = await client.get(
        "/absence-types/", headers={"Authorization": f"Bearer {employee_token}"}
    )
    assert response.status_code == 200
    assert {t["code"] for t in response.json()} == {"VACATION", "SICK"}
