# ─────────────────────────────────────────────────────────────────────────────
# mk/node.mk — Bun / Node projects. No DDEV: the local loop is the package
# manager's dev server.
#
# `commands.dev`, `commands.build` and `commands.install` come from site.yml,
# so bun / pnpm / npm is a config value, not a fork of this file.
#
# Vendored by netdust-devops. Do not edit in a project.
# ─────────────────────────────────────────────────────────────────────────────

PKG_INSTALL := $(shell $(SITE) commands.install 2>/dev/null || echo "npm install")
PKG_DEV     := $(shell $(SITE) commands.dev 2>/dev/null || echo "npm run dev")
PKG_BUILD   := $(shell $(SITE) commands.build 2>/dev/null || echo "npm run build")

_help-stack:
	@echo "$(YELLOW)LOCAL$(RESET)        Node / Bun"
	@printf "  $(GREEN)%-22s$(RESET) %s\n" "setup" "install dependencies, create .env"
	@printf "  $(GREEN)%-22s$(RESET) %s\n" "dev"   "$(PKG_DEV)"
	@printf "  $(GREEN)%-22s$(RESET) %s\n" "build" "$(PKG_BUILD)"
	@echo ""

.PHONY: setup
setup: ## First clone: .env + dependencies
	@$(MAKE) --no-print-directory _check-requirements
	@if [ ! -f .env ] && [ -f .env.example ]; then \
		cp .env.example .env && echo "$(YELLOW)✓ .env created from .env.example — configure it$(RESET)"; \
	fi
	@$(PKG_INSTALL)
	@echo "$(GREEN)✅ Local setup complete$(RESET)"

.PHONY: dev
dev: ## Start the dev server (warns when you are on a rung branch)
	@$(MAKE) --no-print-directory _warn-rung-branch
	@$(PKG_DEV)

.PHONY: build
build: ## Produce the deployable build
	@$(PKG_BUILD)

# A built payload must exist and be current before it ships.
_backup-data:
	@if [ "$$($(SITE) deploy.skip_data_backup 2>/dev/null)" = "true" ]; then \
		echo "$(YELLOW)⚠  no server-side data to back up (deploy.skip_data_backup: true)$(RESET)"; \
	else \
		echo "$(RED)✗ stack 'node' has no data backup verb$(RESET)"; \
		echo "$(YELLOW)  Set deploy.skip_data_backup: true in site.yml if this project keeps$(RESET)"; \
		echo "$(YELLOW)  no server-side state, or add _backup-data to the project Makefile.$(RESET)"; \
		exit 1; \
	fi

_status-stack:
	@printf "  node:    %s\n" "$$(node --version 2>/dev/null || echo 'not installed')"

_doctor-stack:
	@command -v node >/dev/null 2>&1 && printf "  ✅ node\n" || printf "  $(RED)❌ node (required for stack $(STACK))$(RESET)\n"

.PHONY: _help-stack _backup-data _status-stack _doctor-stack
