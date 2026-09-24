#
# ABOUT
# Mock-only LLM roast-control envelope sidecar.
# Fail-closed EnvelopeGate over allowlisted intents. No machine I/O.
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

"""Fail-closed gate for ``set_SV`` and ``send_Event``.

Out-of-envelope commands are rejected. This gate does not clamp, and it
does not call Artisan or a serial port.
"""

from __future__ import annotations

from llm_envelope.models import (
    REASON_BT_ABOVE_MAX,
    REASON_DELTA_SV,
    REASON_ET_ABOVE_MAX,
    REASON_INCOMPLETE_STATE,
    REASON_MALFORMED_EVENT,
    REASON_OK,
    REASON_ROR,
    REASON_STATE_OUTSIDE,
    REASON_SV_ABOVE_MAX,
    REASON_SV_BELOW_MIN,
    REASON_SV_NOT_FINITE,
    REASON_UNKNOWN_INTENT,
    REASON_USB_FAULT,
    EnvelopeConfig,
    GateDecision,
    RoastState,
    SendEventIntent,
    SetSVIntent,
    finite_float,
    is_allowed_event,
)


class EnvelopeGate:
    """Allow a command only when the explicit envelope and the supplied state agree."""

    def __init__(self, config: EnvelopeConfig | None = None) -> None:
        self.config: EnvelopeConfig = config if config is not None else EnvelopeConfig()

    def evaluate(self, intent: object, state: object) -> GateDecision:
        """Return a decision. Unknown or malformed input is rejected."""
        if isinstance(intent, SetSVIntent):
            return self._evaluate_set_sv(intent, state)
        if isinstance(intent, SendEventIntent):
            return self._evaluate_send_event(intent, state)
        return GateDecision(allowed=False, reason=REASON_UNKNOWN_INTENT, intent=None)

    def _evaluate_set_sv(self, intent: SetSVIntent, state: object) -> GateDecision:
        blocked = self._interlock(state)
        if blocked is not None or not isinstance(state, RoastState):
            return GateDecision(
                allowed=False,
                reason=blocked if blocked is not None else REASON_INCOMPLETE_STATE,
                intent=intent,
            )
        sv = finite_float(intent.sv)
        if sv is None:
            return GateDecision(allowed=False, reason=REASON_SV_NOT_FINITE, intent=intent)
        if sv < self.config.sv_min_c:
            return GateDecision(allowed=False, reason=REASON_SV_BELOW_MIN, intent=intent)
        if sv > self.config.absolute_max_c:
            return GateDecision(allowed=False, reason=REASON_SV_ABOVE_MAX, intent=intent)
        sensor = self._sensor_block(state)
        if sensor is not None:
            return GateDecision(allowed=False, reason=sensor, intent=intent)
        current = finite_float(state.sv_c)
        if current is None:
            return GateDecision(allowed=False, reason=REASON_INCOMPLETE_STATE, intent=intent)
        if current < self.config.sv_min_c or current > self.config.absolute_max_c:
            return GateDecision(allowed=False, reason=REASON_STATE_OUTSIDE, intent=intent)
        if abs(sv - current) > self.config.max_delta_sv_c:
            return GateDecision(allowed=False, reason=REASON_DELTA_SV, intent=intent)
        return GateDecision(allowed=True, reason=REASON_OK, intent=SetSVIntent(sv=sv))

    def _evaluate_send_event(self, intent: SendEventIntent, state: object) -> GateDecision:
        blocked = self._interlock(state)
        if blocked is not None or not isinstance(state, RoastState):
            return GateDecision(
                allowed=False,
                reason=blocked if blocked is not None else REASON_INCOMPLETE_STATE,
                intent=intent,
            )
        if not is_allowed_event(intent.event):
            return GateDecision(allowed=False, reason=REASON_MALFORMED_EVENT, intent=intent)
        sensor = self._sensor_block(state)
        if sensor is not None:
            return GateDecision(allowed=False, reason=sensor, intent=intent)
        return GateDecision(
            allowed=True,
            reason=REASON_OK,
            intent=SendEventIntent(event=intent.event),
        )

    def _interlock(self, state: object) -> str | None:
        """USB fault rejects every write. A missing snapshot rejects too."""
        if not isinstance(state, RoastState):
            return REASON_INCOMPLETE_STATE
        if not isinstance(state.usb_fault, bool) or state.usb_fault:
            return REASON_USB_FAULT
        return None

    def _sensor_block(self, state: RoastState) -> str | None:
        """Reject when BT, ET, or RoR is missing or outside the envelope."""
        bt = finite_float(state.bt_c)
        if bt is None:
            return REASON_INCOMPLETE_STATE
        if bt > self.config.absolute_max_c:
            return REASON_BT_ABOVE_MAX
        et = finite_float(state.et_c)
        if et is None:
            return REASON_INCOMPLETE_STATE
        if et > self.config.absolute_max_c:
            return REASON_ET_ABOVE_MAX
        ror = finite_float(state.ror_c_per_min)
        if ror is None:
            return REASON_INCOMPLETE_STATE
        if ror > self.config.max_ror_c_per_min:
            return REASON_ROR
        return None
