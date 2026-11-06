ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
KMS_EXTRA_DIR := $(ROOT_DIR)/extras/kms

KMS_SOURCE ?= $(ROOT_DIR)/branch-kms
KMS_IMAGE ?= kms
KMS_FDB_VERSION ?= 7.3.68
KMS_FDB_ARCH ?= aarch64
KMS_GVA_CONTAINER ?= go-agent-kms-gva2
KMS_FRA_CONTAINER ?= go-agent-kms-fra1
KMS_CONFIG_DIR ?= $(KMS_EXTRA_DIR)/config
KMS_SECRETS_DIR ?= $(KMS_SOURCE)/secrets
KMS_FDB_CLUSTER_FILE ?= $(KMS_EXTRA_DIR)/.local/fdb.cluster
KMS_ROOT_KEY_ID ?= 5383347d-35c9-4e56-86a2-d504e540c2f1
FDB_CONTAINER ?= go-agent-fdb
FDB_CLUSTER_SOURCE ?= /var/fdb/fdb.cluster
AGENT_INTERNAL_NETWORK ?= go-agent-internal-net
KMS_GVA_DOCKER_RUN_EXTRA ?=
KMS_FRA_DOCKER_RUN_EXTRA ?=

.PHONY: help kms-image-build kms-cluster-sync kms-check kms-gva-up kms-fra-up kms-up kms-gva-down kms-fra-down kms-down kms-gva-logs kms-fra-logs kms-status

help:
	@echo "make -f extras/kms/Makefile kms-image-build [KMS_SOURCE=path] [KMS_FDB_ARCH=aarch64]"
	@echo "make -f extras/kms/Makefile kms-cluster-sync"
	@echo "make -f extras/kms/Makefile kms-gva-up | kms-fra-up | kms-up"
	@echo "make -f extras/kms/Makefile kms-gva-down | kms-fra-down | kms-down"
	@echo "make -f extras/kms/Makefile kms-gva-logs | kms-fra-logs | kms-status"

kms-image-build:
	@test -f "$(KMS_SOURCE)/Earthfile" || { echo "error: KMS_SOURCE has no Earthfile: $(KMS_SOURCE)" >&2; exit 1; }
	cd "$(KMS_SOURCE)" && earthly \
		--build-arg FDB_VERSION="$(KMS_FDB_VERSION)" \
		--build-arg FDB_ARCH="$(KMS_FDB_ARCH)" \
		+kms-image-build-local

kms-cluster-sync:
	@docker inspect "$(FDB_CONTAINER)" >/dev/null || { echo "error: FoundationDB container is unavailable: $(FDB_CONTAINER)" >&2; exit 1; }
	@mkdir -p "$(dir $(KMS_FDB_CLUSTER_FILE))"
	docker cp "$(FDB_CONTAINER):$(FDB_CLUSTER_SOURCE)" "$(KMS_FDB_CLUSTER_FILE)"
	@echo "Copied FoundationDB cluster file to $(KMS_FDB_CLUSTER_FILE)"

kms-check:
	@docker image inspect "$(KMS_IMAGE)" >/dev/null || { echo "error: KMS image is unavailable: $(KMS_IMAGE); run kms-image-build" >&2; exit 1; }
	@docker network inspect "$(AGENT_INTERNAL_NETWORK)" >/dev/null || { echo "error: agent network is unavailable: $(AGENT_INTERNAL_NETWORK); run make networks" >&2; exit 1; }
	@test -f "$(KMS_CONFIG_DIR)/gva2.yaml" -a -f "$(KMS_CONFIG_DIR)/fra1.yaml" || { echo "error: missing KMS zone config in $(KMS_CONFIG_DIR)" >&2; exit 1; }
	@test -d "$(KMS_SECRETS_DIR)" || { echo "error: KMS secrets directory is unavailable: $(KMS_SECRETS_DIR)" >&2; exit 1; }
	@test -f "$(KMS_SECRETS_DIR)/$(KMS_ROOT_KEY_ID)" || { echo "error: KMS root key file $(KMS_ROOT_KEY_ID) is missing from $(KMS_SECRETS_DIR)" >&2; exit 1; }
	@test -s "$(KMS_FDB_CLUSTER_FILE)" || { echo "error: FoundationDB cluster file is missing: $(KMS_FDB_CLUSTER_FILE); run kms-cluster-sync" >&2; exit 1; }
	@if grep -Eq '@(127\.0\.0\.1|localhost):' "$(KMS_FDB_CLUSTER_FILE)"; then \
		echo "error: FoundationDB cluster file points to localhost, which is unreachable from KMS containers" >&2; \
		exit 1; \
	fi

kms-gva-up: kms-check
	@docker rm -f "$(KMS_GVA_CONTAINER)" >/dev/null 2>&1 || true
	docker run -d \
		--name "$(KMS_GVA_CONTAINER)" \
		--network "$(AGENT_INTERNAL_NETWORK)" \
		--mount "type=bind,src=$(KMS_CONFIG_DIR)/gva2.yaml,target=/etc/kms/config.yaml,readonly" \
		--mount "type=bind,src=$(KMS_SECRETS_DIR),target=/etc/kms/secrets,readonly" \
		--mount "type=bind,src=$(KMS_FDB_CLUSTER_FILE),target=/etc/kms/fdb.cluster,readonly" \
		$(KMS_GVA_DOCKER_RUN_EXTRA) \
		"$(KMS_IMAGE)" -f /etc/kms/config.yaml

kms-fra-up: kms-check
	@docker rm -f "$(KMS_FRA_CONTAINER)" >/dev/null 2>&1 || true
	docker run -d \
		--name "$(KMS_FRA_CONTAINER)" \
		--network "$(AGENT_INTERNAL_NETWORK)" \
		--mount "type=bind,src=$(KMS_CONFIG_DIR)/fra1.yaml,target=/etc/kms/config.yaml,readonly" \
		--mount "type=bind,src=$(KMS_SECRETS_DIR),target=/etc/kms/secrets,readonly" \
		--mount "type=bind,src=$(KMS_FDB_CLUSTER_FILE),target=/etc/kms/fdb.cluster,readonly" \
		$(KMS_FRA_DOCKER_RUN_EXTRA) \
		"$(KMS_IMAGE)" -f /etc/kms/config.yaml

kms-up: kms-gva-up kms-fra-up

kms-gva-down:
	-docker rm -f "$(KMS_GVA_CONTAINER)"

kms-fra-down:
	-docker rm -f "$(KMS_FRA_CONTAINER)"

kms-down: kms-gva-down kms-fra-down

kms-gva-logs:
	docker logs -f "$(KMS_GVA_CONTAINER)"

kms-fra-logs:
	docker logs -f "$(KMS_FRA_CONTAINER)"

kms-status:
	docker ps -a --filter "name=^/$(KMS_GVA_CONTAINER)$$" --filter "name=^/$(KMS_FRA_CONTAINER)$$"
