# Story setup handoff

Host-side Git setup for workspaces prepared by `meta-shell`. No service, credentials
in containers, image rebuild, or new network permission is needed. Python 3.9+ and
host Git are required. Existing host setup skills continue to support host-only use;
the installed agent skills implement the container handoff.

Install with `make install`; refresh skills with `make install-agent-context`.
The authoritative container skills and host command are maintained in this extra.

The agent supplies the exact host command, including the required `apply` action
and the host request path. It does not search for the host executable inside the
container. `window` is reserved for completed-Git window retries or migrations.
After verifying the completed setup, meta supplies a tailored, ready-to-paste Pi
prompt for the story workspace. Pi first investigates read-only, briefs the operator
on its understanding and proposed approach, and waits for explicit go-ahead before
implementation or full review. Meta does not launch Pi or start the story work.

The agent prepares the template/brief and a JSON request inside an existing
`~/exoscale/stories/<workspace>/`. Review the request, then run on the host:

```sh
story-setup apply ~/exoscale/stories/sc-123-example/setup.json
```

Use `--workspace-root PATH` for another root. Repository names are direct children
of that root. The request cannot supply credentials, URLs, commands, or Git options.
The host's configured `origin` and authentication are used. Repositories and their
Git configuration must be trusted host checkouts; do not grant agents write access
to their Git metadata. Run against a quiescent story directory: path validation is
not a sandbox against a concurrently malicious host process changing directories.

```json
{
  "version": 1,
  "worktrees": [{
    "repository": "kms",
    "destination": "stories/sc-123-example/branch",
    "branch": "jbelo/sc-123/example",
    "base": "main",
    "mode": "new"
  }]
}
```

`new` requires the branch absent locally and on origin; it starts at `origin/base`
and has no upstream. `existing` requires `branch == base` and an origin branch;
an existing local branch must match. Its upstream becomes `origin/base`.
Optional `expected_commit` pins the fetched commit (use PR `head_sha` for reviews).
Before handing off a review request, the agent checks registered worktrees for the
PR branch. If occupied, it reports the old location/commit and asks whether to make
a fresh review branch or arrange authorized reuse. A fresh review uses `new`, a
unique local `review/rv-...` branch, the original PR branch as `base`, and the PR
head as `expected_commit`; it leaves the old worktree unchanged and has no upstream.
Reuse is outside this command's absent-destination contract. Host collision checks
remain the final safeguard against changes after agent preflight.

Local-only branches, forks, arbitrary refspecs, and alternate existing-branch names
are not supported in this first version; use the host setup skill for those cases.

Destinations must be absent siblings of the request, under `stories/<workspace>`.
The entire request is validated before fetch; all fetched branches are checked
before any worktree creation. Fetch/prune updates remote refs even if later checks
fail. No push, reset, merge, branch deletion or automatic rollback occurs.

`setup.json.result.json` is created exclusively before fetch. It contains the request
SHA-256, state, created worktrees, commits and upstreams. Existing receipts prevent
replay. On failure, inspect the receipt and existing worktrees; do not delete the
receipt and blindly retry. Resolve partial work explicitly, using a new request
only for work that remains. Briefs and templates are never overwritten by this tool.

Git forward pointers are relative; host backlinks are retained. Host worktree
management remains supported. Container Git reads are verified in disposable tests;
container worktree creation/repair/removal is not supported. Native relative-worktree
extensions are not enabled, preserving compatibility with agent Git 2.48.

Tests: `python3 -m unittest discover -s extras/story-setup/tests`.

## Host tmux windows

New agent requests include `"tmux": {"session": "main", "window": "sc-example"}`
for implementation, or session `review` and window `rv-example` for reviews.
The existing host session and absent window name are checked before fetch or Git
changes. After Git verification the command creates a detached host tmux window
at the story directory running `/bin/bash`; it does not launch story-shell.
Session/window/pane IDs and the working directory are recorded in the receipt.
The agent must not create a duplicate window in its container tmux server.
Requests without tmux remain valid Git-only requests for compatibility.

If tmux fails after Git succeeds, the receipt has `status: tmux_failed` and
`git_status: complete`. Fix the host session/window issue, then run:

```sh
story-setup window ~/exoscale/stories/sc-123-example/setup.json
```

This locks the receipt, validates the request hash and existing worktrees, and
retries only window creation. It never fetches or adds worktrees. A receipt already
recording a successful window is refused; inspect the recorded ID instead of
creating a duplicate. Existing request/receipt pairs remain intact. If interrupted
between tmux creation and receipt persistence, inspect host windows before retrying;
an occupied window is never automatically reused or removed.

### Add a window to an older completed setup

Do not edit a completed request to add tmux: its receipt pins the exact request hash.
For a Git-only request (including older receipts without git_status), run:

```sh
story-setup window ~/exoscale/stories/rv-123-example/setup-review.json \
  --session review --window rv-example
```

The command requires a completed Git receipt, checks the unchanged request hash and
worktree branches/commits, and records the operator-supplied settings in the receipt's
`window_request`. It leaves the request bytes unchanged and does not fetch or create
worktrees. Both flags are required together; they cannot override settings in a
request or prior migration. On a window failure, the settings remain in the receipt;
retry `story-setup window` with the same request and no flags. A successful recorded
window cannot be duplicated. Existing occupied windows are not adopted automatically.

## Portable host profiles

Select `"extras": ["story-setup"]` in a Fenced host profile. The extra-owned
`host-profile.json` declares host tools and agent skills; profile planning and
initialization check these before mutating Docker resources. No service, Git fetch
or tmux window is started by initialization. The reviewed `story-setup apply`
command remains an explicit host action, and the requested tmux session must exist.
Credentials and optional private templates require separate operator enrollment.
The handoff is tested with local Git fixtures on Ubuntu 24.04 ARM64 and Ubuntu
26.04 AMD64. Ubuntu 26.04 ARM64 revalidation and external authenticated fetch
remain separate validation requirements.

## Profile-session host paths

`fenced meta` and `fenced story` expose `FENCED_HOST_WORKSPACE` and
`FENCED_HOST_CHECKOUT` as path metadata inside the container. Setup skills use
these values to produce a host command via the selected checkout's
`fenced exec story-setup`, always supplying `--workspace-root`. This does not mount
the host checkout or provide host credentials. Legacy launchers supply the workspace
mapping; when checkout metadata is absent, the skill asks for the host command
environment instead of assuming ~/.local/bin or ~/exoscale.

Select the private template with `fenced template /host/path/to/memty` before
starting a new profile session. See [Memty](../memty/README.md) for the read-only
mount and host-specific paths. No template copy into the agent home is required.
