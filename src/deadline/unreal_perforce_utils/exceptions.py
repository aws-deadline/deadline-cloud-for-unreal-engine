#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.


class UnrealSourceControlNotAvailableError(Exception):
    """Raised whenn Unreal Source Control Provider is not available"""
    pass


class PerforceWorkspaceNotFoundError(Exception):
    """Raised when a workspace with the given parameters was not found"""


class PerforceConnectionError(Exception):
    """Raised when failed to connect to the Perforce with given credentials"""

    pass