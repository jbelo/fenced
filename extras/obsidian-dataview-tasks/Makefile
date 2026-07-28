ROOT_DIR := $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../..)

OBSIDIAN_DV_TASKS_SKILL_NAME ?= obsidian-dataview-tasks
OBSIDIAN_DV_TASKS_SKILL_SOURCE ?= $(ROOT_DIR)/extras/obsidian-dataview-tasks/skills/$(OBSIDIAN_DV_TASKS_SKILL_NAME)
CODEX_SKILLS_DIR ?= $(HOME)/.codex/skills

.PHONY: help obsidian-dv-tasks-skill-install

help:
	@echo "make -f extras/obsidian-dataview-tasks/Makefile obsidian-dv-tasks-skill-install [CODEX_SKILLS_DIR=$(CODEX_SKILLS_DIR)]"

obsidian-dv-tasks-skill-install:
	@test -d "$(OBSIDIAN_DV_TASKS_SKILL_SOURCE)" || (echo "error: missing skill source: $(OBSIDIAN_DV_TASKS_SKILL_SOURCE)" >&2; exit 1)
	@test ! -e "$(CODEX_SKILLS_DIR)/$(OBSIDIAN_DV_TASKS_SKILL_NAME)" || (echo "error: skill already exists: $(CODEX_SKILLS_DIR)/$(OBSIDIAN_DV_TASKS_SKILL_NAME)" >&2; exit 1)
	@mkdir -p "$(CODEX_SKILLS_DIR)"
	cp -R "$(OBSIDIAN_DV_TASKS_SKILL_SOURCE)" "$(CODEX_SKILLS_DIR)/$(OBSIDIAN_DV_TASKS_SKILL_NAME)"
	@echo "Installed $(OBSIDIAN_DV_TASKS_SKILL_NAME) to $(CODEX_SKILLS_DIR)/$(OBSIDIAN_DV_TASKS_SKILL_NAME)"
