# Conversation Grouping for Windowed Delta Scripts

## Problem

Stateless windowed delta scripts (`whatsapp_delta.py --since 3h`) truncate history at a timestamp boundary. When Pallav replies to a message that fell in a previous window, the LLM sees an orphan — "Yes Thursday works!" with no antecedent. The reply is meaningless in isolation.

## Solution

Group delta output by conversation (JID) and include the last N pre-window messages per conversation as context. The LLM sees the full thread even when only the reply is in-window.

## Implementation (whatsapp_delta.py, June 2026)

### Architecture

Two per-JID buffers instead of one flat list:

```
context_buf = defaultdict(lambda: deque(maxlen=CONTEXT_DEPTH))  # pre-window: ring buffer
window_msgs = defaultdict(list)                                  # in-window: full list
```

**Pass 1 — all deltas:** Every line is processed, parsed, and resolved (sender name, contact ID, group filter, `fromMe` flag). Messages before the cutoff go into the ring buffer; messages after the cutoff go into the window list. Group chat messages (`@g.us`) are buffered only if they pass the Pallav-mention filter — but they are NOT added to the context buffer (groups are too noisy).

**fromMe handling:** When `fromMe=true` in the delta (outgoing message from Pallav), the sender resolves to "Pallav Vasa" (looked up by `id=pallav-vasa` in CONTACT_JID_MAP) instead of the conversation partner. The conversation JID is still used for grouping — the message appears under the correct conversation header. This was added in the same batch as the `emitOwnEvents` fix in the bridge.

**Pass 2 — grouped output:** For each JID that has window messages, emit:
1. `--- {Conversation Name} ---` header (resolved from JID map, with relationship suffix)
2. Context buffer messages (pre-window, if any)
3. Window messages

### Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Grouping key | `remoteJid` (the conversation JID) | One JID per conversation for 1:1 chats. Group chats already have the mention filter. |
| Context depth | 10 messages per JID | Enough to catch "Yo → Thursday → Drinks? → 5pm?" without inflating context. 20 would also work. |
| Group chat context | Excluded | Group chats are noisy — 100 messages where Pallav was mentioned once. The pre-window buffer would pull in unrelated chatter. The Pallav-mention filter only applies to the window, not the buffer. |
| Header | Resolved name from JID map | `_resolve_conversation_name(jid)` iterates CONTACT_JID_MAP to find the display name, with relationship suffix from PALLAV_RELATIONSHIPS. Falls back to last 6 digits of phone number for known-but-unresolved JIDs. Empty/unknown JIDs get no header (flat output). |
| Flat output fallback | No header when single JID, no context | Maintains backward compatibility. If there's only one conversation with no context to show, output is flat (same as before). |

### Output Formats

**Single conversation, no context (current behavior, no changes):**
```
Sun 15:06 | Christian Wietoska (friend) | id=christian-wietoska | Yo
Sun 15:06 | Christian Wietoska (friend) | id=christian-wietoska | Thursday
```

**Single conversation with context (Pallav's reply is in-window, the thread is pre-window):**
```
--- Christian Wietoska (friend) ---
Sun 15:06 | Christian Wietoska (friend) | id=christian-wietoska | Yo
Sun 15:06 | Christian Wietoska (friend) | id=christian-wietoska | Thursday
Sun 15:06 | Christian Wietoska (friend) | id=christian-wietoska | Drinks?
Sun 15:07 | Christian Wietoska (friend) | id=christian-wietoska | 5pm?
Sun 19:00 | Pallav Vasa | id=pallav-vasa | Yes Thursday works!
```
Note that Pallav's reply shows as `Pallav Vasa | id=pallav-vasa` — the `fromMe=true` handler resolves the sender to his own contact file rather than the conversation partner.

**Multiple conversations (each gets its own header group):**
```
--- Dilipkumar Prataprai Vasa (father) ---
Sun 06:59 | Dilipkumar Prataprai Vasa (father) | id=dilipkumar-vasa | Hi

--- Christian Wietoska (friend) ---
Sun 15:06 | Christian Wietoska (friend) | id=christian-wietoska | Yo
Sun 15:06 | Christian Wietoska (friend) | id=christian-wietoska | Thursday
```

### Edge Cases

- **Stale context bleeding:** Christian's 15:06 messages are pre-window at 18:00 and 20:00 (if Pallav replied at 19:00). At 22:00 with no new activity, the conversation drops from output entirely — no window messages → no group shown. Correct behavior.

- **Group chat in window + 1:1 in window:** Each gets its own section. Groups are always flat (no context buffer). 1:1 conversations show context if available.

- **Unknown JID:** If the JID isn't in CONTACT_JID_MAP, the header falls back to the last 6 digits of the phone number (e.g. `--- 644183 ---`). Empty JIDs get no header at all (flat output).

- **Rolling buffer at file boundary:** The ring buffer wraps naturally — old messages fall off when the deque reaches CONTEXT_DEPTH. No need to track file position.

### Applicability

This pattern applies to any stateless windowed delta script where:
1. Messages are grouped by conversation (JID, thread ID, channel)
2. Replies to earlier messages fall outside the window
3. The consuming LLM needs to see the full thread to understand the reply

gmail_delta.py doesn't need this because email threading is handled by Gmail's thread ID and subject-based grouping. WhatsApp's flat feed has no threading metadata — the conversation JID is the only grouping signal.

### Outgoing Message Capture — fromMe Messages

**Fixed 7 Jun 2026.** The bridge now captures outgoing messages (Pallav's own replies) in 1:1 conversations.

**Two changes required — both were made:**

1. **`baileys-watch.js:92`** — `emitOwnEvents: false` → `true`. When `false`, Baileys suppresses ALL `fromMe` events entirely (including WhatsApp echo-backs from Pallav's phone). The watcher never receives them.
2. **`baileys-watch.js:165`** — Removed the `if (msg.key?.fromMe) continue;` guard. Previously this was redundant with `emitOwnEvents: false`; after enabling own events, this guard must also be removed so outgoing messages are written to deltas.

**Sender resolution in `whatsapp_delta.py`:** When a delta entry has `fromMe=true`, the sender is resolved as "Pallav Vasa" (looked up by `id=pallav-vasa` in CONTACT_JID_MAP) rather than the conversation partner. The conversation grouping still uses `remoteJid` for grouping — the message appears under the conversation partner's header, attributed to Pallav:

```
--- Christian Wietoska (friend) ---
Sun 15:06 | Christian Wietoska (friend) | id=christian-wietoska | Yo
Sun 15:06 | Christian Wietoska (friend) | id=christian-wietoska | Thursday
Sun 15:06 | Christian Wietoska (friend) | id=christian-wietoska | Drinks?
Sun 15:07 | Christian Wietoska (friend) | id=christian-wietoska | 5pm?
Sun 19:00 | Pallav Vasa | id=pallav-vasa | Yes Thursday works!
```

**Why it was missed:** `emitOwnEvents: false` is the default recommendation in Baileys for bot-style setups (avoid echo loop when the bot sends its own messages). The WhatsApp setup uses self-chat mode (Pallav's own number, not a bot number), so `fromMe` echoes from Pallav's phone should be captured for heartbeat context. The guard at line 165 was a belt-and-suspenders that became the blocking factor after the config change.

**Credits:** Discovered via investigation of empty WhatsApp deltas while debugging the WhatsApp context pipeline (7 Jun 2026 session).

### Protocol Message Filter (follow-on fix, 7 Jun 2026)

After enabling `emitOwnEvents`, the Baileys session began receiving protocol sync messages from Pallav's phone JID (`447943644183@s.whatsapp.net`). These are `PEER_DATA_OPERATION_REQUEST_RESPONSE_MESSAGE / PLACEHOLDER_MESSAGE_RESEND` messages — internal WhatsApp traffic that dispatches message content between devices. They have no user-visible text and should never appear in the heartbeat's WhatsApp data.

**Filter added to `whatsapp_delta.py`:**
```python
# Skip protocol messages (PLACEHOLDER_MESSAGE_RESEND, etc.) —
# internal WhatsApp sync traffic with no user-visible content.
if not txt and "protocolMessage" in msg_obj:
    continue
```

**Also required:** A `messageContextInfo` skip in the text-extraction loop, and a `break` on first text match from `msg_obj` dict keys (the old code iterated all keys and the last non-empty value won — fragile).

**Symptoms of missing this filter:** The heartbeat's WhatsApp section showed rows like:
```
--- 644183 ---
Sun 09:45 | !!UNKNOWN:!! | 
```
Where `644183` is the last 6 digits of Pallav's phone JID, `!!UNKNOWN:!!` because the push_name was empty, and no text because protocol messages have none. These leaked into context on every heartbeat tick until the filter was added.
