# Sources

Primary references for the Obsidian Project Manager plugin:

- Community plugin page: https://community.obsidian.md/plugins/project-manager
- Project website: https://stepankropachev.github.io/obsidian-pm-site/

Facts used by this skill:

- Project Manager stores projects and tasks as plain Markdown files with YAML frontmatter.
- The plugin provides Table, Gantt, and Kanban views over the same file-backed data.
- The documented data format uses `pm-task: true` for task files.
- Project files can be opened as projects with `pm-project: true`.
- Documented task fields include title, description body, type, status, priority, start/due dates, progress, time estimates/logs, assignees, tags, subtasks, dependencies, recurrence, and custom fields.
- Documented sample task frontmatter:

```yaml
pm-task: true
title: "Ship v1.0"
status: in-progress
priority: high
due: "2026-04-01"
progress: 60
assignees: ["alice", "bob"]
tags: ["launch"]
dependencies: ["task-abc123"]
```

Verify against the links above if behavior or field names appear to have changed.
