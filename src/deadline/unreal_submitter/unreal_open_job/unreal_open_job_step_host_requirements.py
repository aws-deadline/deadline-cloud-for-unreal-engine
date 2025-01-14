import unreal
from typing import Any, Optional

from openjd.model.v2023_09 import HostRequirementsTemplate


class HostRequirementsHelper:

    @staticmethod
    def u_host_requirements_to_openjd_host_requirements(
        u_host_requirements: unreal.DeadlineCloudHostRequirementsStruct,
    ) -> Optional[HostRequirementsTemplate]:

        if u_host_requirements.run_on_all_worker_nodes:
            return None

        requirements: dict[str, Any] = {}

        os_requirements = HostRequirementsHelper.get_os_requirements(u_host_requirements)
        if os_requirements:
            # OS requirements are currently all amount type capabilities
            requirements["attributes"] = os_requirements

        hardware_requirements = HostRequirementsHelper.get_hardware_requirements(
            u_host_requirements
        )
        if hardware_requirements:
            # hardware requirements are currently all amount
            requirements["amounts"] = hardware_requirements

        return HostRequirementsTemplate(**requirements)

    @staticmethod
    def get_os_requirements(
        u_host_requirements: unreal.DeadlineCloudHostRequirementsStruct,
    ) -> list[dict]:
        """
        Get requirements for OS family and CPU architecture

        :return: list of the OS requirements
        :rtype: list[dict]
        """

        requirements: list[dict[str, Any]] = []

        if u_host_requirements.operating_system:
            requirements.append(
                {"name": "attr.worker.os.family", "anyOf": [u_host_requirements.operating_system]}
            )
        if u_host_requirements.cpu_architecture:
            requirements.append(
                {"name": "attr.worker.cpu.arch", "anyOf": [u_host_requirements.cpu_architecture]}
            )

        return requirements

    @staticmethod
    def get_hardware_requirements(
        u_host_requirements: unreal.DeadlineCloudHostRequirementsStruct,
    ) -> list[dict[str, Any]]:
        """
        Get requirements for cpu, gpu and memory limits

        :return: list of the OS requirements
        :rtype: list[dict]
        """

        cpus = HostRequirementsHelper.get_amount_requirement(
            u_host_requirements.cp_us, "amount.worker.vcpu"
        )
        cpu_memory = HostRequirementsHelper.get_amount_requirement(
            u_host_requirements.memory, "amount.worker.memory", 1024
        )

        gpus = HostRequirementsHelper.get_amount_requirement(
            u_host_requirements.gp_us, "amount.worker.gpu"
        )
        gpu_memory = HostRequirementsHelper.get_amount_requirement(
            u_host_requirements.gpu_memory, "amount.worker.gpu.memory", 1024
        )

        scratch_space = HostRequirementsHelper.get_amount_requirement(
            u_host_requirements.scratch_space, "amount.worker.disk.scratch"
        )

        requirements: list[dict[str, Any]] = [
            item
            for item in [cpus, cpu_memory, gpus, gpu_memory, scratch_space]
            if HostRequirementsHelper.amount_requirement_is_valid(item)
        ]

        return requirements

    @staticmethod
    def amount_requirement_is_valid(amount_requirement: dict[str, Any]) -> bool:
        if "name" in amount_requirement and (
            "min" in amount_requirement or "max" in amount_requirement
        ):
            return True
        return False

    @staticmethod
    def get_amount_requirement(
        source_interval: unreal.Int32Interval, name: str, scaling_factor: int = 1
    ) -> dict:
        """
        Get the amount of Host Requirement setting interval

        :param source_interval: Interval unreal setting
        :type source_interval: unreal.Int32Interval

        :param name: AWS HostRequirements setting name
        :type name: str

        :param scaling_factor: Multiplier number by which to scale the source_interval values
        :type scaling_factor: int

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
