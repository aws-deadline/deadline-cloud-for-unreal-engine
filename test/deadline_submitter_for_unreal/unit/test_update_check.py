# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from __future__ import annotations

import json
import sys
import urllib.error
from unittest.mock import patch, MagicMock

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

    def test_newer_version_available(self):
        assert _is_update_available("0.5.0", "0.6.5") is True

    def test_same_version(self):
        assert _is_update_available("0.6.5", "0.6.5") is False

    def test_older_version(self):
        assert _is_update_available("1.0.0", "0.6.5") is False

    def test_invalid_current_version(self):
        assert _is_update_available("not-a-version", "0.6.5") is False

    def test_invalid_latest_version(self):
        assert _is_update_available("0.6.5", "not-a-version") is False

    def test_dev_build_is_older_than_release(self):
        assert _is_update_available("0.6.5.post144", "0.7.0") is True

    def test_release_is_newer_than_dev_build(self):
        assert _is_update_available("0.7.0", "0.6.5.post144") is False

    def test_post_release_does_not_trigger_update_for_same_base(self):
        assert _is_update_available("0.6.5.post144", "0.6.5") is False


class TestCheckAndShowUpdateDialog:
    """Tests for safe_check_and_show_update_dialog()."""

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
        mock_webbrowser.assert_called_once_with(RELEASES_PAGE_URL)
        # Should show two dialogs: the update dialog and the restart reminder
        assert _mock_unreal.EditorDialog.show_message.call_count == 2

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
