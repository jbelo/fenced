# Task Conventions

A task groups an objective, its supporting context, execution records, and any repository worktrees. Use this convention alongside `COLLABORATION.md`, which defines the foundational concepts, responsibilities, and authority boundaries. It does not change ownership or approval authority.

## Names and types

Use a short, descriptive slug that identifies the work, not its executor or team.

| Folder | Type | Brief | Completion means |
|---|---|---|---|
| `sc-<short-slug>` | Story Card | `brief/STORY.md` | The change meets its acceptance criteria and has been verified. |
| `rs-<short-slug>` | Research | `brief/RESEARCH.md` | The research questions are answered, with evidence, limitations, and recommendations or unresolved questions recorded. |
| `rv-<short-slug>` | Review | `brief/REVIEW.md` | The defined scope has been examined and findings, severity, and follow-up actions are recorded. |

Research and review may use worktrees when useful. Research does not itself authorize production implementation; completing a review does not imply that every finding has been fixed.

## Folder layout

```text
sc-example/                         # or rs-example / rv-example
├── brief/
│   ├── STORY.md                    # RESEARCH.md or REVIEW.md for other types
│   └── attachments/                # optional supporting specification material
├── reference/                     # supporting context, with source and revision
├── progress/
│   ├── STATUS.md                   # current task state
│   ├── LOG.md                      # significant progress and decisions
│   ├── HANDOVER.md                 # checkpoint for resuming work
│   └── tickets/                    # optional; one file per ticket
├── guidance/                      # conventions, checklists, instructions
├── branch/                        # optional main repository Git worktree
└── branch-<repo>/                  # optional additional repository worktree(s)
```

Create folders and files as needed; empty placeholders are unnecessary. Keep durable briefs and progress outside the disposable worktrees. Task records may sit beside the unit's working checkouts or in another established location; link that location from unit records rather than reorganizing the workspace.

## What is authoritative

- **Objective:** The brief defines the goal, scope, acceptance criteria or research/review questions, constraints, and relevant approved decisions. Record material scope changes explicitly with the required authorization.
- **Context:** `reference/` supplies evidence and background. Identify each source and its revision, version, or retrieval date. Copies do not supersede the authoritative source or an approved contract; distinguish facts, assumptions, and proposals.
- **Status:** `progress/STATUS.md` is authoritative for the overall task. Each ticket's own record is authoritative for that ticket's status; summaries should link to it rather than maintain competing status records. Logs record history, and handovers explain how to resume.
- **Instructions:** `guidance/` holds applicable conventions and checklists, or links to them. It applies within the authority established by `COLLABORATION.md`, unit instructions, and repository instructions.

If a ticket is already maintained for a unit in its lasting `tickets/` directory or an external tracker, designate that record as authoritative and link it from `progress/tickets/`. Do not create a second independent ticket record.

## Start with the minimum

Create the typed folder, its brief, and `progress/STATUS.md`. Record the objective, completion criteria, responsible unit and owner, executor, current state, and next action. Link the originating request and any required approvals. Add context, guidance, worktrees, logs, and a handover when they become useful.

Use the workspace's existing lifecycle, such as `BACKLOG → READY → IN_PROGRESS → IN_REVIEW → DONE`, with `CANCELLED` where needed. Record blockers separately and precisely.

## Ownership, permissions, and dependencies

Folder names, assignments, and access to a worktree do not grant ownership or permission to modify another unit. Work within the assigned scope and technical permissions. Apply the authority boundaries in `COLLABORATION.md` to responsibility changes, shared contracts, implementation assignments, and cross-unit handoffs. Keep secrets and live credentials out of task records and Git.

Decompose into tickets only when separate deliverables, owners, or dependencies make execution clearer. Each ticket needs a goal, completion criteria, owner/executor, status, and result. Identify dependencies by the exact decision, artifact revision, or verified capability required and the activity it blocks. Unrelated work may proceed independently. Completing all tickets does not close the parent task until its own completion criteria are met.

## Checkpoint and resume

At a meaningful checkpoint, before handoff, or before stopping substantial work:

- Update overall status and affected ticket records.
- Add significant results and decisions to `LOG.md`; avoid a transcript of routine activity.
- Update `HANDOVER.md` with completed and remaining work, repository/worktree locations and saved commits, verification results, blockers, pending decisions, and the next action.

On resumption, read applicable instructions and guidance, the brief, current status and tickets, and the handover. Check relevant reference and contract revisions and the actual repository state before continuing. Chat history should not be necessary to resume.

## Verify and clean up

Verify against the brief's completion criteria. Story Cards need evidence for the delivered behavior; Research needs traceable findings and stated uncertainty; Reviews need scope coverage and actionable findings. Record the relevant revisions, checks, results, and limitations. Where cross-unit integration is required, use the assigned test responsibilities and evidence from the real provider to verify the agreed contract.

Before marking the task done, save its outputs and evidence, identify remaining follow-up work, and update authoritative status records. Preserve code in commits and record where it is available before removing worktrees. Confirm that needed changes and files are saved, then clean up temporary worktrees and artifacts using the established process. Retain the brief and durable progress records; move reusable knowledge to its established unit or shared location and link it.

Keep records proportional to the work: one clear brief and a small, current checkpoint are often enough.
