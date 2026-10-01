# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import json
import sys
import urllib.error
from unittest.mock import patch, MagicMock

import pytest

# Mock the 'unreal' module before importing update_check, since it's only
# available inside the Unreal Engine Python environment.
_mock_unreal = MagicMock()
sys.modules["unreal"] = _mock_unreal


# Now safe to import — unreal is already in sys.modules.
from update_check import (  # noqa: E402
    _fetch_latest_version,
    _is_update_available,
    safe_check_and_show_update_dialog,
    RELEASES_PAGE_URL,
    SETUP_GUIDE_URL,
)


class TestFetchLatestVersion:
    """Tests for _fetch_latest_version()."""

    @patch("update_check.ssl.create_default_context")
    @patch("update_check.urllib.request.urlopen")
    @patch("update_check._get_botocore_ca_bundle", return_value="/fake/cacert.pem")
    def test_returns_version_from_github(self, mock_ca, mock_urlopen, mock_ssl):
        response_data = json.dumps({"tag_name": "v0.6.5"}).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        assert _fetch_latest_version() == "0.6.5"

    @patch("update_check.ssl.create_default_context")
    @patch("update_check.urllib.request.urlopen")
    @patch("update_check._get_botocore_ca_bundle", return_value="/fake/cacert.pem")
    def test_returns_none_on_network_error(self, mock_ca, mock_urlopen, mock_ssl):
        mock_urlopen.side_effect = urllib.error.URLError("connection refused")

        assert _fetch_latest_version() is None

    @patch("update_check.ssl.create_default_context")
    @patch("update_check.urllib.request.urlopen")
    @patch("update_check._get_botocore_ca_bundle", return_value="/fake/cacert.pem")
    def test_returns_none_on_timeout(self, mock_ca, mock_urlopen, mock_ssl):
        import socket

        mock_urlopen.side_effect = socket.timeout("timed out")

        assert _fetch_latest_version() is None

    @patch("update_check.ssl.create_default_context")
    @patch("update_check.urllib.request.urlopen")
    @patch("update_check._get_botocore_ca_bundle", return_value="/fake/cacert.pem")
    def test_returns_none_on_invalid_json(self, mock_ca, mock_urlopen, mock_ssl):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not json"
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        assert _fetch_latest_version() is None

    @patch("update_check.ssl.create_default_context")
    @patch("update_check.urllib.request.urlopen")
    @patch("update_check._get_botocore_ca_bundle", return_value="/fake/cacert.pem")
    def test_returns_none_on_empty_tag(self, mock_ca, mock_urlopen, mock_ssl):
        response_data = json.dumps({"tag_name": ""}).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.read.return_value = response_data
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        assert _fetch_latest_version() is None


class TestIsUpdateAvailable:
    """Tests for _is_update_available()."""

    @pytest.mark.parametrize(
        "current, latest, expected",
        [
            # Newer version available
            ("0.5.0", "0.6.5", True),
            ("0.6.5", "0.10.0", True),
            # Same version
            ("0.6.5", "0.6.5", False),
            # Current is newer (no update)
            ("1.0.0", "0.6.5", False),
            ("0.10.0", "0.6.5", False),
            # Invalid versions
            ("not-a-version", "0.6.5", False),
            ("0.6.5", "not-a-version", False),
            # Dev/post builds
            ("0.6.5.post144", "0.7.0", True),
            ("0.7.0", "0.6.5.post144", False),
            ("0.6.5.post144", "0.6.5", False),
        ],
        ids=[
            "newer_available",
            "newer_available_double_digit_minor",
            "same_version",
            "current_is_newer",
            "current_is_newer_double_digit_minor",
            "invalid_current",
            "invalid_latest",
            "dev_build_older_than_release",
            "release_newer_than_dev_build",
            "post_release_same_base",
        ],
    )
    def test_is_update_available(self, current, latest, expected):
        assert _is_update_available(current, latest) is expected


class TestCheckAndShowUpdateDialog:
    """Tests for safe_check_and_show_update_dialog()."""

    @pytest.fixture(autouse=True)
    def reset_unreal_mock(self):
        _mock_unreal.reset_mock()

    @patch("update_check._is_update_notification_enabled", return_value=False)
    def test_returns_false_when_notifications_disabled(self, mock_enabled):
        assert safe_check_and_show_update_dialog() is False

    @patch("update_check._fetch_latest_version", return_value=None)
    @patch("update_check._get_current_version", return_value="0.5.0")
    @patch("update_check._is_update_notification_enabled", return_value=True)
    def test_returns_false_when_fetch_fails(self, mock_enabled, mock_current, mock_fetch):
        assert safe_check_and_show_update_dialog() is False

    @patch("update_check._is_update_available", return_value=False)
    @patch("update_check._fetch_latest_version", return_value="0.5.0")
    @patch("update_check._get_current_version", return_value="0.5.0")
    @patch("update_check._is_update_notification_enabled", return_value=True)
    def test_returns_false_when_already_up_to_date(
        self, mock_enabled, mock_current, mock_fetch, mock_available
    ):
        assert safe_check_and_show_update_dialog() is False

    @patch("update_check.webbrowser.open")
    @patch("update_check._is_update_available", return_value=True)
    @patch("update_check._fetch_latest_version", return_value="0.6.5")
    @patch("update_check._get_current_version", return_value="0.5.0")
    @patch("update_check._is_update_notification_enabled", return_value=True)
    def test_returns_true_when_user_clicks_yes(
        self, mock_enabled, mock_current, mock_fetch, mock_available, mock_webbrowser
    ):
        _mock_unreal.AppReturnType.YES = "YES"
        _mock_unreal.EditorDialog.show_message.return_value = "YES"

        result = safe_check_and_show_update_dialog()

        assert result is True
        # Should open releases page first, then setup guide
        assert mock_webbrowser.call_count == 2
        mock_webbrowser.assert_any_call(RELEASES_PAGE_URL)
        mock_webbrowser.assert_any_call(SETUP_GUIDE_URL)
        # Should show two dialogs: the update dialog and the setup guide
        assert _mock_unreal.EditorDialog.show_message.call_count == 2

        # First dialog should mention release notes
        first_call_args = _mock_unreal.EditorDialog.show_message.call_args_list[0]
        assert RELEASES_PAGE_URL in first_call_args[0][1]

        # Second dialog should mention the setup guide
        second_call_args = _mock_unreal.EditorDialog.show_message.call_args_list[1]
        assert SETUP_GUIDE_URL in second_call_args[0][1]

    @patch("update_check._is_update_available", return_value=True)
    @patch("update_check._fetch_latest_version", return_value="0.6.5")
    @patch("update_check._get_current_version", return_value="0.5.0")
    @patch("update_check._is_update_notification_enabled", return_value=True)
    def test_returns_false_when_user_clicks_no(
        self, mock_enabled, mock_current, mock_fetch, mock_available
    ):
        _mock_unreal.AppReturnType.YES = "YES"
        _mock_unreal.EditorDialog.show_message.return_value = "NO"

        result = safe_check_and_show_update_dialog()

        assert result is False

    @patch("update_check.webbrowser.open")
    @patch("update_check._is_update_available", return_value=True)
    @patch("update_check._fetch_latest_version", return_value="0.6.5")
    @patch("update_check._get_current_version", return_value="0.5.0")
    @patch("update_check._is_update_notification_enabled", return_value=True)
    def test_skips_setup_guide_when_user_dismisses_second_dialog(
        self, mock_enabled, mock_current, mock_fetch, mock_available, mock_webbrowser
    ):
        _mock_unreal.AppReturnType.YES = "YES"
        # First dialog: Yes, second dialog: No
        _mock_unreal.EditorDialog.show_message.side_effect = ["YES", "NO"]

        result = safe_check_and_show_update_dialog()

        assert result is True
        # Only the releases page should be opened, not the setup guide
        mock_webbrowser.assert_called_once_with(RELEASES_PAGE_URL)

    @patch("update_check.webbrowser.open", side_effect=Exception("browser error"))
    @patch("update_check._is_update_available", return_value=True)
    @patch("update_check._fetch_latest_version", return_value="0.6.5")
    @patch("update_check._get_current_version", return_value="0.5.0")
    @patch("update_check._is_update_notification_enabled", return_value=True)
    def test_returns_false_when_webbrowser_fails(
        self, mock_enabled, mock_current, mock_fetch, mock_available, mock_webbrowser
    ):
        _mock_unreal.AppReturnType.YES = "YES"
        _mock_unreal.EditorDialog.show_message.return_value = "YES"

        result = safe_check_and_show_update_dialog()

        assert result is False
