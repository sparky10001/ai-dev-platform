#!/usr/bin/env python3
###################################################################
# runtime/contracts.py
#
# Phase 3E Runtime Contract Specification Layer
#
# Responsibilities:
# - explicit versioned contract specifications
# - canonical event/response/dataset/eval/registry contracts
# - centralized contract validation helpers
# - compatibility and deterministic serialization helpers
#
###################################################################

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field

from runtime.schemas import DatasetRecord
from runtime.schemas import EvalComparison
from runtime.schemas import EvalDatasetRecord
from runtime.schemas import EvalSummary
from runtime.schemas import EVENT_MODELS
from runtime.schemas import ResponseModel
from runtime.schemas import RunQueryResult
from runtime.schemas import RunSummary
from runtime.schemas import SCHEMA_VERSION
from runtime.schemas import TraceDatasetRecord


CONTRACT_VERSION = 1


class ContractModel(BaseModel):

    model_config = ConfigDict(
        extra='allow',
        frozen=False,
    )

    contract_version: int = CONTRACT_VERSION


class EventContract(ContractModel):

    schema_version: int = SCHEMA_VERSION

    required_fields: list[str] = Field(
        default_factory=lambda: [
            'schema_version',
            'timestamp',
            'run_id',
            'event',
            'data',
        ]
    )

    event_types: list[str] = Field(
        default_factory=lambda: sorted(EVENT_MODELS.keys())
    )


class ResponseContract(ContractModel):

    schema_version: int = SCHEMA_VERSION

    required_fields: list[str] = Field(
        default_factory=lambda: [
            'schema_version',
            'status',
            'output',
            'meta',
        ]
    )

    statuses: list[str] = Field(
        default_factory=lambda: ['done', 'error']
    )


class DatasetContract(ContractModel):

    schema_version: int = SCHEMA_VERSION

    record_types: list[str] = Field(
        default_factory=lambda: [
            'DatasetRecord',
            'EvalDatasetRecord',
            'TraceDatasetRecord',
        ]
    )


class EvalContract(ContractModel):

    schema_version: int = SCHEMA_VERSION

    record_types: list[str] = Field(
        default_factory=lambda: [
            'EvalSummary',
            'EvalComparison',
        ]
    )


class RegistryContract(ContractModel):

    schema_version: int = SCHEMA_VERSION

    record_types: list[str] = Field(
        default_factory=lambda: [
            'RunQueryResult',
            'RunSummary',
        ]
    )


def validate_event_contract(payload: dict[str, Any]):

    if not isinstance(payload, dict):
        raise TypeError('Event payload must be dict')

    event_type = payload.get('event')

    if not event_type:
        raise ValueError('Missing event field')

    model = EVENT_MODELS.get(event_type)

    if not model:
        raise ValueError(f'Unknown event type: {event_type}')

    return model.model_validate(payload)


def validate_response_contract(payload: dict[str, Any]):

    if not isinstance(payload, dict):
        raise TypeError('Response payload must be dict')

    return ResponseModel.model_validate(payload)


def validate_dataset_record(payload: dict[str, Any]):

    if not isinstance(payload, dict):
        raise TypeError('Dataset payload must be dict')

    if {'run', 'result', 'trace', 'eval'}.issubset(payload.keys()):
        return DatasetRecord.model_validate(payload)

    if {'event_index', 'event'}.issubset(payload.keys()):
        return TraceDatasetRecord.model_validate(payload)

    if 'eval' in payload:
        return EvalDatasetRecord.model_validate(payload)

    raise ValueError('Unknown dataset record contract')


def validate_eval_record(payload: dict[str, Any]):

    if not isinstance(payload, dict):
        raise TypeError('Eval payload must be dict')

    if {'run_a', 'run_b'}.issubset(payload.keys()):
        return EvalComparison.model_validate(payload)

    return EvalSummary.model_validate(payload)


def _compatible(old: Any, new: Any) -> bool:

    if isinstance(old, dict):
        if not isinstance(new, dict):
            return False

        for key, value in old.items():
            if key not in new:
                return False
            if not _compatible(value, new[key]):
                return False

        return True

    if isinstance(old, list):
        if not isinstance(new, list):
            return False
        if not old:
            return True
        if not new:
            return False
        return _compatible(old[0], new[0])

    if old is None:
        return True

    return isinstance(new, old.__class__)


def assert_backward_compatible(old: Any, new: Any):

    if not _compatible(old, new):
        raise ValueError('Breaking change detected: incompatible contract shape')


def assert_no_breaking_changes():

    if CONTRACT_VERSION < 1:
        raise ValueError('Invalid contract version')

    if SCHEMA_VERSION < 1:
        raise ValueError('Invalid schema version')

    required_events = {
        'session_start',
        'tool_call',
        'tool_result',
        'agent_output',
        'session_end',
    }

    missing = sorted(required_events - set(EVENT_MODELS.keys()))

    if missing:
        raise ValueError(f'Missing required event contracts: {", ".join(missing)}')


def to_canonical_json(obj: Any) -> str:

    if hasattr(obj, 'model_dump'):
        payload = obj.model_dump(mode='json')
    else:
        payload = obj

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(',', ':'),
    )
