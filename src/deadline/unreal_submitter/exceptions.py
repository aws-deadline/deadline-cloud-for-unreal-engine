# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.


class DeadlineCloudSubmitterException(Exception):
    """Base exception for all deadline-cloud-for-unreal-engine custom exceptions"""

    pass


class UserException:
    """Marker mixin: Exceptions that do not trigger UI notifications and are raised by user choice."""

    pass


class ParametersAreNotConsistentError(DeadlineCloudSubmitterException):
    """Raised when OpenJD parameters/variables are not consistent"""

    pass


class RenderStepCountConstraintError(DeadlineCloudSubmitterException):
    """Raised when the number of Render Steps in a Render Job is different from 1."""

    pass


class MrqJobIsMissingError(DeadlineCloudSubmitterException):
    """Raised when the Render Job or Render step missed the required MRQ job"""

    pass


class OpenJobIsMissingError(DeadlineCloudSubmitterException):
    """Raised when the Render step missed the required Render Job"""

    pass


class UEVersionParseError(DeadlineCloudSubmitterException):
    """Raised when the current Unreal Engine version string cannot be parsed (expected 'x.y')."""

    pass


class UserCancelledSubmissionMismatchedUEVersion(DeadlineCloudSubmitterException, UserException):
    """Raised when Conda Package parameter contains an invalid UE version"""

    pass


class RenderArgumentsTypeNotSetError(DeadlineCloudSubmitterException):
    """Raised when the render arguments type is not set"""

    pass


class PathContainsNonValidCharacters(DeadlineCloudSubmitterException):
    """Raised when the path contains not allowed characters"""

    pass


class FailedToDetectFilesTransferStrategy(DeadlineCloudSubmitterException):
    """Raised when its failed to detect which strategy to use for transfer files to render"""


class ProjectIsNotUnderWorkspaceError(Exception):
    """Raised when current Unreal Project is not under the current Workspace"""
