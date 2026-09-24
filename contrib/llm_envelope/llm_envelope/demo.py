#
# ABOUT
# Mock-only LLM roast-control envelope sidecar.
# Demo that prints allowlisted intent payloads. No serial writes.
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

"""Print the mock control loop.

Stdout is only allowlisted payloads. The temperatures below are an injected
mock snapshot for the demo, not a reading from a roaster.
"""

from __future__ import annotations

import sys

from llm_envelope.mock_writer import MockWriter
from llm_envelope.models import RoastState
from llm_envelope.pipeline import run_mock_control
from llm_envelope.stub import LayaStub

# Injected mock telemetry. Not read from Artisan or a machine.
DEMO_MOCK_STATE = RoastState(
    bt_c=160.0,
    et_c=190.0,
    sv_c=155.0,
    ror_c_per_min=12.0,
    usb_fault=False,
)

# Untrusted script. The gate keeps the two in-envelope commands.
_SCRIPT: list[dict[str, object]] = [
    {'action': 'set_SV', 'sv': 158.0},
    {'action': 'send_Event', 'event': 'CHARGE'},
    {'action': 'set_SV', 'sv': 400.0},
    {'action': 'set_SV', 'sv': 170.0},
    {'intent': 'set_heater'},
    {
        'externalprogram': 'test.py',
        'alarmaction': [1],
        'externaloutprogram': 'out.py',
    },
]


def main() -> None:
    """Run stub → mapper → gate → mock log. Stdout is allowlisted payloads only."""
    writer = MockWriter()
    decisions = run_mock_control(
        LayaStub(_SCRIPT).propose_all(),
        DEMO_MOCK_STATE,
        writer=writer,
    )
    rejected = sum(1 for decision in decisions if not decision.allowed)
    print(
        f'mock-only: {len(writer.records)} allowed, {rejected} rejected; '
        'real Kaleido serial writes are NO-GO',
        file=sys.stderr,
    )


if __name__ == '__main__':
    main()
