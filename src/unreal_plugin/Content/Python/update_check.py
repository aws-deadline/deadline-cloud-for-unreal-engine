# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

"""
Update checker for the Deadline Cloud for Unreal Engine plugin.

Checks the GitHub releases API for a newer version and shows an Unreal
Editor dialog when an update is available.  Respects the Deadline Cloud
``settings.submitter_update_notification`` config toggle.
"""

from __future__ import annotations

import json
import logging
import os
import socket
import ssl
import urllib.request
import urllib.error
import webbrowser

import botocore
import unreal

from packaging.version import Version, InvalidVersion

from deadline.client.config import config_file
from deadline.unreal_submitter._version import version as _current_version

logger = logging.getLogger(__name__)

GITHUB_LATEST_RELEASE_URL = (
    "https://api.github.com/repos/aws-deadline/deadline-cloud-for-unreal-engine/releases/latest"
)
RELEASES_PAGE_URL = "https://github.com/aws-deadline/deadline-cloud-for-unreal-engine/releases"
SETUP_GUIDE_URL = "https://aws-deadline.github.io/unreal-engine/setup-submitter/"
_REQUEST_TIMEOUT_SECONDS = 5


def _is_update_notification_enabled() -> bool:
    """Check whether the user has opted in to update notifications."""
    return config_file.str2bool(config_file.get_setting("settings.submitter_update_notification"))


def _get_current_version() -> str:
    """Return the currently installed plugin version string."""
    return _current_version


def _fetch_latest_version() -> str | None:
    """Fetch the latest release tag from GitHub.

    Returns:
        The version string (e.g. ``"0.6.5"``) or ``None`` on failure.
    """
    # Pin to GitHub REST API v3 JSON format so the response shape stays stable.
    req = urllib.request.Request(
        GITHUB_LATEST_RELEASE_URL,
        headers={"Accept": "application/vnd.github.v3+json"},
    )

    # Build a strict TLS context: enforce TLS 1.2+ and use the botocore CA
    # bundle so certificate verification works even in embedded Python
    # environments (e.g. Unreal) that may lack system root certificates.
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    ctx.load_verify_locations(_get_botocore_ca_bundle())

    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SECONDS, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            tag = data.get("tag_name", "")
            return tag.lstrip("v") if tag else None
    except urllib.error.URLError:
        return None
    except (socket.timeout, TimeoutError):
        return None
    except json.JSONDecodeError:
        return None


def _get_botocore_ca_bundle() -> str:
    """Return the path to botocore's bundled CA certificate bundle."""
    return os.path.join(os.path.dirname(botocore.__file__), "cacert.pem")


def _is_update_available(current: str, latest: str) -> bool:
    """Return True if *latest* is strictly newer than *current*."""
    try:
        return Version(latest) > Version(current)
    except InvalidVersion:
        return False


def safe_check_and_show_update_dialog() -> bool:
    """Check GitHub for a newer release and show an Unreal dialog if found.

    Returns:
        ``True`` if the user chose to open the download page (caller may
        want to skip opening the submitter), ``False`` otherwise.
    """
    try:
        return _check_and_show_update_dialog()
    except Exception:
        logger.debug("Update check failed -- skipping", exc_info=True)
        return False


def _check_and_show_update_dialog() -> bool:
    """Internal implementation of the update check and dialog flow."""
    if not _is_update_notification_enabled():
        return False

    current_version = _get_current_version()

    latest_version = _fetch_latest_version()

    if not latest_version:
        return False

    if not _is_update_available(current_version, latest_version):
        return False

    message = (
        f"Version {latest_version} of Deadline Cloud for Unreal Engine "
        f"submitter is now available.\n\n"
        f"Current: {current_version}  ->  New: {latest_version}\n\n"
        f"View release notes:\n{RELEASES_PAGE_URL}\n\n"
        "To disable these notifications, go to Edit > Project Settings > "
        'search for "Deadline" and uncheck "Show Submitter Update '
        'Notifications" under General Settings.\n\n'
        "Click 'Yes' to open the release page, or 'No' to dismiss."
    )

    response = unreal.EditorDialog.show_message(
        "New version available",
        message,
        unreal.AppMsgType.YES_NO,
    )

    if response == unreal.AppReturnType.YES:
        try:
            webbrowser.open(RELEASES_PAGE_URL)
        except Exception:
            return False

        guide_message = (
            "Please follow the setup guide to install the new release and "
            "then restart Unreal Engine to use the new version.\n\n"
            f"Setup guide:\n{SETUP_GUIDE_URL}\n\n"
            "Click 'Yes' to open the setup guide, or 'No' to dismiss."
        )

        guide_response = unreal.EditorDialog.show_message(
            "Installation Guide",
            guide_message,
            unreal.AppMsgType.YES_NO,
        )

        if guide_response == unreal.AppReturnType.YES:
            try:
                webbrowser.open(SETUP_GUIDE_URL)
            except Exception:
                logger.debug("Failed to open setup guide URL", exc_info=True)
        return True

    return False
