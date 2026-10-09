ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
EXTRA_DIR := $(ROOT_DIR)/extras/cassandra

CASSANDRA_VERSION ?= 4.1.10
CASSANDRA_IMAGE ?= cassandra:$(CASSANDRA_VERSION)
CASSANDRA_CONTAINER ?= go-agent-cassandra
CASSANDRA_DATA_VOLUME ?= go-agent-cassandra-data
CASSANDRA_HEAP ?= 1G
CASSANDRA_WAIT_ATTEMPTS ?= 60
CASSANDRA_DOCKER_RUN_EXTRA ?=
AGENT_INTERNAL_NETWORK ?= go-agent-internal-net

.DEFAULT_GOAL := help
.PHONY: help networks cassandra-up cassandra-ready cassandra-cqlsh cassandra-logs cassandra-status cassandra-down cassandra-clean-data

help:
	@echo "make -f extras/cassandra/Makefile cassandra-up"
	@echo "make -f extras/cassandra/Makefile cassandra-ready"
	@echo "make -f extras/cassandra/Makefile cassandra-cqlsh | cassandra-logs | cassandra-status"
	@echo "make -f extras/cassandra/Makefile cassandra-down"
	@echo "make -f extras/cassandra/Makefile cassandra-clean-data CONFIRM_DELETE=$(CASSANDRA_DATA_VOLUME)"

networks:
	$(MAKE) -C "$(ROOT_DIR)" networks AGENT_INTERNAL_NETWORK="$(AGENT_INTERNAL_NETWORK)"

cassandra-up: networks
	@docker volume inspect "$(CASSANDRA_DATA_VOLUME)" >/dev/null 2>&1 || docker volume create "$(CASSANDRA_DATA_VOLUME)"
	@if docker container inspect "$(CASSANDRA_CONTAINER)" >/dev/null 2>&1; then \
		docker start "$(CASSANDRA_CONTAINER)"; \
	else \
		docker run -d \
			--name "$(CASSANDRA_CONTAINER)" \
			--network "$(AGENT_INTERNAL_NETWORK)" \
			--mount "type=volume,src=$(CASSANDRA_DATA_VOLUME),target=/var/lib/cassandra" \
			-e CASSANDRA_CLUSTER_NAME=public_api \
			-e CASSANDRA_ENDPOINT_SNITCH=GossipingPropertyFileSnitch \
			-e CASSANDRA_DC=datacenter1 \
			-e CASSANDRA_NUM_TOKENS=1 \
			-e "JVM_OPTS=-Xms$(CASSANDRA_HEAP) -Xmx$(CASSANDRA_HEAP) -Dcassandra.skip_wait_for_gossip_to_settle=0 -Dcassandra.initial_token=0" \
			--ulimit nofile=65536:65536 \
			$(CASSANDRA_DOCKER_RUN_EXTRA) \
			"$(CASSANDRA_IMAGE)"; \
	fi

cassandra-ready:
	bash "$(EXTRA_DIR)/scripts/wait-ready.sh" "$(CASSANDRA_CONTAINER)" "$(CASSANDRA_WAIT_ATTEMPTS)"

cassandra-cqlsh:
	docker exec -it "$(CASSANDRA_CONTAINER)" cqlsh

cassandra-logs:
	docker logs -f "$(CASSANDRA_CONTAINER)"

cassandra-status:
	docker ps -a --filter "name=^/$(CASSANDRA_CONTAINER)$$"

cassandra-down:
	@if docker container inspect "$(CASSANDRA_CONTAINER)" >/dev/null 2>&1; then \
		docker stop -t 60 "$(CASSANDRA_CONTAINER)" && docker rm "$(CASSANDRA_CONTAINER)"; \
	fi

cassandra-clean-data:
	@test -n "$(CASSANDRA_DATA_VOLUME)" && test "$(CONFIRM_DELETE)" = "$(CASSANDRA_DATA_VOLUME)" || { echo "Set CONFIRM_DELETE=$(CASSANDRA_DATA_VOLUME) to permanently delete this volume." >&2; exit 1; }
	docker volume rm "$(CASSANDRA_DATA_VOLUME)"
