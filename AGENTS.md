# Repository guidance

When adding, changing, or removing an extra, or updating the agent-facing extras
references, read and follow
[the maintain-extras skill](.agents/skills/maintain-extras/SKILL.md).

Keep extra-specific implementation and detailed documentation under `extras/`.
Top-level integration should stay generic, apart from the brief agent context
needed to discover and connect to extras.
