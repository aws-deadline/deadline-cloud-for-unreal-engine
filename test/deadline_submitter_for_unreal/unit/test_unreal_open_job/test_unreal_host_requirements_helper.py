# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

from dataclasses import dataclass
from typing import List, Optional, cast, Any

from deadline.unreal_submitter.unreal_open_job.unreal_open_job_step_host_requirements import (
    HostRequirementsHelper,
)


class _RangeBoundTypes:
    # Range boundary types matching Unreal Engine's ERangeBoundTypes.
    # OPEN   — open boundary (the value is not included in the range)
    # CLOSED — closed boundary (the value is included in the range)
    OPEN = "OPEN"
    CLOSED = "CLOSED"


@dataclass
class _Bound:
    bound_type: str = _RangeBoundTypes.CLOSED
    value: Optional[float] = None

    def get_value(self):
        return self.value


@dataclass
class _Range:
    lower_bound: Optional[_Bound] = None
    upper_bound: Optional[_Bound] = None


@dataclass
class _AmountRequirementEntry:
    is_enabled: bool
    amount_requirement: _Range


@dataclass
class _AttributeRequirementEntry:
    is_enabled: bool
    any_of: Optional[List[str]] = None
    all_of: Optional[List[str]] = None


def _mk_amount_entry(lb=None, ub=None, enabled=True):
    return _AmountRequirementEntry(
        is_enabled=enabled,
        amount_requirement=_Range(lower_bound=lb, upper_bound=ub),
    )


def _mk_attr_entry(any_of=None, all_of=None, enabled=True):
    return _AttributeRequirementEntry(is_enabled=enabled, any_of=any_of, all_of=all_of)


def _sorted_by_name(items: List[dict]):
    return sorted(items, key=lambda d: d["name"])


class TestRangeToMinMax:
    def test_both_closed(self):
        lb = _Bound(bound_type=_RangeBoundTypes.CLOSED, value=1)
        ub = _Bound(bound_type=_RangeBoundTypes.CLOSED, value=5.5)
        assert HostRequirementsHelper.parse_amount_requirement(_Range(lb, ub)) == (1.0, 5.5)

    def test_open_lower_and_missing_upper(self):
        lb = _Bound(bound_type=_RangeBoundTypes.OPEN, value=10)
        assert HostRequirementsHelper.parse_amount_requirement(_Range(lb, None)) == (10.0, None)

    def test_uses_get_value_when_value_none(self):
        b = _Bound(bound_type=_RangeBoundTypes.CLOSED, value=None)
        cast(Any, b).get_value = lambda: 7
        assert HostRequirementsHelper.parse_amount_requirement(_Range(b, None)) == (7.0, None)


class TestGetUHostRequirementsAmounts:
    def test_parses_amounts_min_max(self):
        amounts = {
            "cpu": _mk_amount_entry(lb=_Bound(value=4), ub=_Bound(value=16)),
            "ram": _mk_amount_entry(lb=_Bound(value=None), ub=_Bound(value=64)),
        }

        got = HostRequirementsHelper.get_amount_requirements_from_data_asset(amounts)
        assert _sorted_by_name(got) == [
            {"name": "cpu", "min": 4.0, "max": 16.0},
            {"name": "ram", "max": 64.0},
        ]

    def test_zeros_are_omitted_due_to_truthiness_check(self):
        amounts = {"gpu": _mk_amount_entry(lb=_Bound(value=0.0), ub=_Bound(value=0.0))}
        got = HostRequirementsHelper.get_amount_requirements_from_data_asset(amounts)
        assert got == [{"name": "gpu", "min": 0.0}]


class TestGetUHostAttributesRequirement:
    def test_parses_attributes(self):
        attributes = {"os": _mk_attr_entry(any_of=["linux", "windows"])}

        got = HostRequirementsHelper.get_attribute_requirements_from_data_asset(attributes)
        assert _sorted_by_name(got) == [{"name": "os", "anyOf": ["linux", "windows"]}]


class TestDumpHelpers:
    def test_dump_amounts_accepts_objects_with_model_dump(self):
        class Obj:
            def __init__(self, d):
                self._d = d

            def model_dump(self):
                return self._d

        items = [Obj({"name": "cpu", "min": 4}), Obj({"name": "ram", "max": 32})]
        assert HostRequirementsHelper._dump(items) == [
            {"name": "cpu", "min": 4},
            {"name": "ram", "max": 32},
        ]

    def test_dump_attrs_accepts_plain_dicts_and_objects(self):
        class Obj:
            def __init__(self, d):
                self._d = d

            def model_dump(self):
                return self._d

        items = [
            {"name": "os", "anyOf": ["linux"]},
            Obj({"name": "gpuVendor", "allOf": ["nvidia"]}),
        ]
        assert _sorted_by_name(HostRequirementsHelper._dump(items)) == [
            {"name": "gpuVendor", "allOf": ["nvidia"]},
            {"name": "os", "anyOf": ["linux"]},
        ]

    def test_dump_helpers_handle_none_and_empty(self):
        assert HostRequirementsHelper._dump(None) == []
        assert HostRequirementsHelper._dump([]) == []
        assert HostRequirementsHelper._dump(None) == []
        assert HostRequirementsHelper._dump([]) == []


class TestPrivateMutationHelpers:
    def test_amounts_without_and_upsert(self):
        amounts = [{"name": "cpu", "min": 4}, {"name": "ram", "min": 16}]
        out = HostRequirementsHelper._exclude_requirements_by_name(amounts, "cpu")
        assert out == [{"name": "ram", "min": 16}]

        out2 = HostRequirementsHelper._set_amount_range(out, "gpu", None, 1.0)
        assert _sorted_by_name(out2) == [{"name": "gpu", "max": 1.0}, {"name": "ram", "min": 16}]

        out3 = HostRequirementsHelper._set_amount_range(out2, "ram", 8.0, None)
        assert _sorted_by_name(out3) == [{"name": "gpu", "max": 1.0}, {"name": "ram", "min": 8.0}]

    def test_attrs_exclude_and_set_value(self):
        attrs = [{"name": "os", "anyOf": ["linux"]}, {"name": "gpuVendor", "allOf": ["nvidia"]}]
        out = HostRequirementsHelper._exclude_requirements_by_name(attrs, "gpuVendor")
        assert out == [{"name": "os", "anyOf": ["linux"]}]

        out2 = HostRequirementsHelper._set_attr_value(out, "gpuVendor", None, ["nvidia"])
        assert _sorted_by_name(out2) == [
            {"name": "gpuVendor", "allOf": ["nvidia"]},
            {"name": "os", "anyOf": ["linux"]},
        ]

        out3 = HostRequirementsHelper._set_attr_value(out2, "os", ["linux", "windows"], None)
        assert _sorted_by_name(out3) == [
            {"name": "gpuVendor", "allOf": ["nvidia"]},
            {"name": "os", "anyOf": ["linux", "windows"]},
        ]
