#
# ABOUT
# Mock-only LLM roast-control envelope sidecar.
# Shared types for the fail-closed intent gate. No machine I/O.
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

"""Types for the mock-only envelope sidecar.

``RoastState`` is always supplied by the caller. Tests and the demo inject
mock snapshots. This package does not read Artisan curves and does not
invent BT, ET, or elapsed time for a machine write.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Final, Literal

# Approved ceilings. EnvelopeConfig may tighten these and must not loosen them.
APPROVED_SV_MIN_C: Final[float] = 0.0
APPROVED_ABSOLUTE_MAX_C: Final[float] = 250.0
APPROVED_MAX_DELTA_SV_C: Final[float] = 5.0
APPROVED_MAX_ROR_C_PER_MIN: Final[float] = 30.0

ALLOWED_INTENTS: Final[frozenset[str]] = frozenset({'set_SV', 'send_Event'})

# Roast-profile fields this path must never execute.
IGNORED_PROFILE_FIELDS: Final[frozenset[str]] = frozenset({
    'externalprogram',
    'alarmaction',
    'externaloutprogram',
})

REASON_OK: Final[str] = 'ok'
REASON_USB_FAULT: Final[str] = 'usb_fault'
REASON_UNKNOWN_INTENT: Final[str] = 'unknown_intent'
REASON_MALFORMED: Final[str] = 'malformed_proposal'
REASON_SV_BELOW_MIN: Final[str] = 'sv_below_min'
REASON_SV_ABOVE_MAX: Final[str] = 'sv_above_max'
REASON_SV_NOT_FINITE: Final[str] = 'sv_not_finite'
REASON_DELTA_SV: Final[str] = 'delta_sv_exceeded'
REASON_BT_ABOVE_MAX: Final[str] = 'bt_above_max'
REASON_ET_ABOVE_MAX: Final[str] = 'et_above_max'
REASON_ROR: Final[str] = 'ror_above_ceiling'
REASON_INCOMPLETE_STATE: Final[str] = 'incomplete_state'
REASON_STATE_OUTSIDE: Final[str] = 'state_outside_envelope'
REASON_MALFORMED_EVENT: Final[str] = 'malformed_event'

_EVENT_RE: Final[re.Pattern[str]] = re.compile(r'^[A-Za-z][A-Za-z0-9_]{0,31}$')


def finite_float(value: object) -> float | None:
    """Return a finite float, or None. Booleans and strings are rejected."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    return number


def is_allowed_event(event: object) -> bool:
    """True for a plain event token. Profile-field names are not events."""
    if not isinstance(event, str):
        return False
    if event.lower() in IGNORED_PROFILE_FIELDS:
        return False
    return _EVENT_RE.fullmatch(event) is not None


@dataclass(frozen=True, slots=True)
class EnvelopeConfig:
    """Explicit temperature envelope. Not derived from a roast profile.

    Values may be stricter than the approved ceilings. Looser values raise
    ``ValueError`` so a caller cannot open the gate past the product limits.
    """

    sv_min_c: float = APPROVED_SV_MIN_C
    absolute_max_c: float = APPROVED_ABSOLUTE_MAX_C
    max_delta_sv_c: float = APPROVED_MAX_DELTA_SV_C
    max_ror_c_per_min: float = APPROVED_MAX_ROR_C_PER_MIN

    def __post_init__(self) -> None:
        if not math.isfinite(self.sv_min_c) or self.sv_min_c < APPROVED_SV_MIN_C:
            raise ValueError('sv_min_c must be finite and >= 0C')
        if (
            not math.isfinite(self.absolute_max_c)
            or self.absolute_max_c > APPROVED_ABSOLUTE_MAX_C
            or self.absolute_max_c < self.sv_min_c
        ):
            raise ValueError('absolute_max_c must stay within the approved 250C ceiling')
        if (
            not math.isfinite(self.max_delta_sv_c)
            or self.max_delta_sv_c <= 0
            or self.max_delta_sv_c > APPROVED_MAX_DELTA_SV_C
        ):
            raise ValueError('max_delta_sv_c must be within the approved 5C step')
        if (
            not math.isfinite(self.max_ror_c_per_min)
            or self.max_ror_c_per_min <= 0
            or self.max_ror_c_per_min > APPROVED_MAX_ROR_C_PER_MIN
        ):
            raise ValueError('max_ror_c_per_min must be within the approved 30C/min ceiling')


@dataclass(frozen=True, slots=True)
class RoastState:
    """Caller-supplied curve snapshot in degrees Celsius and °C/min.

    Inject this from tests or the mock demo. Do not treat it as live
    machine telemetry for a real write.
    """

    bt_c: float
    et_c: float
    sv_c: float
    ror_c_per_min: float
    usb_fault: bool


@dataclass(frozen=True, slots=True)
class SetSVIntent:
    """Allowlisted setpoint command. ``sv`` is degrees Celsius."""

    sv: float
    intent: Literal['set_SV'] = 'set_SV'

    def payload(self) -> dict[str, float | str]:
        return {'intent': self.intent, 'sv': self.sv}


@dataclass(frozen=True, slots=True)
class SendEventIntent:
    """Allowlisted event command. ``event`` is a constrained token."""

    event: str
    intent: Literal['send_Event'] = 'send_Event'

    def payload(self) -> dict[str, float | str]:
        return {'intent': self.intent, 'event': self.event}


Intent = SetSVIntent | SendEventIntent


@dataclass(frozen=True, slots=True)
class GateDecision:
    """Result of mapping or gating. ``allowed`` is false unless every check passed."""

    allowed: bool
    reason: str
    intent: Intent | None = None
