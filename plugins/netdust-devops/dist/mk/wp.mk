# ─────────────────────────────────────────────────────────────────────────────
# mk/wp.mk — WordPress data ops on top of the DDEV local loop.
#
# Owns: setup, pull, refresh, block-mail, and the production database backup
# that `make ship` requires. Everything flow- and deploy-shaped lives in
# Makefile.netdust and is identical on every stack.
#
# Vendored by netdust-devops. Do not edit in a project.
# ─────────────────────────────────────────────────────────────────────────────

include mk/ddev.mk

WP_CORE     := $(shell $(SITE) deploy.wp_path 2>/dev/null || $(SITE) structure.wpcli_path 2>/dev/null)
CONTENT_DIR := $(shell $(SITE) deploy.content_dir)

_help-stack:
	@echo "$(YELLOW)LOCAL$(RESET)        DDEV + WordPress"
	@printf "  $(GREEN)%-22s$(RESET) %s\n" "setup"             "first clone: .env, ddev, composer"
	@printf "  $(GREEN)%-22s$(RESET) %s\n" "dev"               "start the local loop"
	@printf "  $(GREEN)%-22s$(RESET) %s\n" "logs / restart / stop" "container lifecycle"
	@printf "  $(GREEN)%-22s$(RESET) %s\n" "ssh env=E"         "shell on an environment"
	@echo ""
	@echo "$(YELLOW)DATA$(RESET)         moves backward only — never into production"
	@printf "  $(GREEN)%-22s$(RESET) %s\n" "pull env=E"        "DB + third-party plugins → local (uploads=yes for media)"
	@printf "  $(GREEN)%-22s$(RESET) %s\n" "refresh env=E"     "production data → staging or development"
	@printf "  $(GREEN)%-22s$(RESET) %s\n" "block-mail env=E"  "install the outgoing-mail block"
	@echo ""

.PHONY: setup
setup: ## First clone: .env, DDEV, composer
	@$(MAKE) --no-print-directory _check-requirements
	@$(MAKE) --no-print-directory _check-ddev-installed
	@if [ ! -f .env ] && [ -f .env.example ]; then \
		cp .env.example .env && echo "$(YELLOW)✓ .env created from .env.example — configure it$(RESET)"; \
	fi
	@if ! ddev describe >/dev/null 2>&1; then \
		ddev config --docroot=$$($(SITE) structure.webroot) --project-type=wordpress --project-name=$(DDEV_PROJECT) && \
		echo "$(GREEN)✓ DDEV configured$(RESET)"; \
	fi
	@ddev start
	@ddev composer install
	@echo "$(GREEN)✅ Local setup complete$(RESET)"
	@echo "$(YELLOW)Next:$(RESET) configure .env  →  make pull env=production  →  make dev"

.PHONY: pull
pull: ## Pull DB + third-party plugins from an environment down to local (uploads=yes for media)
	@ENV="$(env)"; \
	if [ -z "$$ENV" ]; then ENV=production; fi; \
	if [ -z "$$($(SITE) environments.$$ENV.path)" ]; then \
		echo "$(RED)✗ Unknown environment: $$ENV$(RESET)"; exit 1; fi; \
	echo "$(BLUE)Pulling $$ENV → local$(RESET)"; \
	$(MAKE) --no-print-directory _check-ddev && \
	$(MAKE) --no-print-directory _pull-db env=$$ENV && \
	$(MAKE) --no-print-directory _pull-plugins env=$$ENV && \
	if [ "$(uploads)" = "yes" ]; then \
		$(MAKE) --no-print-directory _pull-uploads env=$$ENV; \
	else \
		echo "$(YELLOW)  uploads skipped — add uploads=yes to include them$(RESET)"; \
	fi && \
	echo "$(GREEN)✅ local refreshed from $$ENV$(RESET)"

.PHONY: refresh
refresh: ## Copy production data down to staging or development (make refresh env=staging)
	@ENV="$(env)"; \
	$(MAKE) --no-print-directory _refuse-production env=$$ENV || exit 1; \
	$(MAKE) --no-print-directory _need-tty verb="refresh env=$$ENV"; \
	echo "$(RED)╔══════════════════════════════════════════════════════╗$(RESET)"; \
	echo "$(RED)║  REPLACE $$ENV WITH PRODUCTION DATA$(RESET)"; \
	echo "$(RED)╚══════════════════════════════════════════════════════╝$(RESET)"; \
	echo "$(YELLOW)  database, uploads, third-party plugins and themes$(RESET)"; \
	echo "$(YELLOW)  $$ENV's current database will be replaced (a backup is taken)$(RESET)"; \
	read -p "Type 'yes' to continue: " reply; \
	if [ "$$reply" != "yes" ]; then echo "$(RED)✗ Cancelled$(RESET)"; exit 1; fi
	@$(MAKE) --no-print-directory block-mail env=$(env)
	@$(MAKE) --no-print-directory _refresh-db env=$(env)
	@$(MAKE) --no-print-directory _refresh-uploads env=$(env)
	@$(MAKE) --no-print-directory _refresh-plugins env=$(env)
	@echo "$(YELLOW)Re-deploying the git payload so custom plugins match the branch...$(RESET)"
	@$(MAKE) --no-print-directory deploy env=$(env)
	@echo "$(GREEN)✅ $(env) refreshed from production$(RESET)"

.PHONY: block-mail
block-mail: ## Install the outgoing-mail block on a non-production environment
	@ENV="$(env)"; \
	$(MAKE) --no-print-directory _refuse-production env=$$ENV || exit 1; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	REMOTE=$$($(SITE) environments.$$ENV.path); \
	PROD=$$($(SITE) environments.production.url | sed -E 's#^https?://##; s#/$$##'); \
	sed "s|__PRODUCTION_HOST__|$$PROD|" scripts/remote/00-block-outgoing-mail.php \
		| ssh -q "$$HOST" "cat > $$REMOTE/$(CONTENT_DIR)/mu-plugins/00-block-outgoing-mail.php" || exit 1; \
	echo "$(YELLOW)  self-disables if it ever lands on $$PROD$(RESET)"; \
	echo "$(GREEN)✓ mail block installed on $$ENV$(RESET)"

# `make ship` calls this before touching production.
_backup-data:
	@ENV="$(env)"; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	REMOTE=$$($(SITE) environments.$$ENV.path); \
	mkdir -p backups; \
	STAMP=$$(date +%Y%m%d-%H%M%S); \
	OUT="backups/$$ENV-$$STAMP.sql.gz"; \
	echo "$(YELLOW)Backing up the $$ENV database...$(RESET)"; \
	if ! ssh -qn "$$HOST" "cd $$REMOTE && wp db export --path=$(WP_CORE) - | gzip" > "$$OUT"; then \
		echo "$(RED)❌ Failed to back up the $$ENV database$(RESET)"; rm -f "$$OUT"; exit 1; \
	fi; \
	SIZE=$$(wc -c < "$$OUT" | tr -d ' '); \
	if [ "$$SIZE" -lt 1024 ]; then \
		echo "$(RED)✗ Database backup is $$SIZE bytes — not deploying$(RESET)"; rm -f "$$OUT"; exit 1; \
	fi; \
	echo "$(GREEN)✅ $$ENV database backed up: $$OUT ($$(( SIZE / 1024 )) KB)$(RESET)"

_pull-db:
	@ENV="$(env)"; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	SRC=$$($(SITE) environments.$$ENV.path); \
	SRC_URL=$$($(SITE) environments.$$ENV.url); \
	LOCAL_URL=$$($(SITE) local.url); \
	mkdir -p backups; \
	echo "$(YELLOW)Backing up local database...$(RESET)"; \
	ddev wp db export backups/local-before-pull-$$(date +%Y%m%d-%H%M%S).sql --add-drop-table --skip-lock-tables || exit 1; \
	echo "$(YELLOW)Streaming $$ENV database (DEFINER stripped, gzipped)...$(RESET)"; \
	: "the sed below is duplicated in scripts/remote/refresh-db.sh — that one"; \
	: "runs server-to-server, this one runs here for local."; \
	: "Change both or one path silently breaks (ERROR 1227 on the views)."; \
	ssh -qn "$$HOST" "cd $$SRC && wp db export --path=$(WP_CORE) --default-character-set=utf8mb4 --single-transaction --quick - | gzip" \
		| gunzip \
		| sed -E 's/DEFINER=[^ ]+ / /g; s/SQL SECURITY DEFINER/SQL SECURITY INVOKER/g' \
		> /tmp/$(PROJECT_NAME)-pull.sql || exit 1; \
	ddev import-db --file=/tmp/$(PROJECT_NAME)-pull.sql || { rm -f /tmp/$(PROJECT_NAME)-pull.sql; exit 1; }; \
	rm -f /tmp/$(PROJECT_NAME)-pull.sql; \
	echo "$(YELLOW)Rewriting URLs: $$SRC_URL → $$LOCAL_URL$(RESET)"; \
	ddev wp search-replace "$$SRC_URL" "$$LOCAL_URL" --all-tables --precise --skip-columns=guid --quiet || exit 1; \
	echo "$(YELLOW)Forcing mail simulation locally...$(RESET)"; \
	ddev wp eval '$$o = get_option("fluentmail-settings", array()); if (!is_array($$o)) { $$o = array(); } if (empty($$o["misc"]) || !is_array($$o["misc"])) { $$o["misc"] = array(); } $$o["misc"]["simulate_emails"] = "yes"; update_option("fluentmail-settings", $$o); echo "simulate_emails=yes";' || true; \
	echo "$(GREEN)✓ local database refreshed$(RESET)"; \
	echo "$(YELLOW)  transients left alone on purpose$(RESET)"

_pull-plugins:
	@ENV="$(env)"; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	SRC=$$($(SITE) environments.$$ENV.path); \
	EXCL=""; \
	for p in $$($(SITE) deploy.payload); do EXCL="$$EXCL --exclude=$$(basename $$p)/"; done; \
	for x in $$($(SITE) deploy.pull_exclude 2>/dev/null); do EXCL="$$EXCL --exclude=$$x"; done; \
	echo "$(YELLOW)Mirroring third-party plugins from $$ENV (git-owned and pull_exclude entries skipped)...$(RESET)"; \
	rsync -az --delete -e "ssh -q" $$EXCL \
		"$$HOST:$$SRC/$(CONTENT_DIR)/plugins/" $(WEBROOT)/$(CONTENT_DIR)/plugins/ || exit 1; \
	TEXCL=""; \
	for p in $$($(SITE) deploy.payload); do \
		case "$$p" in content/themes/*|*/themes/*) TEXCL="$$TEXCL --exclude=$$(basename $$p)/";; esac; \
	done; \
	echo "$(YELLOW)Mirroring themes (payload themes excluded)...$(RESET)"; \
	rsync -az --delete -e "ssh -q" $$TEXCL "$$HOST:$$SRC/$(CONTENT_DIR)/themes/" $(WEBROOT)/$(CONTENT_DIR)/themes/ || exit 1; \
	echo "$(GREEN)✓ third-party plugins and themes match $$ENV$(RESET)"

_pull-uploads:
	@ENV="$(env)"; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	SRC=$$($(SITE) environments.$$ENV.path); \
	echo "$(YELLOW)Mirroring uploads from $$ENV (incremental)...$(RESET)"; \
	rsync -az --delete -e "ssh -q" --info=stats1 \
		"$$HOST:$$SRC/$(CONTENT_DIR)/uploads/" $(WEBROOT)/$(CONTENT_DIR)/uploads/ || exit 1; \
	echo "$(GREEN)✓ uploads mirrored$(RESET)"

_refresh-db:
	@ENV="$(env)"; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	SRC=$$($(SITE) environments.production.path); \
	DST=$$($(SITE) environments.$$ENV.path); \
	DIR=$$($(SITE) deploy.state_dir); \
	SRC_URL=$$($(SITE) environments.production.url); \
	DST_URL=$$($(SITE) environments.$$ENV.url); \
	scp -q scripts/remote/refresh-db.sh "$$HOST:/tmp/ntdst-refresh-db.sh" || exit 1; \
	ssh -qn "$$HOST" "bash /tmp/ntdst-refresh-db.sh '$$SRC' '$$DST' '$$SRC_URL' '$$DST_URL' '$$DIR' '$$ENV' '$(WP_CORE)'; rc=\$$?; rm -f /tmp/ntdst-refresh-db.sh; exit \$$rc" || exit 1; \
	echo "$(GREEN)✓ database refreshed and mail simulation restored$(RESET)"; \
	echo "$(YELLOW)  transients left alone on purpose — deleting them all re-runs migrations$(RESET)"

_refresh-uploads:
	@ENV="$(env)"; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	SRC=$$($(SITE) environments.production.path); \
	DST=$$($(SITE) environments.$$ENV.path); \
	echo "$(YELLOW)Mirroring uploads (server-side, incremental)...$(RESET)"; \
	ssh -qn "$$HOST" "rsync -a --delete --info=stats2 $$SRC/$(CONTENT_DIR)/uploads/ $$DST/$(CONTENT_DIR)/uploads/" || exit 1; \
	echo "$(GREEN)✓ uploads mirrored$(RESET)"

_refresh-plugins:
	@ENV="$(env)"; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	SRC=$$($(SITE) environments.production.path); \
	DST=$$($(SITE) environments.$$ENV.path); \
	EXCL=""; \
	for p in $$($(SITE) deploy.payload); do EXCL="$$EXCL --exclude=$$(basename $$p)/"; done; \
	for x in $$($(SITE) deploy.pull_exclude 2>/dev/null); do EXCL="$$EXCL --exclude=$$x"; done; \
	echo "$(YELLOW)Mirroring third-party plugins (git-owned and pull_exclude entries skipped)...$(RESET)"; \
	ssh -qn "$$HOST" "rsync -a --delete $$EXCL $$SRC/$(CONTENT_DIR)/plugins/ $$DST/$(CONTENT_DIR)/plugins/" || exit 1; \
	TEXCL=""; \
	for p in $$($(SITE) deploy.payload); do \
		case "$$p" in content/themes/*|*/themes/*) TEXCL="$$TEXCL --exclude=$$(basename $$p)/";; esac; \
	done; \
	echo "$(YELLOW)Mirroring themes (payload themes excluded)...$(RESET)"; \
	ssh -qn "$$HOST" "rsync -a --delete $$TEXCL $$SRC/$(CONTENT_DIR)/themes/ $$DST/$(CONTENT_DIR)/themes/" || exit 1; \
	echo "$(GREEN)✓ third-party plugins and themes mirrored (mu-plugins untouched)$(RESET)"

.PHONY: _help-stack _backup-data _pull-db _pull-plugins _pull-uploads \
        _refresh-db _refresh-uploads _refresh-plugins
