ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)

OBSIDIAN_PM_SKILL_NAME ?= obsidian-project-manager-tasks
OBSIDIAN_PM_SKILL_SOURCE ?= $(ROOT_DIR)/extras/obsidian-project-manager/skills/$(OBSIDIAN_PM_SKILL_NAME)
CODEX_SKILLS_DIR ?= $(HOME)/.codex/skills

.PHONY: help obsidian-pm-skill-install

help:
	@echo "make -f extras/obsidian-project-manager/Makefile obsidian-pm-skill-install [CODEX_SKILLS_DIR=$(CODEX_SKILLS_DIR)]"

obsidian-pm-skill-install:
	@test -d "$(OBSIDIAN_PM_SKILL_SOURCE)" || (echo "error: missing skill source: $(OBSIDIAN_PM_SKILL_SOURCE)" >&2; exit 1)
	@test ! -e "$(CODEX_SKILLS_DIR)/$(OBSIDIAN_PM_SKILL_NAME)" || (echo "error: skill already exists: $(CODEX_SKILLS_DIR)/$(OBSIDIAN_PM_SKILL_NAME)" >&2; exit 1)
	@mkdir -p "$(CODEX_SKILLS_DIR)"
	cp -R "$(OBSIDIAN_PM_SKILL_SOURCE)" "$(CODEX_SKILLS_DIR)/$(OBSIDIAN_PM_SKILL_NAME)"
	@echo "Installed $(OBSIDIAN_PM_SKILL_NAME) to $(CODEX_SKILLS_DIR)/$(OBSIDIAN_PM_SKILL_NAME)"
