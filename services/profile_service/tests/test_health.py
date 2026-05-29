async def test_health(client):
    """GET /health → 200, service: profile_service."""
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "profile_service"
