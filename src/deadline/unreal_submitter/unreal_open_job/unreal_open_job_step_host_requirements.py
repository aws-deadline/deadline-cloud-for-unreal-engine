import unreal
from typing import Any


class OperatingSystemOption:

    WINDOWS = "windows"
    LINUX = "linux"
    MACOS = "macos"


class CpuArchitectureOption:

    X86_64 = "x86_64"
    ARM64 = "arm64"


class HostRequirements:
    """OpenJob host requirements representation"""

    def __init__(
        self,
        run_on_all_worker_nodes: bool = True,
        operating_system: str = OperatingSystemOption.WINDOWS,
        cpu_architecture: str = CpuArchitectureOption.X86_64,
        cpu_count: tuple[int, int] = (0, 0),
        cpu_memory_gb: tuple[int, int] = (0, 0),
        gpu_count: tuple[int, int] = (0, 0),
        gpu_memory_gb: tuple[int, int] = (0, 0),
        scratch_space: tuple[int, int] = (0, 0),
    ):
        self._run_on_all_worker_nodes = run_on_all_worker_nodes

        self._operating_system = operating_system

        self._cpu_architecture = cpu_architecture
        self._cpu_count = cpu_count
        self._cpu_memory_gb = cpu_memory_gb

        self._gpu_count = gpu_count
        self._gpu_memory_gb = gpu_memory_gb

        self._scratch_space = scratch_space

    @property
    def run_on_all_worker_nodes(self) -> bool:
        return self._run_on_all_worker_nodes

    @classmethod
    def from_u_deadline_cloud_host_requirements(
        cls, host_requirements: unreal.DeadlineCloudHostRequirementsStruct
    ):
        return cls(
            run_on_all_worker_nodes=host_requirements.run_on_all_worker_nodes,
            operating_system=host_requirements.operating_system,
            cpu_architecture=host_requirements.cpu_architecture,
            cpu_count=(host_requirements.cp_us.min, host_requirements.cp_us.max),
            cpu_memory_gb=(host_requirements.memory.min, host_requirements.memory.max),
            gpu_count=(host_requirements.gp_us.min, host_requirements.gp_us.max),
            gpu_memory_gb=(host_requirements.gpu_memory.min, host_requirements.gpu_memory.max),
            scratch_space=(
                host_requirements.scratch_space.min,
                host_requirements.scratch_space.max,
            ),
        )

    def _get_os_requirements(self) -> list[dict]:
        """
        Get requirements for OS family and CPU architecture

        :return: list of the OS requirements
        :rtype: list[dict]
        """
        requirements: list[dict[str, Any]] = []
        if self._operating_system:
            requirements.append(
                {"name": "attr.worker.os.family", "anyOf": [self._operating_system]}
            )
        if self._cpu_architecture:
            requirements.append({"name": "attr.worker.cpu.arch", "anyOf": [self._cpu_architecture]})

        return requirements

    def _get_hardware_requirements(self) -> list[dict[str, Any]]:
        """
        Get requirements for cpu, gpu and memory limits

        :return: list of the OS requirements
        :rtype: list[dict]
        """
        cpus = self._get_amount_requirement(self._cpu_count, "amount.worker.vcpu")

        memory = self._get_amount_requirement(self._cpu_memory_gb, "amount.worker.memory", 1024)

        gpus = self._get_amount_requirement(self._gpu_count, "amount.worker.gpu")
        gpu_memory = self._get_amount_requirement(
            self._gpu_memory_gb, "amount.worker.gpu.memory", 1024
        )

        scratch_space = self._get_amount_requirement(
            self._scratch_space, "amount.worker.disk.scratch"
        )

        requirements: list[dict[str, Any]] = [
            item
            for item in [cpus, memory, gpus, gpu_memory, scratch_space]
            if self._amount_requirement_is_valid(item)
        ]

        return requirements

    @staticmethod
    def _amount_requirement_is_valid(amount_requirement: dict[str, Any]) -> bool:
        if "name" in amount_requirement and (
            "min" in amount_requirement or "max" in amount_requirement
        ):
            return True
        return False

    @staticmethod
    def _get_amount_requirement(source_interval: tuple, name: str, scaling_factor: int = 1) -> dict:
        """
        Helper method to get the amount of Host Requirement setting interval

        :param source_interval: Interval represented as tuple
        :param name: AWS HostRequirements setting name
        :param scaling_factor: Multiplier number by which to scale the source_interval values

        :return: Amount requirement as dictionary
        :rtype: dict
        """
        requirement: dict[str, Any] = {}

        if source_interval is None or len(source_interval) != 2:
            return requirement

        interval_min = source_interval[0]
        interval_max = source_interval[1]

        if interval_min > 0 or interval_max > 0:
            requirement = {"name": name}

            if interval_min > 0:
                requirement["min"] = interval_min * scaling_factor

            if interval_max > 0:
                requirement["max"] = interval_max * scaling_factor

        return requirement

    def as_dict(self) -> dict:
        """
        Returns the HostRequirements as dictionary

        :return: Host Requirements as dictionary
        :rtype: dict
        """
        requirements: dict[str, Any] = {}

        os_requirements = self._get_os_requirements()
        if os_requirements:
            # OS requirements are currently all amount type capabilities
            requirements["attributes"] = os_requirements

        hardware_requirements = self._get_hardware_requirements()
        if hardware_requirements:
            # hardware requirements are currently all amount
            requirements["amounts"] = hardware_requirements

        return requirements
