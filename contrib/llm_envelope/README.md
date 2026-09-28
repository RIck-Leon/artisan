# LLM envelope sidecar (mock only)

Fail-closed roast-control gate for this Artisan fork. It sits beside the
application as a sidecar. It does not import Artisan, Kaleido, or pyserial.

```
curve/state → laya/stub → intent_mapper → EnvelopeGate → mock log
```

The product path continues `EnvelopeGate → Artisan Kaleido Serial → machine`.
That hop is **mock-only / real serial NO-GO** in this slice. Accepted intents
are printed as `{intent, sv|event}` and stored on `MockWriter`. Nothing is
sent to a roaster.

`RoastState` in the demo and in tests is **injected mock telemetry**. It is
not read from a machine, and it is not a live write path.

## Envelope defaults

`EnvelopeConfig` is explicit. It is not inferred from roast profiles.
The gate rejects a config looser than these approved ceilings:

| Limit | Approved default |
| --- | --- |
| SV minimum | 0°C |
| BT, ET, and SV absolute maximum | 250°C |
| Absolute SV change per command | 5°C |
| RoR ceiling | 30°C/min, rejected (not clamped) |
| `usb_fault` | reject every write |

Allowlisted intents are `set_SV` and `send_Event`. Any other name, a malformed
payload, or a missing sensor field is rejected.

Profile fields `externalprogram`, `alarmaction`, and `externaloutprogram` are
ignored on this path and are never executed.

## Run the tests

From this directory:

```bash
python -m pytest
```

From the repository root:

```bash
python -m pytest contrib/llm_envelope/tests
```

## Run the mock demo

From this directory:

```bash
python -m llm_envelope.demo
```

Stdout is only allowlisted intent payloads. A one-line mock-only summary goes
to stderr. There is no serial output.
