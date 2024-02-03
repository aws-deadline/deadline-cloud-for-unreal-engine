#  Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import os

from openjd.adaptor_runtime.adaptors import AdaptorDataValidators


def add_module_to_pythonpath(module_path: str):
    """
    Extend or create env variable PYTHONPATH and add there the given path
    """

    # can be passed the __init__.py file or the parent directory
    module_directory = os.path.dirname(module_path) if os.path.isfile(module_path) else module_path

    if 'PYTHONPATH' in os.environ:
        os.environ['PYTHONPATH'] = f'{os.environ["PYTHONPATH"]}{os.pathsep}{module_directory}'
    else:
        os.environ["PYTHONPATH"] = module_directory


class DataValidation:
    """
    Common class for validating init and run data
    """

    def __init__(self):
        cur_dir = os.path.dirname(__file__)
        schema_dir = os.path.join(cur_dir, "schemas")
        self.validators = AdaptorDataValidators.for_adaptor(schema_dir)

    def validate_init_data(self, init_data: dict):
        """
        Validate the given init data

        :param init_data: Initial adaptor data
        :type init_data: dict

        :raises jsonschema.exceptions.ValidationError: if the instance is invalid
        :raises: jsonschema.exceptions.SchemaError: if the schema itself is invalid
        """
        self.validators.init_data.validate(init_data)

    def validate_run_data(self, run_data: dict):
        """
        Validate the given run data

        :raises jsonschema.exceptions.ValidationError: if the instance is invalid
        :raises jsonschema.exceptions.SchemaError: if the schema itself is invalid
        """

        self.validators.run_data.validate(run_data)
