#
# ABOUT
# Mock-only LLM roast-control envelope sidecar.
# Log sink for accepted intents. No serial and no Artisan calls.
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

"""Log sink that stands where a future Kaleido serial writer would sit.

``write`` records ``{intent, sv|event}`` and prints that payload. It does
not open a port.
"""

from __future__ import annotations

import json
from collections.abc import Callable

from llm_envelope.models import Intent


def _print_payload(line: str) -> None:
    print(line, flush=True)


class MockWriter:
    """In-memory log plus an optional print sink. Mock only."""

    def __init__(self, sink: Callable[[str], None] | None = None) -> None:
        self.records: list[dict[str, float | str]] = []
        self._sink: Callable[[str], None] = _print_payload if sink is None else sink

    def write(self, intent: Intent) -> None:
        """Append and emit one allowlisted payload. Caller must gate first."""
        payload = intent.payload()
        self.records.append(payload)
        self._sink(json.dumps(payload))
