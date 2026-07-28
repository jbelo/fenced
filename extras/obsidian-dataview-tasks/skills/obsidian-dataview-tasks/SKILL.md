---
name: obsidian-dataview-tasks
description: Create, inspect, and maintain Markdown ticket/task files for Obsidian vaults using the Dataview and Tasks community plugins. Use when the user wants filesystem-backed tickets, story tasks, dashboards, status boards, or agent-readable work tracking without a database or web task service.
---

# Obsidian Dataview Tasks

Use this skill for Markdown-first work tracking in an Obsidian vault.

The model:

- one Markdown file per ticket/story/task
- YAML frontmatter for ticket-level metadata
- Markdown checkbox items for smaller action items
- Dataview dashboard notes for ticket-level tables
- Tasks query blocks for checkbox/action-item views

Read [references/plugins.md](references/plugins.md) when plugin behavior or query syntax matters.

## File Layout

Prefer this layout unless the vault already has a convention:

```text
tickets/
  Dashboard.md
  2026-07-17-short-title.md
  2026-07-17-other-title.md
```

For story-specific tracking:

```text
stories/
  <story-slug>/
    STORY.md
    tickets/
      Dashboard.md
      2026-07-17-short-title.md
```

## Ticket Format

Each ticket file should start with frontmatter:

```yaml
---
ticket: true
title: "Implement retry handling"
status: ready
assignee: agent-a
priority: high
story: sc-123
updated: 2026-07-17
tags:
  - task
---
```

Recommended statuses:

```text
ready
doing
blocked
review
done
cancelled
```

Recommended priorities:

```text
critical
high
medium
low
```

Use `status`, `assignee`, `priority`, `story`, and `updated` consistently; Dataview dashboards depend on these fields.

## Ticket Body

Use Markdown sections:

```md
# Implement retry handling

## Goal

## Acceptance Criteria

- [ ] Add bounded retries #task #ready
- [ ] Add retry exhaustion tests #task #ready

## Work Log

### 2026-07-17

Status: doing

Started implementation.
```

Use checkbox items for concrete action items. Add `#task` to every actionable checkbox if the vault uses the Tasks plugin global filter.

## Helper Scripts

Create a ticket:

```sh
python3 <skill>/scripts/create_ticket.py \
  --dir /path/to/vault/tickets \
  --title "Implement retry handling" \
  --status ready \
  --priority high \
  --assignee agent-a \
  --story sc-123 \
  --tag task
```

Create or refresh a dashboard note:

```sh
python3 <skill>/scripts/write_dashboard.py \
  --path /path/to/vault/tickets/Dashboard.md
```

## Dataview Dashboards

Use Dataview for ticket-level views over frontmatter. Example:

````md
```dataview
TABLE status, assignee, priority, updated
FROM ""
WHERE ticket = true AND status = "doing"
SORT updated DESC
```
````

For folders:

````md
```dataview
TABLE status, assignee, priority, updated
FROM "tickets"
WHERE ticket = true
SORT status ASC, priority DESC, updated DESC
```
````

## Tasks Query Blocks

Use Tasks for action-item-level views over Markdown checkboxes:

````md
```tasks
not done
tag includes #task
group by filename
sort by due
```
````

For blocked action items:

````md
```tasks
not done
tag includes #blocked
group by filename
```
````

## Updating Work

When starting work:

1. Set frontmatter `status: doing`.
2. Set or update `assignee`.
3. Set `updated` to today's date.
4. Add a `## Work Log` entry.

When blocked:

1. Set `status: blocked`.
2. Add a work-log entry explaining the blocker and needed input.
3. Add `#blocked` to relevant checkbox items when useful.

When complete:

1. Mark relevant checkbox tasks done.
2. Set `status: done`.
3. Set `updated` to today's date.
4. Add verification notes or test output summary.

## Safety

- Preserve existing frontmatter keys unless asked to remove them.
- Do not bulk-edit status across many files without showing the intended changes first.
- Do not overwrite dashboard customizations unless explicitly asked to regenerate the dashboard.
- Do not put secrets or credentials in ticket files.
