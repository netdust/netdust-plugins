# ─────────────────────────────────────────────────────────────────────────────
# mk/statamic.mk — Statamic on the DDEV local loop.
#
# Statamic's content is flat files in the payload, so a deploy carries it and
# there is no database refresh to do. What ship must back up is the content
# tree plus whatever the site keeps in storage/.
#
# Vendored by netdust-devops. Do not edit in a project.
# ─────────────────────────────────────────────────────────────────────────────

include mk/ddev.mk

_help-stack:
	@echo "$(YELLOW)LOCAL$(RESET)        DDEV + Statamic"
	@printf "  $(GREEN)%-22s$(RESET) %s\n" "setup"             "first clone: .env, ddev, composer"
	@printf "  $(GREEN)%-22s$(RESET) %s\n" "dev"               "start the local loop"
	@printf "  $(GREEN)%-22s$(RESET) %s\n" "logs / restart / stop" "container lifecycle"
	@printf "  $(GREEN)%-22s$(RESET) %s\n" "ssh env=E"         "shell on an environment"
	@printf "  $(GREEN)%-22s$(RESET) %s\n" "pull-content env=E" "content + users + storage → local"
	@echo ""

.PHONY: setup
setup: ## First clone: .env, DDEV, composer
	@$(MAKE) --no-print-directory _check-requirements
	@$(MAKE) --no-print-directory _check-ddev-installed
	@if [ ! -f .env ] && [ -f .env.example ]; then \
		cp .env.example .env && echo "$(YELLOW)✓ .env created from .env.example — configure it$(RESET)"; \
	fi
	@if ! ddev describe >/dev/null 2>&1; then \
		ddev config --docroot=$$($(SITE) structure.webroot) --project-type=laravel --project-name=$(DDEV_PROJECT) && \
		echo "$(GREEN)✓ DDEV configured$(RESET)"; \
	fi
	@ddev start
	@ddev composer install
	@echo "$(GREEN)✅ Local setup complete$(RESET)"

# The directories that hold content a deploy does not carry. Declared in
# site.yml so a site with an unusual layout is not a fork of this file.
STATAMIC_DATA := $(shell $(SITE) deploy.data_paths 2>/dev/null || echo "content users storage")

.PHONY: pull-content
pull-content: ## Copy an environment's content tree down to local
	@ENV="$(env)"; [ -n "$$ENV" ] || ENV=production; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	SRC=$$($(SITE) environments.$$ENV.path); \
	[ -n "$$SRC" ] || { echo "$(RED)✗ Unknown environment: $$ENV$(RESET)"; exit 1; }; \
	for d in $(STATAMIC_DATA); do \
		echo "$(BLUE)  → $$d$(RESET)"; \
		rsync -az --delete -e "ssh -q" "$$HOST:$$SRC/$$d/" "$$d/" || exit 1; \
	done; \
	echo "$(GREEN)✅ content pulled from $$ENV$(RESET)"

_backup-data:
	@ENV="$(env)"; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	REMOTE=$$($(SITE) environments.$$ENV.path); \
	DIR=$$($(SITE) deploy.state_dir); \
	STAMP=$$(date +%Y%m%d-%H%M%S); \
	ARCHIVE="$$DIR/backups/$$ENV-content-$$STAMP.tar.gz"; \
	echo "$(YELLOW)Backing up the $$ENV content tree...$(RESET)"; \
	ssh -qn "$$HOST" "mkdir -p $$DIR/backups && cd $$REMOTE && tar czf $$ARCHIVE $(STATAMIC_DATA) 2>/dev/null; rc=\$$?; [ \$$rc -le 1 ] || exit \$$rc"; \
	SIZE=$$(ssh -qn "$$HOST" "stat -c %s $$ARCHIVE 2>/dev/null || echo 0"); \
	if [ "$$SIZE" -lt 1024 ]; then \
		echo "$(RED)✗ Content backup is $$SIZE bytes — not deploying$(RESET)"; exit 1; \
	fi; \
	echo "$(GREEN)✅ content backed up: $$ARCHIVE ($$(( SIZE / 1024 )) KB)$(RESET)"

.PHONY: _help-stack _backup-data
