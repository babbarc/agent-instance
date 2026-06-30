# reCAPTCHA Tool Call Budget

Each cron run gets ~150 tool calls total. Budget:
- **Cloudflare queue: ~12-20 calls** (5-8 poll cycles × 2 calls each = sleep + snapshot). The waiting room can take 2-5 minutes. Each poll burns 2 turns. Do NOT poll more than once per 15-30s.
- **Navigation + login: ~10 calls**
- **reCAPTCHA per round: ~8-12 calls** (screenshot + crop + Claude + click tiles + verify + check result)
- **Post-login appointment check: ~5 calls**

**Realistic total with 3-4 reCAPTCHA rounds:** 12 (Cloudflare) + 10 (nav) + 40-50 (captcha, 4 rounds × ~10-12) + 5 (check) = **~67-77 calls**. This leaves ~70-80 calls of headroom.

**Key budget drains to watch:**
- Cloudflare polling: every `sleep` + `browser_snapshot` pair is 2 turns. Don't poll more than once every 30s.
- reCAPTCHA retries: a failed round (`"Please try again"`) doubles per-round cost to ~16-24 calls (2 screenshots, 2 Claude calls, 2 click-and-verify cycles). Budget for at least 1 retry per 3 rounds.
- Claude CLI calls: ~5-8 turns each (including output parsing). This is the single biggest per-round cost.
- Recovering from challenge expiry: re-triggering the checkbox + waiting + new screenshot adds ~6-8 calls.

**When budget is tight:** (Cloudflare took >15 turns, or rounds keep failing):
1. Skip individual tile Claude analysis for subsequent rounds — pass the full bframe screenshot instead of individual tiles
2. Use single-word Claude prompts rather than verbose descriptions
3. If 2+ rounds already failed and budget is below 40 remaining, cut losses and report "reCAPTCHA unsolved"
