# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import sys
import os
import pytest
from unittest.mock import patch

# Add the settings module to path since it's not in the standard package structure
sys.path.insert(
    0, os.path.join(os.path.dirname(__file__), "../../../src/unreal_plugin/Content/Python")
)


class TestBackgroundInitS3Client:
    """Test the background_init_s3_client function"""

    @pytest.mark.skip(
        reason="Test pass in GitHub but fail in CodeBuild - making real API calls instead of using mocks"
    )
    def test_background_init_s3_client_consistency(self, aws_test_config):
        """Test that background_init_s3_client produces consistent results with direct precache_clients calls"""
        from settings import background_init_s3_client
        from deadline.client.api import precache_clients

        # Call background_init_s3_client and get the thread
        thread = background_init_s3_client()

        # Wait for the thread to complete
        thread.join(timeout=10.0)

        # Get the result from the thread
        first_result = thread.result_container.get("result")

        # Call precache_clients again without parameters
        second_result = precache_clients()

        # Verify that both calls return the same client objects
        assert first_result == second_result
        assert first_result is not None
        assert second_result is not None


class TestOnFarmQueueUpdate:
    """Test the on_farm_queue_update function"""

    @patch("settings.background_init_s3_client")
    def test_on_farm_queue_update_calls_background_init(self, mock_background_init):
        """Test that on_farm_queue_update calls background_init_s3_client"""
        from settings import on_farm_queue_update

        on_farm_queue_update()

        mock_background_init.assert_called_once()
