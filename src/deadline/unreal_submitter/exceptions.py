#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.


class DeadlineCloudSubmitterException(Exception):
    """Base exception for all deadline-cloud-for-unreal-engine custom exceptions"""

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


class RenderArgumentsTypeNotSetError(DeadlineCloudSubmitterException):
    """Raised when the render arguments type is not set"""

    pass


class FailedToDetectFilesTransferStrategy(DeadlineCloudSubmitterException):
    """Raised when its failed to detect which strategy to use for transfer files to render"""
