# Progress: go-agent-egress-proxy

## Done

- [x] Onboarded the original Squid proxy setup note into `tasks/go-agent-egress-proxy/task.md`
- [x] Normalized naming to match this repository:
  - image: `go-agent`
  - proxy container: `go-agent-egress-proxy`
  - agent internal network: `go-agent-internal-net`
  - proxy upstream network: `go-agent-upstream-net`
  - Makefile targets: `networks`, `egress-proxy-*`, `egress-init`, `egress-verify`
- [x] Added a dedicated progress tracker for this task
- [x] Updated `README.md` to point to the task and progress files
- [x] Added `squid.conf` with a CONNECT allowlist for approved domains
- [x] Added Makefile targets for egress network/proxy lifecycle management
- [x] Updated `bin/run-shell` to join `go-agent-internal-net`
- [x] Injected proxy-related environment variables into the agent session container
- [x] Added a verification target for allowed vs denied destinations
- [x] Updated the README with operational egress proxy usage
- [x] Configured the agent internal network as internal-only and attached the proxy to a second outbound-capable network
- [x] Kept the proxy internal-only; host port `3128` is not published

## Remaining

- [ ] Expand the Squid allowlist if additional upstream domains are required in practice

## Notes

- The current launcher starts an unnamed ephemeral agent session container via `docker run --rm -it`; the task therefore uses the term **agent session container** rather than introducing a new fixed runtime container name.
- Direct Internet bypass is prevented by putting the agent session on the internal-only `go-agent-internal-net` and attaching the proxy to `go-agent-upstream-net` for outbound access.
