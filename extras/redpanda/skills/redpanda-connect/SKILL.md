---
name: redpanda-connect
description: Connect Kafka clients to the local harness Redpanda broker and inspect connectivity using rpk, not provision brokers or topics.
---

# Connect to Redpanda

Use the developer's overrides when supplied; these are local harness defaults, not live service status. Report missing services, tools, schemas, or credentials to the developer. Container provisioning and persistent-state cleanup remain host responsibilities.

For Kafka clients use `go-agent-redpanda:9092` as a bootstrap broker. Creating
the broker does not imply application topics have been created. If `rpk` is
available, inspect the broker with:

```sh
rpk cluster info -X brokers=go-agent-redpanda:9092
```
