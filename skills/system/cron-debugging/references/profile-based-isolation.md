# Profile-Based Isolation for Cron Workers

Use when routine cron jobs need lower reasoning_effort than interactive sessions.

## Setup Steps

1. Create profile:
```bash
hermes profile create cron-workers --no-skills
rm /opt/data/profiles/cron-workers/SOUL.md
```

2. Create profile `config.yaml`:
```yaml
model:
  provider: deepseek
  default: deepseek-v4-flash
  base_url: https://api.deepseek.com
agent:
  reasoning_effort: medium
```

3. Copy API key:
```bash
grep '^DEEPSEEK_API_KEY=' /opt/data/.env > /opt/data/profiles/cron-workers/.env
```

4. Create minimal SOUL.md:
```markdown
## Grounding Rules
- Base every statement EXCLUSIVELY on injected data sections.
- Do NOT merge context across unrelated data sections.
## Output Rules
- Address the user as "you". Never third person.
- If data doesn't contain the info, do not fabricate it.
```

5. Fix script paths: `$HERMES_HOME/scripts/` → `/opt/data/scripts/`

6. Update cron job: `cronjob action=update job_id=<id> profile=cron-workers`

## Choosing reasoning_effort

| Effort | TTFT | When |
|--------|------|------|
| none | Fastest | Pure data-passing, no analysis |
| low | 1-5s | Simple analysis without timeout risk |
| medium | 5-15s | Balanced choice — weekly checkins, meta-review |

## Verification
```bash
ls -t /opt/data/sessions/request_dump_*.json | head -1
```
Check that `thinking` and `reasoning_effort` are absent or at expected level.
