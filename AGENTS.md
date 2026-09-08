# Project Instructions

- Try to minimise token usage so we do not use all available credits.
- When the user explicitly corrects a repeatable workflow or quality rule governed by a project-owned skill, update the applicable `SKILL.md` during the same task so the correction persists.
- Keep durable corrections narrowly scoped. Do not automatically modify system, third-party, unrelated, or non-writable skills, and do not encode one-off preferences as universal rules.

## Sub-agent model routing

When delegation is authorized and useful, pass an explicit model override based on task complexity:

- `gpt-5.6-luna` for menial, deterministic, low-risk work: file discovery, formatting, simple data extraction, mechanical edits, and straightforward tests.
- `gpt-5.6-terra` for ordinary implementation, investigation, and multi-step work that is not especially difficult or risky.
- `gpt-5.6-sol` for hard, ambiguous, security-sensitive, architectural, cross-cutting, or reasoning-heavy work.

When uncertain, use Terra; choose Sol when a mistake would be costly or the task needs substantial judgment. Keep delegation bounded and do not spawn an agent unless the user, these instructions, or an applicable skill authorizes it.
