
---

## TEST_1

- **Session ID:** test-call-patch-001
- **Started:** 2026-09-09 10:20:55

### Conversation & Events

- `[  0.002s]` 🔄 **Session init** — reason=`first_inbound_call_start`
- `[  0.002s]` 🌐 **Language switch** en-IN → hi-IN (conf=None)
- `[  0.003s]` 🌐 **Language switch** hi-IN → te-IN (conf=None)

### Summary — TEST_1

| Metric | Value |
|---|---|
| Duration | 0.004s |
| Disposition | completed |
| Turns | 0 |
| Interruptions | 0 |
| Session re-inits | 1 (✅ OK) |
| Language switches | 2 |
| Reconnects | 0 |
| Errors | 0 |
| Notes |  |


### Summary — TEST_1

| Metric | Value |
|---|---|
| Duration | 0.006s |
| Disposition | completed |
| Turns | 0 |
| Interruptions | 0 |
| Session re-inits | 1 (✅ OK) |
| Language switches | 2 |
| Reconnects | 0 |
| Errors | 0 |
| Notes |  |

- `[  0.007s]` 🔄 **Session init** — reason=`first_inbound_call_start`
- `[  0.009s]` 🔄 **Session init** — reason=`duplicate_call_start_attempt` 🚨 **UNEXPECTED MID-CALL RE-INIT — LIKELY BUG**

### Summary — TEST_1

| Metric | Value |
|---|---|
| Duration | 0.009s |
| Disposition | completed |
| Turns | 0 |
| Interruptions | 0 |
| Session re-inits | 3 (🚨 CHECK — expected exactly 1) |
| Language switches | 2 |
| Reconnects | 0 |
| Errors | 0 |
| Notes |  |

- `[  0.011s]` 🔄 **Session init** — reason=`first_inbound_call_start`
- `[  0.012s]` 🔌 **Reconnect** — transport=`websocket_telephony`, reason: websocket_packet_loss_reconnect

### Summary — TEST_1

| Metric | Value |
|---|---|
| Duration | 0.013s |
| Disposition | completed |
| Turns | 0 |
| Interruptions | 0 |
| Session re-inits | 4 (🚨 CHECK — expected exactly 1) |
| Language switches | 2 |
| Reconnects | 1 |
| Errors | 0 |
| Notes |  |

