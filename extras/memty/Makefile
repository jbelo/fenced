ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)
INSTALL_DIR ?= $(HOME)/.local/bin

.PHONY: help memty-install

help:
	@echo "make -f extras/memty/Makefile memty-install [INSTALL_DIR=...]"
	@echo "memty-shell [story-shell options]  # MEMTY_SOURCE defaults to ~/personal/memty"

memty-install:
	install -d "$(INSTALL_DIR)"
	install -m 0755 "$(ROOT_DIR)/extras/memty/bin/memty-shell" "$(INSTALL_DIR)/memty-shell"
