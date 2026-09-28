#
# ABOUT
# Mock-only LLM roast-control envelope sidecar.
# Public API. Does not write Kaleido serial.
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

"""Mock-only fail-closed roast-control envelope.

Architecture for this slice::

    curve/state → laya/stub → intent_mapper → EnvelopeGate → mock log

Real Artisan Kaleido serial writes are NO-GO here.
"""

from llm_envelope.envelope import EnvelopeGate
from llm_envelope.intent_mapper import MapResult, map_proposal
from llm_envelope.mock_writer import MockWriter
from llm_envelope.models import (
    APPROVED_ABSOLUTE_MAX_C,
    APPROVED_MAX_DELTA_SV_C,
    APPROVED_MAX_ROR_C_PER_MIN,
    APPROVED_SV_MIN_C,
    EnvelopeConfig,
    GateDecision,
    RoastState,
    SendEventIntent,
    SetSVIntent,
)
from llm_envelope.pipeline import run_mock_control
from llm_envelope.stub import LayaStub

__all__ = [
    'APPROVED_ABSOLUTE_MAX_C',
    'APPROVED_MAX_DELTA_SV_C',
    'APPROVED_MAX_ROR_C_PER_MIN',
    'APPROVED_SV_MIN_C',
    'EnvelopeConfig',
    'EnvelopeGate',
    'GateDecision',
    'LayaStub',
    'MapResult',
    'MockWriter',
    'RoastState',
    'SendEventIntent',
    'SetSVIntent',
    'map_proposal',
    'run_mock_control',
]
