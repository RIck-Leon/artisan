#
# ABOUT
# Mock-only LLM roast-control envelope sidecar.
# Single control path: map, gate, then log. No serial writes.
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

"""The only control path in this sidecar.

``run_mock_control`` maps each proposal, asks ``EnvelopeGate``, and logs
accepted intents. Rejected proposals are not written. There is no second
path around the gate and no Kaleido serial call.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from llm_envelope.envelope import EnvelopeGate
from llm_envelope.intent_mapper import map_proposal
from llm_envelope.mock_writer import MockWriter
from llm_envelope.models import REASON_MALFORMED, GateDecision, RoastState


def run_mock_control(
    proposals: Iterable[Mapping[str, Any]],
    state: RoastState,
    *,
    gate: EnvelopeGate | None = None,
    writer: MockWriter | None = None,
) -> list[GateDecision]:
    """Map, gate, and log. ``state`` is the caller's snapshot, often a mock."""
    active_gate = gate if gate is not None else EnvelopeGate()
    active_writer = writer if writer is not None else MockWriter(sink=lambda _line: None)
    decisions: list[GateDecision] = []
    for proposal in proposals:
        mapped = map_proposal(proposal)
        if not mapped.ok or mapped.intent is None:
            decisions.append(
                GateDecision(
                    allowed=False,
                    reason=mapped.reason or REASON_MALFORMED,
                    intent=None,
                )
            )
            continue
        decision = active_gate.evaluate(mapped.intent, state)
        if decision.allowed and decision.intent is not None:
            active_writer.write(decision.intent)
        decisions.append(decision)
    return decisions
