# Repository guidance

When adding, changing, or removing an extra, or updating the agent-facing extras
references, read and follow
[the maintain-extras skill](.agents/skills/maintain-extras/SKILL.md).

Keep extra-specific implementation and detailed documentation under `extras/`.
Top-level integration should stay generic, apart from the brief agent context
needed to discover and connect to extras.

## Cross-unit coordination

For gateway integration work, read
[/Users/jbelo/personal/workspace/sc-agent-gateway/progress/EXCHANGE.md](/Users/jbelo/personal/workspace/sc-agent-gateway/progress/EXCHANGE.md)
when starting or resuming. Append replies there, preserving earlier entries.
Name the sending unit, entry answered, exact contract commit, findings or outcome,
and next action. Keep the work-item status aligned with the next action.
Review findings are not owner acceptance: agreement requires explicit acceptance
by both unit owners of the same revision. File updates do not notify another agent.
