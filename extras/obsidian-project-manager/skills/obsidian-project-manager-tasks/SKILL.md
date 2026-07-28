---
name: obsidian-project-manager-tasks
description: Create, inspect, and update Markdown task files for the Obsidian Project Manager plugin. Use when the user asks to manage stories, tickets, tasks, kanban/status work, or project dashboard data stored as Project Manager `.md` files with YAML frontmatter in an Obsidian vault.
---

# Obsidian Project Manager Tasks

Use this skill for filesystem-backed task tracking with the Obsidian Project Manager plugin.

Before relying on plugin details, read [references/sources.md](references/sources.md) when current source links or supported fields matter.

## Core Model

Project Manager stores projects and tasks as Markdown files with YAML frontmatter. The vault is the database.

Recognize task files by:

```yaml
pm-task: true
```

Recognize project files by:

```yaml
pm-project: true
```

Task body content is Markdown and should remain useful to humans and agents.

## Default Fields

Prefer these frontmatter fields unless the local vault already uses a different convention:

```yaml
pm-task: true
projectId: "project-id"
parentId: null
id: "task-id"
title: "Task title"
type: task
status: "todo"
priority: medium
progress: 0
assignees: []
tags: []
subtaskIds: []
dependencies: []
```

Common statuses from the plugin docs:

```text
todo
in-progress
blocked
review
done
cancelled
```

Common priorities:

```text
critical
high
medium
low
```

If existing task files use different status or priority spelling, follow the existing vault convention exactly.

## Workflow

1. Locate the vault/project folder from the user's request or local context.
2. Inspect existing task files before creating or changing tasks.
3. Preserve all existing frontmatter keys when editing a task.
4. Update only the fields needed for the requested change.
5. Add notes in Markdown body sections such as `## Work Log`, `## Notes`, or `## Acceptance Criteria`.
6. Avoid deleting or bulk-moving task files unless explicitly asked.

## Creating Tasks

Use `scripts/create_task.py` when creating a new task file.

Example:

```sh
python3 <skill>/scripts/create_task.py \
  --dir /path/to/vault/Projects/MyProject/tasks \
  --project-id e1yy2o2umro3958k \
  --title "Implement retry handling" \
  --status todo \
  --priority high \
  --assignee agent-a \
  --tag story \
  --body /tmp/task-body.md
```

The script creates a stable slug filename, writes Project Manager frontmatter, and refuses to overwrite existing files.

## Updating Tasks

For small edits, patch the Markdown file directly:

- Keep the YAML frontmatter at the top of the file.
- Preserve unknown keys.
- Quote strings containing punctuation.
- Use lists for `assignees`, `tags`, and `dependencies`.
- Keep the Markdown body below the closing `---`.

For status changes, also add a short work-log entry when helpful:

```md
## Work Log

### 2026-07-16

Status: blocked

Blocked on missing test fixture details.
```

## Safety

- Do not invent plugin-only IDs unless the local files already show the expected format.
- Do not rewrite all frontmatter just to change one field.
- Do not remove custom fields; Project Manager supports custom fields.
- Do not assume real-time collaboration. Treat Git or filesystem sync conflicts as normal Markdown conflicts.
