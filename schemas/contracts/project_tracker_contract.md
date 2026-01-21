# Agent Contract: Project Tracker & Narrative

## Input
### `messages[]`
Each message item:
- `source` (email/slack/meeting)
- `timestamp`
- `author`
- `text`
- `thread_or_meeting_id`

Optional:
- `attachments[]` (links/filenames)

## Output
### `project_state`
- `decisions[]` (date, decision, rationale, participants)
- `action_items[]` (owner, task, due_date, status, source_link)
- `blockers[]` (blocking_item, owner, since, next_prompt)
- `open_questions[]`

### `narrative`
A concise status narrative (1–2 paragraphs max).

### `followups`
Suggested follow-up prompts/messages with recipients + context.
