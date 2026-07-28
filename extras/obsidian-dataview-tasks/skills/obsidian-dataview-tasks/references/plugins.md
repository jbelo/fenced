# Dataview and Tasks Plugin Notes

Sources:

- Dataview community plugin page: https://community.obsidian.md/plugins/dataview
- Dataview metadata docs: https://blacksmithgu.github.io/obsidian-dataview/annotation/add-metadata/
- Dataview task/list metadata docs: https://blacksmithgu.github.io/obsidian-dataview/annotation/metadata-tasks/
- Tasks community plugin page: https://community.obsidian.md/plugins/obsidian-tasks-plugin
- Tasks user guide filters: https://publish.obsidian.md/tasks/Queries/Filters
- Tasks user guide examples: https://publish.obsidian.md/tasks/Queries/Examples
- Tasks user guide grouping: https://publish.obsidian.md/tasks/Queries/Grouping

## Dataview

Dataview indexes Markdown files in an Obsidian vault and can query:

- YAML frontmatter at the top of notes.
- Inline fields using `Key:: Value` or bracketed inline fields like `[key:: value]`.
- Markdown tasks/list items and their metadata.

Useful Dataview query types:

- `TABLE` for ticket dashboards.
- `LIST` for simple note lists.
- `TASK` for Dataview-native task lists.
- `dataviewjs` only when DQL is not enough.

Dataview frontmatter must be at the very top of the file between `---` delimiters.

## Tasks

Tasks tracks Markdown checkbox items across a vault and renders query blocks.

Common filters:

```text
not done
done
tag includes #task
path includes tickets
description includes retry
due before tomorrow
```

Filter lines are ANDed by default. Boolean operators such as `AND`, `OR`, and `AND NOT` can be used with parenthesized filters.

Common grouping and sorting:

```text
group by filename
group by folder
group by status
group by status.name
sort by due
sort by description
```

The plugin supports custom statuses. For portable Markdown, use standard checkbox states unless the vault already has configured custom statuses:

```md
- [ ] Todo
- [x] Done
```

## Combined Pattern

Use Dataview for ticket files and Tasks for action items:

- Frontmatter `status` represents the ticket state.
- Checkbox item tags represent action-item filters.
- Dashboard notes combine Dataview tables and Tasks blocks.
