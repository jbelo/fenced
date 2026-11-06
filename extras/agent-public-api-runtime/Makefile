ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
EXTRA_DIR := $(ROOT_DIR)/extras/agent-public-api-runtime
AGENT_IMAGE ?= go-agent
AGENT_JAVA_IMAGE ?= go-agent-java
# Empty uses the pinned default in the Dockerfile.
JAVA_IMAGE ?=
PUBLIC_API_SOURCE ?= $(ROOT_DIR)/branch-public-api
CASSANDRA_CONTAINER ?= go-agent-cassandra
CASSANDRA_WAIT_ATTEMPTS ?= 60
PUBLIC_API_JAR ?= $(PUBLIC_API_SOURCE)/modules/backend/target/public-api.jar

.DEFAULT_GOAL := help
.PHONY: cassandra-init-idstore cassandra-init-public-api help agent-java-build agent-java-check public-api-build public-api-jar-check

help:
	@echo "make -f extras/agent-public-api-runtime/Makefile cassandra-init-idstore [PUBLIC_API_SOURCE=/path/to/repo]"
	@echo "make -f extras/agent-public-api-runtime/Makefile cassandra-init-public-api [PUBLIC_API_SOURCE=/path/to/repo]"
	@echo "Java-only agent extension for host-built Public API uberjars. No service is started automatically."
	@echo "make -f extras/agent-public-api-runtime/Makefile agent-java-build"
	@echo "make -f extras/agent-public-api-runtime/Makefile agent-java-check"
	@echo "make -f extras/agent-public-api-runtime/Makefile public-api-build [PUBLIC_API_SOURCE=/path/to/repo]"
	@echo "make -f extras/agent-public-api-runtime/Makefile public-api-jar-check [PUBLIC_API_JAR=/path/to/public-api.jar]"

agent-java-build:
	docker build --build-arg "BASE_IMAGE=$(AGENT_IMAGE)" \
		$(if $(JAVA_IMAGE),--build-arg "JAVA_IMAGE=$(JAVA_IMAGE)") \
		-t "$(AGENT_JAVA_IMAGE)" "$(EXTRA_DIR)"

agent-java-check:
	docker run --rm --network none --read-only --user "$$(id -u):$$(id -g)" \
		--tmpfs /tmp:rw,mode=1777 --env HOME=/tmp \
		"$(AGENT_JAVA_IMAGE)" java -version

# Uses the host's normal Java/Clojure tools and dependency credentials.
public-api-build:
	$(MAKE) -C "$(PUBLIC_API_SOURCE)" build

# Load the real application entry point, without services, credentials or dependency downloads.
public-api-jar-check:
	@test -s "$(PUBLIC_API_JAR)" || { echo "Missing uberjar: $(PUBLIC_API_JAR); run public-api-build first." >&2; exit 1; }
	docker run --rm --network none --read-only --user "$$(id -u):$$(id -g)" \
		--hostname public-api-check --add-host public-api-check:127.0.0.1 \
		--tmpfs /tmp:rw,exec,size=256m,mode=1777 --env HOME=/tmp \
		--mount "type=bind,src=$(abspath $(PUBLIC_API_JAR)),target=/app/public-api.jar,readonly" \
		"$(AGENT_JAVA_IMAGE)" java -Xmx1g -jar /app/public-api.jar --help

# Apply application schemas to an existing Cassandra service; no container is started.
cassandra-init-idstore:
	bash "$(EXTRA_DIR)/scripts/init-schema.sh" idstore "$(CASSANDRA_CONTAINER)" "$(CASSANDRA_WAIT_ATTEMPTS)" "$(PUBLIC_API_SOURCE)"

cassandra-init-public-api:
	bash "$(EXTRA_DIR)/scripts/init-schema.sh" public-api "$(CASSANDRA_CONTAINER)" "$(CASSANDRA_WAIT_ATTEMPTS)" "$(PUBLIC_API_SOURCE)"
