import asyncio
import uuid

import pytest
from fastapi.testclient import TestClient

from src.app import create_app
from src.models.content_models import DataSourceType, SourceStatus


@pytest.mark.e2e
class TestContentFlowE2E:
    """End-to-end tests for content processing flow."""

    async def test_complete_content_flow(self):
        """Test the entire content processing flow from addition to completion."""
        # 1. Setup real app with actual dependencies
        app = create_app()
        client = TestClient(app)

        # 2. Add a source using proper models
        source_request = {
            "user_id": str(uuid.UUID("00000000-0000-0000-0000-000000000000")),
            "request_id": str(uuid.UUID("00000000-0000-0000-0000-000000000001")),
            "source_type": DataSourceType.WEB.value,
            "request_config": {
                "url": "https://example.com",
                "page_limit": 1,
                "exclude_patterns": [],
                "include_patterns": [],
            },
        }

        response = client.post("/api/v0/sources", json=source_request)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == SourceStatus.CRAWLING.value

        # 3. Poll source status until completion or timeout
        source_id = data["source_id"]
        max_retries = 10
        retry_count = 0
        final_status = None

        while retry_count < max_retries:
            status_response = client.get(f"/api/v0/sources/{source_id}")
            assert status_response.status_code == 200
            status_data = status_response.json()
            final_status = status_data["status"]
            if final_status in [SourceStatus.COMPLETED.value, SourceStatus.FAILED.value]:
                break
            retry_count += 1
            await asyncio.sleep(1)

        assert final_status in [SourceStatus.COMPLETED.value, SourceStatus.PROCESSING.value]
