#
# ABOUT
# Mock-only LLM roast-control envelope sidecar.
# Untrusted proposal stub. No model client and no machine I/O.
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

"""Stand-in for an untrusted laya or LLM proposer.

The stub returns raw dictionaries. Callers must pass them through
``map_proposal`` and ``EnvelopeGate``. The stub has no writer and no port.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


class LayaStub:
    """Scripted proposal source. Output is untrusted by design."""

    def __init__(self, script: Sequence[Mapping[str, Any]]) -> None:
        self._script: list[dict[str, Any]] = [dict(item) for item in script]

    def propose_all(self) -> list[dict[str, Any]]:
        """Return a fresh copy of the scripted proposals."""
        return [dict(item) for item in self._script]
