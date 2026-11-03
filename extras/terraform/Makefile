ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)

AGENT_IMAGE ?= go-agent
AGENT_TERRAFORM_IMAGE ?= go-agent-terraform
AGENT_TERRAFORM_DOCKERFILE ?= $(ROOT_DIR)/extras/terraform/Dockerfile

.PHONY: help agent-terraform-build agent-terraform-check

help:
	@echo "make -f extras/terraform/Makefile agent-terraform-build [AGENT_IMAGE=go-agent] [AGENT_TERRAFORM_IMAGE=go-agent-terraform]"
	@echo "make -f extras/terraform/Makefile agent-terraform-check"

agent-terraform-build:
	docker build \
		--build-arg BASE_IMAGE=$(AGENT_IMAGE) \
		-t $(AGENT_TERRAFORM_IMAGE) \
		-f $(AGENT_TERRAFORM_DOCKERFILE) \
		$(ROOT_DIR)/extras/terraform

agent-terraform-check:
	docker run --rm --network none --read-only --user "$$(id -u):$$(id -g)" \
		--tmpfs /tmp:rw,mode=1777 --env HOME=/tmp --env CHECKPOINT_DISABLE=1 \
		"$(AGENT_TERRAFORM_IMAGE)" sh -ec 'terraform version; mkdir /tmp/tf-check; cd /tmp/tf-check; printf "terraform { required_version = \">= 1.11\" }\n" > main.tf; terraform init -backend=false; terraform validate'
