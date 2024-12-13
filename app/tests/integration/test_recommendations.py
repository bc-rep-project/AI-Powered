import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_get_recommendations():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/recommendations")
        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

@pytest.mark.asyncio
async def test_rate_limiting():
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Make 6 requests (limit is 5)
        responses = []
        for _ in range(6):
            response = await client.get("/recommendations")
            responses.append(response)

        # First 5 should succeed
        assert all(r.status_code == 200 for r in responses[:5])
        # 6th should fail with 429
        assert responses[5].status_code == 429 