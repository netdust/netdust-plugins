# ─────────────────────────────────────────────────────────────────────────────
# mk/ddev.mk — the DDEV local loop. Shared by every containerised stack
# (wp, statamic, laravel). Included by those stacks, never selected directly.
#
# Vendored by netdust-devops. Do not edit in a project.
# ─────────────────────────────────────────────────────────────────────────────

DDEV_PROJECT := $(shell $(SITE) local.ddev_project 2>/dev/null)
DDEV_TYPE    ?= php

.PHONY: dev
dev: ## Start the local loop (warns when you are on a rung branch)
	@$(MAKE) --no-print-directory _check-ddev-installed
	@ddev start
	@$(MAKE) --no-print-directory _warn-rung-branch
	@echo "$(GREEN)✅ $$($(SITE) local.url)$(RESET)  on branch $$(git branch --show-current)"

.PHONY: logs
logs: ## Tail the container logs
	@ddev logs -f

.PHONY: restart
restart: ## Restart the containers
	@ddev restart

.PHONY: stop
stop: ## Stop the containers
	@ddev stop

.PHONY: ssh
ssh: ## SSH into an environment (make ssh env=staging)
	@ENV="$(env)"; [ -n "$$ENV" ] || ENV=staging; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	P=$$($(SITE) environments.$$ENV.path); \
	[ -n "$$P" ] || { echo "$(RED)✗ Unknown environment: $$ENV$(RESET)"; exit 1; }; \
	ssh "$$HOST" -t "cd $$P; bash"

_check-ddev-installed:
	@command -v ddev >/dev/null 2>&1 || { echo "$(RED)❌ DDEV not installed$(RESET)"; exit 1; }

_check-ddev:
	@if ! ddev describe >/dev/null 2>&1; then \
		echo "$(RED)❌ DDEV not running. Run 'make dev' first$(RESET)"; \
		exit 1; \
	fi

_doctor-stack:
	@command -v ddev >/dev/null 2>&1 && printf "  ✅ ddev\n" || printf "  $(RED)❌ ddev (required for stack $(STACK))$(RESET)\n"

_status-stack:
	@printf "  ddev:    %s\n" "$$(ddev describe >/dev/null 2>&1 && echo running || echo stopped)"

.PHONY: _check-ddev-installed _check-ddev _doctor-stack _status-stack
