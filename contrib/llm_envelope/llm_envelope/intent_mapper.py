#
# ABOUT
# Mock-only LLM roast-control envelope sidecar.
# Fail-closed mapper from untrusted proposals to allowlisted intents.
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

"""Map an untrusted stub or laya-like proposal into one allowlisted intent.

Anything unknown, ambiguous, or malformed is rejected. Profile execution
fields are dropped and never become commands.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from llm_envelope.models import (
    IGNORED_PROFILE_FIELDS,
    REASON_MALFORMED,
    REASON_OK,
    REASON_UNKNOWN_INTENT,
    Intent,
    SendEventIntent,
    SetSVIntent,
    finite_float,
    is_allowed_event,
)

_ACTION_KEYS = frozenset({'intent', 'action'})
_SET_SV_ALIASES = frozenset({'set_sv', 'setsv'})
_SEND_EVENT_ALIASES = frozenset({'send_event', 'sendevent'})


@dataclass(frozen=True, slots=True)
class MapResult:
    """Mapper outcome. ``ok`` is true only for a fully parsed allowlisted intent."""

    ok: bool
    intent: Intent | None
    reason: str


def map_proposal(proposal: object) -> MapResult:
    """Parse one untrusted proposal. This function does not execute anything."""
    if not isinstance(proposal, Mapping):
        return MapResult(ok=False, intent=None, reason=REASON_MALFORMED)
    if any(not isinstance(key, str) for key in proposal):
        return MapResult(ok=False, intent=None, reason=REASON_MALFORMED)

    kept = {
        key: value
        for key, value in proposal.items()
        if key not in IGNORED_PROFILE_FIELDS
    }
    action_keys = _ACTION_KEYS.intersection(kept)
    if len(action_keys) != 1:
        return MapResult(ok=False, intent=None, reason=REASON_MALFORMED)
    action_key = next(iter(action_keys))
    raw_action = kept[action_key]
    if not isinstance(raw_action, str):
        return MapResult(ok=False, intent=None, reason=REASON_MALFORMED)
    canonical = _canonical_intent(raw_action)
    if canonical is None:
        return MapResult(ok=False, intent=None, reason=REASON_UNKNOWN_INTENT)

    fields = {key: value for key, value in kept.items() if key != action_key}
    if canonical == 'set_SV':
        return _map_set_sv(fields)
    return _map_send_event(fields)


def _canonical_intent(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    folded = raw.strip().lower().replace('-', '_')
    if folded in _SET_SV_ALIASES:
        return 'set_SV'
    if folded in _SEND_EVENT_ALIASES:
        return 'send_Event'
    return None


def _map_set_sv(fields: Mapping[str, object]) -> MapResult:
    if set(fields) != {'sv'}:
        return MapResult(ok=False, intent=None, reason=REASON_MALFORMED)
    sv = finite_float(fields['sv'])
    if sv is None:
        return MapResult(ok=False, intent=None, reason=REASON_MALFORMED)
    return MapResult(ok=True, intent=SetSVIntent(sv=sv), reason=REASON_OK)


def _map_send_event(fields: Mapping[str, object]) -> MapResult:
    if set(fields) != {'event'}:
        return MapResult(ok=False, intent=None, reason=REASON_MALFORMED)
    event = fields['event']
    if not is_allowed_event(event):
        return MapResult(ok=False, intent=None, reason=REASON_MALFORMED)
    assert isinstance(event, str)
    return MapResult(ok=True, intent=SendEventIntent(event=event), reason=REASON_OK)
