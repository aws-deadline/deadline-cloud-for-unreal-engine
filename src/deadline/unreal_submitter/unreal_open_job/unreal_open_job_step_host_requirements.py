import unreal
from typing import Any


class HostRequirements:
    """OpenJob host requirements representation"""

    def __init__(self, host_requirements: unreal.DeadlineCloudHostRequirementsStruct):
        self.source_host_requirements = host_requirements
        self.requirements: dict = {}

        os_requirements = self._get_os_requirements()
        if os_requirements:
            # OS requirements are currently all amount type capabilities
            self.requirements["attributes"] = os_requirements

        hardware_requirements = self._get_hardware_requirements()
        if hardware_requirements:
            # hardware requirements are currently all amount
            self.requirements["amounts"] = hardware_requirements

    def _get_os_requirements(self) -> list[dict]:
        """
        Get requirements for OS family and CPU architecture

        :return: list of the OS requirements
        :rtype: list[dict]
        """
        requirements: list[dict] = []
        if self.source_host_requirements.operating_system:
            requirements.append(
                {
                    "name": "attr.worker.os.family",
                    "anyOf": [self.source_host_requirements.operating_system],
                }
            )
        if self.source_host_requirements.cpu_architecture:
            requirements.append(
                {
                    "name": "attr.worker.cpu.arch",
                    "anyOf": [self.source_host_requirements.cpu_architecture],
                }
            )
        return requirements

    def _get_hardware_requirements(self) -> list[dict[str, Any]]:
        """
        Get requirements for cpu, gpu and memory limits

        :return: list of the OS requirements
        :rtype: list[dict]
        """
        cpus = self._get_amount_requirement(
            self.source_host_requirements.cp_us, "amount.worker.vcpu"
        )
        memory = self._get_amount_requirement(
            self.source_host_requirements.memory, "amount.worker.memory", 1024
        )

        gpus = self._get_amount_requirement(
            self.source_host_requirements.gp_us, "amount.worker.gpu"
        )
        gpu_memory = self._get_amount_requirement(
            self.source_host_requirements.gpu_memory, "amount.worker.gpu.memory", 1024
        )

        scratch_space = self._get_amount_requirement(
            self.source_host_requirements.scratch_space, "amount.worker.disk.scratch"
        )

        requirements: list[dict[str, Any]] = [
            item for item in [cpus, memory, gpus, gpu_memory, scratch_space] if item is not None
        ]

        return requirements

    @staticmethod
    def _get_amount_requirement(source_interval, name: str, scaling_factor: int = 1) -> dict:
        """
        Helper method to get the amount of Host Requirement setting interval

        :param source_interval: Interval unreal setting
        :param name: AWS HostRequirements setting name
        :param scaling_factor: Multiplier number by which to scale the source_interval values

        :return: Amount requirement as dictionary
        :rtype: dict
        """
        requirement = {}
        if source_interval.min > 0 or source_interval.max > 0:
            requirement = {"name": name}
            if source_interval.min > 0:
                requirement["min"] = source_interval.min * scaling_factor
            if source_interval.max > 0:
                requirement["max"] = source_interval.max * scaling_factor
        return requirement

    def as_dict(self) -> dict:
        """
        Returns the HostRequirements as dictionary

        :return: Host Requirements as dictionary
        :rtype: dict
        """
        return self.requirements
