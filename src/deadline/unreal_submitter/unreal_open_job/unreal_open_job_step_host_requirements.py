# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

import unreal
from typing import Any, Optional, Union

from openjd.model import parse_model
from openjd.model.v2023_09 import HostRequirementsTemplate


DEFAULT_HOST_REQUIREMENTS: dict[str, list[Any]] = {
    "amounts": [
        {"name": "amount.worker.vcpu", "min": 32},
        {"name": "amount.worker.memory", "min": 8},
        {"name": "amount.worker.gpu", "min": 1},
        {"name": "amount.worker.gpu.memory", "min": 8},
        {"name": "amount.worker.disk.scratch", "min": 16},
    ],
    "attributes": [
        {"name": "attr.worker.os.family", "anyOf": ["windows", "linux", "macos"]},
        {"name": "attr.worker.cpu.arch", "anyOf": ["x86_64", "arm64"]},
    ],
}

FRIENDLY_NAME_MAP = {
    "amount.worker.vcpu": "vCPUs",
    "amount.worker.memory": "Memory",
    "amount.worker.gpu": "GPUs",
    "amount.worker.gpu.memory": "GPU Memory",
    "amount.worker.disk.scratch": "Scratch Space",
    "attr.worker.os.family": "Operating System",
    "attr.worker.cpu.arch": "CPU Architecture",
}


class HostRequirementsHelper:

    @staticmethod
    def is_predefined_requirement_by_name(dict_name: str, name: str) -> bool:
        for req in DEFAULT_HOST_REQUIREMENTS.get(dict_name, []):
            if req["name"] == name:
                return True
        return False

    @staticmethod
    def get_friendly_name(name: str) -> str:
        return FRIENDLY_NAME_MAP.get(name, name)

    @staticmethod
    def parse_amount_requirement(r) -> tuple[Optional[float], Optional[float]]:
        lb = getattr(r, "lower_bound", None)
        ub = getattr(r, "upper_bound", None)

        def _extract_amount_value(b) -> Optional[float]:
            if b is None:
                return None
            btype = getattr(b, "bound_type", getattr(b, "type", None))
            if btype == unreal.RangeBoundTypes.OPEN:
                return None
            val = getattr(b, "value", None)
            if val is None:
                getter = getattr(b, "get_value", None)
                val = getter() if callable(getter) else None
            return float(val) if val is not None else None

        return _extract_amount_value(lb), _extract_amount_value(ub)

    @staticmethod
    def get_host_requirements_from_data_asset(
        data_asset: unreal.DeadlineCloudHostRequirements,
    ) -> Optional[HostRequirementsTemplate]:
        if not data_asset:
            return None

        requirements: dict[str, Any] = {}

        attributes = HostRequirementsHelper.get_attribute_requirements_from_data_asset(
            data_asset.host_requirements.attributes
        )
        if attributes:
            requirements["attributes"] = attributes

        amounts = HostRequirementsHelper.get_amount_requirements_from_data_asset(
            data_asset.host_requirements.amounts
        )
        if amounts:
            requirements["amounts"] = amounts

        if not requirements and not amounts:
            return None

        return parse_model(model=HostRequirementsTemplate, obj=requirements)

    @staticmethod
    def get_amount_requirements_from_data_asset(
        u_host_requirements_amounts: dict[str, unreal.DeadlineCloudAmountRequirement],
    ) -> list[dict]:
        u_amounts_map = u_host_requirements_amounts
        attribute_amounts = []

        for name, req in u_amounts_map.items():
            min_v, max_v = HostRequirementsHelper.parse_amount_requirement(req.amount_requirement)

            if min_v is None and max_v is None:
                continue

            attr: dict[str, Any] = {"name": str(name)}

            if min_v is not None:
                attr["min"] = min_v

            if max_v:
                attr["max"] = max_v

            attribute_amounts.append(attr)

        return attribute_amounts

    @staticmethod
    def _dump(amounts: Optional[list[Any]]) -> list[dict]:
        if not amounts:
            return []
        out: list[dict] = []
        for a in amounts:
            out.append(a.model_dump() if hasattr(a, "model_dump") else dict(a))
        return out

    @staticmethod
    def _set_amount_range(
        amounts: list[dict], name: str, min_value: Optional[float], max_value: Optional[float]
    ) -> list[dict]:
        base = HostRequirementsHelper._exclude_requirements_by_name(amounts, name)
        item: dict[str, Any] = {"name": str(name)}
        if min_value is not None:
            item["min"] = min_value
        if max_value is not None:
            item["max"] = max_value
        base.append(item)
        return base

    @staticmethod
    def _exclude_requirements_by_name(attrs: list[dict], name: str) -> list[dict]:
        return [a for a in attrs if a.get("name") != name]

    @staticmethod
    def _set_attr_value(
        attrs: list[dict], name: str, any_of: Optional[list[str]], all_of: Optional[list[str]]
    ) -> list[dict]:
        base = HostRequirementsHelper._exclude_requirements_by_name(attrs, name)
        item: dict[str, Any] = {"name": str(name)}
        if any_of is not None:
            item["anyOf"] = list(any_of)
        if all_of is not None:
            item["allOf"] = list(all_of)
        base.append(item)
        return base

    @staticmethod
    def add_overrides(
        base: Optional[HostRequirementsTemplate],
        step_host_requirements_override: unreal.DeadlineCloudHostRequirementsOverrides,
    ) -> Optional[HostRequirementsTemplate]:
        base_amounts = HostRequirementsHelper._dump(getattr(base, "amounts", None))
        base_attrs = HostRequirementsHelper._dump(getattr(base, "attributes", None))

        # 1) Amount overrides
        amounts = HostRequirementsHelper._apply_overrides(
            base_amounts, step_host_requirements_override.host_requirements.amounts
        )
        # 2) Attribute overrides
        attrs = HostRequirementsHelper._apply_overrides(
            base_attrs, step_host_requirements_override.host_requirements.attributes
        )

        if not amounts and not attrs:
            return None

        data: dict[str, Any] = {}
        if amounts:
            data["amounts"] = amounts
        if attrs:
            data["attributes"] = attrs

        return parse_model(model=HostRequirementsTemplate, obj=data)

    @staticmethod
    def _apply_overrides(
        base: list[dict],
        overrides: Union[
            unreal.DeadlineCloudAmountRequirement, unreal.DeadlineCloudAttributeRequirements
        ],
    ) -> list[dict]:
        result = list(base)
        for name, req in overrides.items():
            if not req.is_enabled:
                result = HostRequirementsHelper._exclude_requirements_by_name(result, name)
            else:
                if isinstance(req, unreal.DeadlineCloudAttributeRequirements):
                    any_of: Optional[list[str]]
                    all_of: Optional[list[str]]
                    if HostRequirementsHelper.is_predefined_requirement_by_name("attributes", name):
                        any_of = [req.selected_value]
                        all_of = None
                    else:
                        any_of = list(req.any_of) if getattr(req, "any_of", None) else None
                        all_of = list(req.all_of) if getattr(req, "all_of", None) else None
                    result = HostRequirementsHelper._set_attr_value(result, name, any_of, all_of)

                if isinstance(req, unreal.DeadlineCloudAmountRequirement):
                    min_req, max_req = HostRequirementsHelper.parse_amount_requirement(
                        req.amount_requirement
                    )
                    result = HostRequirementsHelper._set_amount_range(
                        result, name, min_req, max_req
                    )

        return result

    @staticmethod
    def get_attribute_requirements_from_data_asset(
        u_host_requirements_attributes: dict[str, unreal.DeadlineCloudAttributeRequirements],
    ) -> list[dict]:
        u_attributes_map = u_host_requirements_attributes
        attribute_requirements = []

        for name, req in u_attributes_map.items():

            attr: dict[str, Any] = {"name": str(name)}
            if HostRequirementsHelper.is_predefined_requirement_by_name("amounts", name):
                attr["anyOf"] = [req.selected_value]
            else:
                if req.all_of:
                    attr["allOf"] = list(req.all_of)

                if req.any_of:
                    attr["anyOf"] = list(req.any_of)

            attribute_requirements.append(attr)

        return attribute_requirements
