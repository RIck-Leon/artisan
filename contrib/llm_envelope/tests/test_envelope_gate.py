#
# ABOUT
# Mock-only LLM roast-control envelope sidecar tests.
# Proves the fail-closed gate and the log-only writer.
#
# COPYRIGHT (C) 2010-2026 The artisan team represented by
#   Marko Luther <marko.luther@gmx.net> (maintainer) and all contributors
#
# LICENSE
# This program or module is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

"""Safety tests for the mock envelope sidecar.

State objects in this file are injected mocks. They are not machine telemetry.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from llm_envelope.envelope import EnvelopeGate
from llm_envelope.intent_mapper import map_proposal
from llm_envelope.mock_writer import MockWriter
from llm_envelope.models import (
    APPROVED_ABSOLUTE_MAX_C,
    APPROVED_MAX_DELTA_SV_C,
    APPROVED_MAX_ROR_C_PER_MIN,
    APPROVED_SV_MIN_C,
    REASON_BT_ABOVE_MAX,
    REASON_DELTA_SV,
    REASON_ET_ABOVE_MAX,
    REASON_MALFORMED,
    REASON_ROR,
    REASON_SV_ABOVE_MAX,
    REASON_SV_BELOW_MIN,
    REASON_UNKNOWN_INTENT,
    REASON_USB_FAULT,
    EnvelopeConfig,
    RoastState,
)
from llm_envelope.pipeline import run_mock_control


def mock_state(**overrides: object) -> RoastState:
    """Build an in-envelope mock snapshot. Overrides replace one field at a time."""
    base: dict[str, object] = {
        'bt_c': 160.0,
        'et_c': 190.0,
        'sv_c': 155.0,
        'ror_c_per_min': 12.0,
        'usb_fault': False,
    }
    base.update(overrides)
    return RoastState(**base)  # type: ignore[arg-type]


def _drive(
    proposal: object,
    state: RoastState,
    writer: MockWriter | None = None,
) -> tuple[object, MockWriter]:
    sink: list[str] = []
    active = writer if writer is not None else MockWriter(sink=sink.append)
    decisions = run_mock_control([proposal], state, writer=active)  # type: ignore[list-item]
    return decisions[0], active


def test_allows_in_range_set_sv_and_send_event() -> None:
    decision, writer = _drive({'action': 'set_SV', 'sv': 158.0}, mock_state())
    assert decision.allowed is True
    assert decision.reason == 'ok'
    assert writer.records == [{'intent': 'set_SV', 'sv': 158.0}]

    edge, edge_writer = _drive(
        {'intent': 'set_sv', 'sv': 250.0},
        mock_state(bt_c=250.0, et_c=250.0, sv_c=245.0, ror_c_per_min=30.0),
    )
    assert edge.allowed is True
    assert edge_writer.records == [{'intent': 'set_SV', 'sv': 250.0}]

    floor, floor_writer = _drive(
        {'action': 'setSV', 'sv': 0},
        mock_state(sv_c=0.0),
    )
    assert floor.allowed is True
    assert floor_writer.records == [{'intent': 'set_SV', 'sv': 0.0}]

    event, event_writer = _drive(
        {'action': 'send_event', 'event': 'CHARGE'},
        mock_state(),
    )
    assert event.allowed is True
    assert event_writer.records == [{'intent': 'send_Event', 'event': 'CHARGE'}]


def test_rejects_sv_outside_absolute_bounds() -> None:
    high, high_writer = _drive({'action': 'set_SV', 'sv': 250.1}, mock_state(sv_c=250.0))
    assert high.allowed is False
    assert high.reason == REASON_SV_ABOVE_MAX
    assert high_writer.records == []

    low, low_writer = _drive({'action': 'set_SV', 'sv': -0.1}, mock_state(sv_c=0.0))
    assert low.allowed is False
    assert low.reason == REASON_SV_BELOW_MIN
    assert low_writer.records == []


def test_rejects_delta_sv_above_5c() -> None:
    decision, writer = _drive({'action': 'set_SV', 'sv': 161.0}, mock_state(sv_c=155.0))
    assert decision.allowed is False
    assert decision.reason == REASON_DELTA_SV
    assert writer.records == []

    exact, exact_writer = _drive({'action': 'set_SV', 'sv': 160.0}, mock_state(sv_c=155.0))
    assert exact.allowed is True
    assert exact_writer.records == [{'intent': 'set_SV', 'sv': 160.0}]


def test_rejects_all_writes_when_usb_fault() -> None:
    state = mock_state(usb_fault=True)
    for proposal in (
        {'action': 'set_SV', 'sv': 156.0},
        {'action': 'send_Event', 'event': 'CHARGE'},
    ):
        decision, writer = _drive(proposal, state)
        assert decision.allowed is False
        assert decision.reason == REASON_USB_FAULT
        assert writer.records == []


def test_rejects_unknown_intent() -> None:
    decision, writer = _drive({'intent': 'set_heater', 'sv': 156.0}, mock_state())
    assert decision.allowed is False
    assert decision.reason == REASON_UNKNOWN_INTENT
    assert writer.records == []

    mapped = map_proposal({'action': 'pid_off'})
    assert mapped.ok is False
    assert mapped.intent is None

    gate_decision = EnvelopeGate().evaluate(object(), mock_state())
    assert gate_decision.allowed is False
    assert gate_decision.reason == REASON_UNKNOWN_INTENT


def test_mapper_fail_closed_on_malformed_proposals() -> None:
    samples = [
        None,
        ['set_SV'],
        'set_SV',
        {},
        {'action': 'set_SV'},
        {'action': 'set_SV', 'sv': True},
        {'action': 'set_SV', 'sv': '200'},
        {'action': 'set_SV', 'sv': float('nan')},
        {'intent': 'set_SV', 'action': 'set_SV', 'sv': 156.0},
        {'action': 'set_SV', 'sv': 156.0, 'port': '/dev/ttyUSB0'},
        {'action': 'send_Event', 'event': ''},
        {'action': 'send_Event', 'event': 'CHARGE; rm'},
        {'action': 'send_Event', 'event': 'externalprogram'},
        {'action': 1, 'sv': 156.0},
    ]
    for proposal in samples:
        decision, writer = _drive(proposal, mock_state())
        assert decision.allowed is False
        assert decision.reason == REASON_MALFORMED
        assert decision.intent is None
        assert writer.records == []


def test_rejects_ror_above_soft_ceiling() -> None:
    decision, writer = _drive(
        {'action': 'set_SV', 'sv': 156.0},
        mock_state(ror_c_per_min=30.1),
    )
    assert decision.allowed is False
    assert decision.reason == REASON_ROR
    assert writer.records == []

    event, event_writer = _drive(
        {'action': 'send_Event', 'event': 'DROP'},
        mock_state(ror_c_per_min=31.0),
    )
    assert event.allowed is False
    assert event.reason == REASON_ROR
    assert event_writer.records == []


def test_rejects_bt_and_et_above_absolute_max() -> None:
    bt, bt_writer = _drive(
        {'action': 'set_SV', 'sv': 156.0},
        mock_state(bt_c=250.1),
    )
    assert bt.allowed is False
    assert bt.reason == REASON_BT_ABOVE_MAX
    assert bt_writer.records == []

    et, et_writer = _drive(
        {'action': 'send_Event', 'event': 'FC'},
        mock_state(et_c=251.0),
    )
    assert et.allowed is False
    assert et.reason == REASON_ET_ABOVE_MAX
    assert et_writer.records == []

    missing, missing_writer = _drive(
        {'action': 'set_SV', 'sv': 156.0},
        mock_state(bt_c=None),
    )
    assert missing.allowed is False
    assert missing.reason == 'incomplete_state'
    assert missing_writer.records == []


def test_profile_fields_are_ignored_and_never_executed(monkeypatch: pytest.MonkeyPatch) -> None:
    def _executed(*_args: object, **_kwargs: object) -> None:
        raise AssertionError('profile field was executed')

    monkeypatch.setattr(subprocess, 'Popen', _executed)
    monkeypatch.setattr(os, 'system', _executed)
    monkeypatch.setattr(os, 'popen', _executed)

    only_profile, only_writer = _drive(
        {
            'externalprogram': 'test.py',
            'alarmaction': [1, 2, 3],
            'externaloutprogram': 'out.py',
        },
        mock_state(),
    )
    assert only_profile.allowed is False
    assert only_writer.records == []

    mixed, mixed_writer = _drive(
        {
            'action': 'set_SV',
            'sv': 158.0,
            'externalprogram': 'test.py',
            'alarmaction': ['kaleido(TS, 999)'],
            'externaloutprogram': 'out.py',
        },
        mock_state(),
    )
    assert mixed.allowed is True
    assert mixed_writer.records == [{'intent': 'set_SV', 'sv': 158.0}]
    blob = json.dumps(mixed_writer.records)
    assert 'test.py' not in blob
    assert 'out.py' not in blob
    assert 'kaleido' not in blob
    assert 'externalprogram' not in blob


def test_mock_writer_logs_only_allowlisted_payloads() -> None:
    writer = MockWriter(sink=lambda _line: None)
    proposals = [
        {'action': 'set_SV', 'sv': 158.0},
        {'action': 'send_Event', 'event': 'CHARGE'},
        {'action': 'set_SV', 'sv': 400.0},
        {'intent': 'drop_beans'},
        {'action': 'send_Event', 'event': 'DRY_END'},
    ]
    decisions = run_mock_control(proposals, mock_state(), writer=writer)
    assert [decision.allowed for decision in decisions] == [True, True, False, False, True]
    assert writer.records == [
        {'intent': 'set_SV', 'sv': 158.0},
        {'intent': 'send_Event', 'event': 'CHARGE'},
        {'intent': 'send_Event', 'event': 'DRY_END'},
    ]
    for record in writer.records:
        assert record['intent'] in {'set_SV', 'send_Event'}
        if record['intent'] == 'set_SV':
            assert set(record) == {'intent', 'sv'}
        else:
            assert set(record) == {'intent', 'event'}


def test_envelope_defaults_cannot_be_loosened_or_inferred() -> None:
    config = EnvelopeConfig()
    assert config.sv_min_c == APPROVED_SV_MIN_C == 0.0
    assert config.absolute_max_c == APPROVED_ABSOLUTE_MAX_C == 250.0
    assert config.max_delta_sv_c == APPROVED_MAX_DELTA_SV_C == 5.0
    assert config.max_ror_c_per_min == APPROVED_MAX_ROR_C_PER_MIN == 30.0

    with pytest.raises(ValueError):
        EnvelopeConfig(absolute_max_c=251)
    with pytest.raises(ValueError):
        EnvelopeConfig(max_delta_sv_c=6)
    with pytest.raises(ValueError):
        EnvelopeConfig(max_ror_c_per_min=31)
    with pytest.raises(ValueError):
        EnvelopeConfig(sv_min_c=-1)

    tighter = EnvelopeConfig(absolute_max_c=240, max_delta_sv_c=2, max_ror_c_per_min=20)
    smuggled, smuggled_writer = _drive(
        {
            'action': 'set_SV',
            'sv': 200.0,
            'absolute_max_c': 500,
            'externalprogram': 'test.py',
        },
        mock_state(sv_c=198.0),
    )
    assert smuggled.allowed is False
    assert smuggled.reason == REASON_MALFORMED
    assert smuggled_writer.records == []

    gate = EnvelopeGate(tighter)
    held = gate.evaluate(
        map_proposal({'action': 'set_SV', 'sv': 158.0}).intent,
        mock_state(sv_c=155.0),
    )
    assert held.allowed is False
    assert held.reason == REASON_DELTA_SV


def test_sidecar_sources_do_not_import_serial() -> None:
    package = Path(__file__).resolve().parents[1] / 'llm_envelope'
    import_re = re.compile(r'^\s*(?:import|from)\s+([A-Za-z0-9_\.]+)')
    sources = list(package.glob('*.py'))
    assert sources
    for path in sources:
        for line in path.read_text(encoding='utf-8').splitlines():
            if line.lstrip().startswith('#'):
                continue
            match = import_re.match(line)
            if match is None:
                continue
            module = match.group(1)
            assert 'serial' not in module
            assert 'kaleido' not in module
            assert not module.startswith('artisanlib')


def test_mock_demo_prints_only_allowlisted_payloads() -> None:
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run(
        [sys.executable, '-m', 'llm_envelope.demo'],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    assert proc.stdout.splitlines() == [
        '{"intent": "set_SV", "sv": 158.0}',
        '{"intent": "send_Event", "event": "CHARGE"}',
    ]
    assert 'serial' not in proc.stdout.lower()
    assert 'NO-GO' in proc.stderr
