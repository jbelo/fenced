# Task: Add Squid CONNECT Egress Proxy to the Go Agent Docker Harness

## Objective

Extend the existing Docker-based Go agent environment so outbound HTTPS traffic from the agent session is routed through a **Squid forward proxy using CONNECT**.

The goal is to enable controlled egress while preserving end-to-end TLS with upstream services such as OpenAI / ChatGPT Codex endpoints.

LiteLLM or any other OpenAI-compatible gateway is intentionally **out of scope** for this task.

The intended architecture is:

```text
go-agent session container
        |
        v
go-agent-egress-proxy
        |
        v
Internet / approved upstream endpoints
```

The proxy mediates TLS connections but does **not** terminate TLS.

---

## Existing Repository Context

This repository already provides:

- a Docker image build for the coding harness (`go-agent`)
- persistent Docker volumes (`agenthome`, `gomodcache`)
- installed launcher scripts (`story-shell`, `run-shell`)
- `Makefile` orchestration for build/install/bootstrap tasks
- a `run-shell` launcher that performs the `docker run`

This task adds controlled outbound networking to that setup.

---

## Naming Conventions for This Task

Use the following names consistently across documentation, scripts, config, and Makefile targets:

- Docker image: `go-agent`
- Agent session container: unnamed ephemeral container started by `bin/run-shell`
- Egress proxy container: `go-agent-egress-proxy`
- Agent internal network: `go-agent-internal-net`
- Proxy upstream network: `go-agent-upstream-net`
- Proxy address inside the internal network: `http://go-agent-egress-proxy:3128`
- Makefile target prefix: `egress-`

Suggested Makefile targets:

- `networks`
- `egress-proxy-up`
- `egress-proxy-down`
- `egress-proxy-logs`
- `egress-init`
- `egress-verify`

---

## Scope of Work

Add the following:

1. A dedicated internal Docker network for agent sessions plus a separate upstream network for the proxy
2. A Squid proxy container
3. A Squid configuration that only allows CONNECT to approved domains
4. Proxy environment variables injected into the agent session container
5. Makefile targets to create the network and manage the proxy
6. Validation steps or scripts
7. Documentation updates describing the egress model and usage

---

## Architecture

```text
+---------------------------+
| go-agent session          |
| ephemeral Docker          |
| container started by      |
| run-shell                 |
|                           |
| HTTPS requests            |
| via proxy env vars        |
+-------------+-------------+
              |
              v
+---------------------------+
| go-agent-egress-proxy     |
| Squid container           |
| CONNECT tunnel mediation  |
+-------------+-------------+
              |
              v
+---------------------------+
| Internet                  |
| approved domains only     |
| e.g. api.openai.com       |
| chatgpt.com               |
+---------------------------+
```

Key properties:

- Squid **tunnels TLS using CONNECT**
- Squid **does not decrypt traffic**
- Squid enforces **destination restrictions**
- The agent session should **not have direct Internet access** because it is attached only to the internal Docker network

---

## Docker Networks

Create two Docker networks:

- an internal network for agent-session-to-proxy traffic
- an upstream-capable network for proxy-to-Internet traffic

Example:

```sh
docker network create --internal go-agent-internal-net
docker network create go-agent-upstream-net
```

The agent session launched by `bin/run-shell` should join only the internal network.

The proxy container should attach to both networks under the name:

```text
go-agent-egress-proxy
```

The agent should reach the proxy at:

```text
go-agent-egress-proxy:3128
```

---

## Squid Proxy Container

Example run configuration:

```sh
docker run -d \
  --name go-agent-egress-proxy \
  --network go-agent-upstream-net \
  -v $(PWD)/squid.conf:/etc/squid/squid.conf:ro \
  ubuntu/squid:latest

docker network connect go-agent-internal-net go-agent-egress-proxy
```

Do **not** publish `3128` on the host for this repository. Keep the proxy internal to the Docker networks only.

---

## Squid Configuration

Provide a minimal configuration supporting CONNECT tunneling to approved domains only.

Illustrative example:

```conf
http_port 3128

acl SSL_ports port 443
acl Safe_ports port 443
acl CONNECT method CONNECT

acl allowed_openai dstdomain .openai.com
acl allowed_chatgpt dstdomain .chatgpt.com

http_access deny !Safe_ports
http_access deny CONNECT !SSL_ports
http_access allow CONNECT allowed_openai
http_access allow CONNECT allowed_chatgpt
http_access deny all

access_log stdio:/var/log/squid/access.log
```

Expected log entries during operation include lines such as:

```text
TCP_TUNNEL/200 CONNECT api.openai.com:443
```

The final implementation may need to refine ACL ordering or add explicit client-source restrictions.

---

## Agent Session Container Changes

Update `bin/run-shell` so the agent session joins the dedicated internal agent network and receives proxy-related environment variables.

Expected environment variables:

```text
HTTP_PROXY=http://go-agent-egress-proxy:3128
HTTPS_PROXY=http://go-agent-egress-proxy:3128
http_proxy=http://go-agent-egress-proxy:3128
https_proxy=http://go-agent-egress-proxy:3128
NODE_USE_ENV_PROXY=1
```

Consider whether `NO_PROXY` should also be set for localhost and internal-only addresses.

Example `docker run` shape:

```sh
docker run --rm -it \
  --network go-agent-internal-net \
  -e HTTP_PROXY=http://go-agent-egress-proxy:3128 \
  -e HTTPS_PROXY=http://go-agent-egress-proxy:3128 \
  -e http_proxy=http://go-agent-egress-proxy:3128 \
  -e https_proxy=http://go-agent-egress-proxy:3128 \
  -e NODE_USE_ENV_PROXY=1 \
  go-agent bash
```

This task should preserve the current filesystem isolation and launcher behavior.

---

## Makefile Changes

Add egress-related targets using the `egress-` prefix.

Suggested targets:

### Create network

```make
networks:
	docker network create --internal go-agent-internal-net || true
	docker network create go-agent-upstream-net || true
```

### Start proxy

```make
egress-proxy-up: networks
	docker run -d \
	  --name go-agent-egress-proxy \
	  --network go-agent-upstream-net \
	  -v $(PWD)/squid.conf:/etc/squid/squid.conf:ro \
	  ubuntu/squid:latest
	docker network connect go-agent-internal-net go-agent-egress-proxy
```

### Stop proxy

```make
egress-proxy-down:
	docker stop go-agent-egress-proxy || true
	docker rm go-agent-egress-proxy || true
```

### Combined setup

```make
egress-init: networks egress-proxy-up
```

Add any additional quality-of-life targets if useful, such as log tailing or connectivity verification.

---

## Validation

Suggested validation flow:

1. Start the proxy
2. Launch the agent session with proxy variables enabled
3. Verify approved HTTPS requests succeed through Squid
4. Verify unapproved domains are denied by Squid
5. Inspect Squid logs for CONNECT tunnel entries
6. Confirm the agent session has no direct Internet path because it is attached only to the internal network
7. Confirm the Pi coding agent continues to function normally through the proxy path

Example log monitoring:

```sh
docker logs -f go-agent-egress-proxy
```

Expected log content:

```text
TCP_TUNNEL/200 CONNECT api.openai.com:443
```

---

## Security Model

The proxy is intended to enforce:

- approved outbound hostnames
- centralized logging of outbound requests
- controlled TLS tunnel mediation

It does **not** inspect encrypted payloads.

Direct Internet bypass is prevented by attaching agent sessions only to the internal network and attaching the proxy to both the internal and upstream networks.

---

## Deliverables

The completed task should include:

- `squid.conf`
- `Makefile` updates for network/proxy management
- `bin/run-shell` updates for proxy env vars and network membership
- validation instructions or scripts
- README updates describing the egress proxy model
- task progress tracking in `tasks/go-agent-egress-proxy/progress.md`

---

## Acceptance Criteria

The task is complete when:

1. The agent session is configured to use `go-agent-egress-proxy`
2. Approved HTTPS requests succeed through Squid
3. Unapproved destinations are denied by Squid
4. Squid logs show CONNECT tunnels for approved upstream endpoints
5. Documentation reflects the new egress setup and operational workflow
6. The session container cannot access the Internet directly because it is attached only to the internal network
