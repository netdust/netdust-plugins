# WordPress Bedrock Development Makefile
# Simple, secure workflow for small teams
#
# DEPLOYMENT STRATEGY: Git bundles (no GitHub/remote repo required!)
# This uses git bundles for deployment, meaning you can deploy directly
# from local to servers without any central repository.
#
# WORKFLOW: setup → dev → save → deploy → ship
# - No external dependencies (GitHub, CI/CD)
# - Direct local-to-server deployment
# - Built-in safety checks and backups
# - Templates for reusable site setups
#
# Version: 2.0 - Simplified & Reliable

# === CONFIGURATION ===
PROJECT_NAME := $(shell scripts/site site.name)

# Every host, path, URL and branch is read from site.yml — never hardcoded here.
SITE := scripts/site

# Layout comes from site.yml, so the same Makefile serves every stack:
# custom (app/), Bedrock (web/), standard (WP at the root).
WEBROOT  := $(shell scripts/site structure.webroot)
WP_CORE  := $(shell scripts/site deploy.wp_path)

# Branch names are derived from the environments — never written twice.
# A project without a development environment integrates on its review branch.
BR_PROD   := $(shell scripts/site environments.production.branch 2>/dev/null || scripts/site environments.staging.branch 2>/dev/null)
HAS_PROD  := $(shell scripts/site environments.production.path >/dev/null 2>&1 && echo yes || echo no)
BR_REVIEW := $(shell scripts/site environments.staging.branch)
BR_INTEG  := $(shell scripts/site environments.development.branch 2>/dev/null || scripts/site environments.staging.branch 2>/dev/null)
# Sourced from site.yml — never edit a host or path here.
STAGING_HOST := $(shell $(SITE) deploy.ssh_host)
STAGING_PATH := $(shell $(SITE) environments.staging.path)
STAGING_URL := $(shell $(SITE) environments.staging.url)
PRODUCTION_HOST := $(shell $(SITE) deploy.ssh_host)
PRODUCTION_PATH := $(shell $(SITE) environments.production.path 2>/dev/null)
PRODUCTION_URL := $(shell $(SITE) environments.production.url 2>/dev/null)


# Path Configuration - Adjust these for your setup
CONTENT_DIR := $(shell scripts/site deploy.content_dir)
UPLOADS_DIR := $(CONTENT_DIR)/uploads
PLUGINS_DIR := $(CONTENT_DIR)/plugins
THEMES_DIR := $(CONTENT_DIR)/themes
MU_PLUGINS_DIR := $(CONTENT_DIR)/mu-plugins

# Colors
RED := \033[31m
GREEN := \033[32m
YELLOW := \033[33m
BLUE := \033[34m
RESET := \033[0m

# WSL/Ubuntu PATH fix
# export PATH := /usr/bin:/bin:$(PATH)

# === HELP & STATUS ===
.PHONY: help
help: ## Show this help
	@echo "$(BLUE)╔════════════════════════════════════════════════════╗$(RESET)"
	@echo "$(BLUE)║  $(PROJECT_NAME) - WordPress Bedrock Development$(RESET)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════╝$(RESET)"
	@echo ""
	@echo "$(GREEN)Branch:$(RESET) $(shell git branch --show-current 2>/dev/null || echo 'none')"
	@echo "$(GREEN)DDEV:$(RESET) $(shell if ddev describe >/dev/null 2>&1; then echo 'running'; else echo 'not installed'; fi)"
	@echo ""
	@echo "$(YELLOW)🚀 Deploy:$(RESET) rsync moves the files, git is the gate and the ledger"
	@echo "   • site.yml describes  ·  Makefile executes  ·  Claude drives"
	@if [ "$(BR_INTEG)" = "$(BR_REVIEW)" ]; then \
		echo "   • feature → $(BR_REVIEW) → $(BR_PROD)  (hotfix branches off $(BR_PROD))"; \
	else \
		echo "   • feature → $(BR_INTEG) → $(BR_REVIEW) → $(BR_PROD)  (hotfix branches off $(BR_PROD))"; \
	fi
	@echo "   • a deploy needs a clean tree, the right branch, and HEAD pushed"
	@echo ""
	@echo "$(YELLOW)📋 INITIAL SETUP$(RESET)"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "setup" "Complete local setup"
	@echo ""
	@echo "$(YELLOW)🔄 DAILY WORKFLOW$(RESET)"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "dev" "Start development (ensures safe branch)"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "save" "Commit your work (auto-stages all changes)"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "deploy env=NAME" "Deploy the payload to an environment"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "deploy-test env=NAME" "Dry run — show what a deploy would change"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "deployed" "Show which commit runs on each environment"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "ship" "Ship to production (gate, backups, confirm)"
	@echo ""
	@echo "$(YELLOW)🌿 FEATURE BRANCHES$(RESET)"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "feature name=X" "Start a feature (branches from $(BR_INTEG))"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "hotfix name=X" "Start a hotfix (branches from origin/$(BR_PROD))"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "promote name=X" "Send ONE feature to staging"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "release" "Promote staging to master"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "finish" "Merge one step up the promotion path"
	@echo ""
	@echo "$(YELLOW)🔁 SYNC TOOLS$(RESET)"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "pull env=NAME" "Pull DB + plugins down to local (uploads=yes for media)"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "refresh env=NAME" "Copy production data down to staging/development"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "block-mail env=NAME" "Install the outgoing-mail block"
	@echo ""
	@echo "$(YELLOW)🛠️  UTILITIES$(RESET)"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "status" "Local branch + what runs on each environment"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "doctor" "Check required tools and SSH connectivity"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "health" "Fleet health: drift, ledger, guards, patched files"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "test" "Run the deploy tooling tests (no server contact)"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "gate" "Run this project's own test suite"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "rollback env=NAME" "Redeploy the previously deployed commit"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "ssh" "SSH to staging"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "ssh-prod" "SSH to production"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "logs" "Show DDEV logs"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "restart" "Restart DDEV"
	@printf "  $(GREEN)%-20s$(RESET) %s\n" "stop" "Stop DDEV"
	@echo ""
	@echo "$(BLUE)Quickstart:$(RESET) make setup && make dev"
	@echo "$(BLUE)Workflow:$(RESET) feature name=X → finish → deploy env=development → promote name=X → deploy env=staging → release → ship"

# === INITIAL SETUP ===

setup: ## Complete local setup
	@echo "$(BLUE)Setting up $(PROJECT_NAME) locally...$(RESET)"
	@$(MAKE) --no-print-directory _check-requirements
	@if [ ! -f .env ]; then \
		cp .env.example .env && \
		echo "$(YELLOW)✓ Created .env - Please configure it!$(RESET)"; \
	fi
	@if ! ddev describe >/dev/null 2>&1; then \
		ddev config --docroot=$$($(SITE) local.webroot) --project-type=wordpress --project-name=$$($(SITE) local.ddev_project) && \
		echo "$(GREEN)✓ DDEV configured$(RESET)"; \
	fi
	@ddev start
	@ddev composer install
	@echo "$(GREEN)✅ Local setup complete!$(RESET)"
	@echo "$(YELLOW)Next steps:$(RESET)"
	@echo "  1. Configure .env"
	@echo "  2. make pull env=production   (database + third-party plugins)"
	@echo "  3. make dev"

# === DAILY WORKFLOW ===

dev: ## Start development (ensures safe branch)
	@echo "$(BLUE)Starting development...$(RESET)"
	@$(MAKE) --no-print-directory _check-ddev
	@ddev start
	@$(MAKE) --no-print-directory _ensure-safe-branch
	@echo "$(GREEN)✅ Ready on branch: $(shell git branch --show-current)$(RESET)"
	@echo "$(GREEN)🌐 Local: https://$(PROJECT_NAME).ddev.site$(RESET)"

save: ## Commit your work (auto-stages all changes)
	@$(MAKE) --no-print-directory _ensure-safe-branch
	@if [ -z "$$(git status --porcelain 2>/dev/null)" ]; then \
		echo "$(YELLOW)No changes to save$(RESET)"; \
	else \
		git add -A; \
		echo "$(YELLOW)Changes to commit:$(RESET)"; \
		git status --short; \
		read -p "Commit message: " msg && \
		if [ -n "$$msg" ]; then \
			git commit -m "$$msg" && \
			echo "$(GREEN)✅ Saved: $$msg$(RESET)"; \
		else \
			echo "$(RED)❌ Commit cancelled$(RESET)"; \
		fi; \
	fi

deploy: ## Deploy the payload to an environment (make deploy env=staging)
	@$(MAKE) --no-print-directory _deploy-gate env=$(env)
	@$(MAKE) --no-print-directory _deploy-confirm env=$(env)
	@$(MAKE) --no-print-directory _deploy-transport env=$(env) dryrun="$(dryrun)"
	@if [ -z "$(dryrun)" ]; then $(MAKE) --no-print-directory _deploy-stamp env=$(env); fi
	@if [ -z "$(dryrun)" ]; then $(MAKE) --no-print-directory _deploy-opcache env=$(env); fi
	@echo "$(GREEN)🌐 $$($(SITE) environments.$(env).url)$(RESET)"

deploy-test: ## Show what a deploy would change, without changing it
	@$(MAKE) --no-print-directory deploy env=$(env) dryrun=--dry-run

ship: ## Ship to production (gate, backups, confirm, deploy)
	@if [ "$(HAS_PROD)" != "yes" ]; then \
		echo "$(RED)✗ No production environment in site.yml yet$(RESET)"; \
		echo "$(YELLOW)  Add environments.production once the site is live.$(RESET)"; exit 1; fi
	@$(MAKE) --no-print-directory _deploy-gate env=production
	@$(MAKE) --no-print-directory _backup-production
	@$(MAKE) --no-print-directory _backup-payload env=production
	@$(MAKE) --no-print-directory deploy env=production

# === FEATURE BRANCHES ===

feature: ## Start a feature (make feature name=my-feature) — branches from the integration branch
	@if [ -z "$(name)" ]; then echo "$(RED)Usage: make feature name=my-feature$(RESET)"; exit 1; fi
	@if ! echo "$(name)" | grep -qE '^[a-zA-Z][a-zA-Z0-9._-]*$$'; then \
		echo "$(RED)✗ Invalid name: use letters, digits, dot, dash, underscore$(RESET)"; exit 1; fi
	@$(MAKE) --no-print-directory _ensure-clean-git
	@git fetch --quiet origin $(BR_INTEG)
	@git checkout -b "feature/$(name)" origin/$(BR_INTEG)
	@echo "$(GREEN)✅ On feature/$(name), branched from origin/$(BR_INTEG)$(RESET)"

hotfix: ## Start a hotfix (make hotfix name=vat-rounding) — branches from the production branch
	@if [ -z "$(name)" ]; then echo "$(RED)Usage: make hotfix name=my-fix$(RESET)"; exit 1; fi
	@if ! echo "$(name)" | grep -qE '^[a-zA-Z][a-zA-Z0-9._-]*$$'; then \
		echo "$(RED)✗ Invalid name: use letters, digits, dot, dash, underscore$(RESET)"; exit 1; fi
	@$(MAKE) --no-print-directory _ensure-clean-git
	@git fetch --quiet origin $(BR_PROD)
	@git checkout -b "hotfix/$(name)" origin/$(BR_PROD)
	@echo "$(GREEN)✅ On hotfix/$(name), branched from origin/$(BR_PROD)$(RESET)"
	@echo "$(YELLOW)   Fix, commit, then: make finish$(RESET)"

finish: ## Merge the current branch one step up the promotion path
	@$(MAKE) --no-print-directory _ensure-clean-git
	@BRANCH=$$(git branch --show-current); \
	case "$$BRANCH" in \
		feature/*) \
			echo "$(YELLOW)$$BRANCH → $(BR_INTEG)$(RESET)"; \
			git checkout $(BR_INTEG) && git pull --quiet --ff-only && \
			git merge --no-ff "$$BRANCH" -m "Merge $$BRANCH" && \
			git push && git branch -d "$$BRANCH" && \
			echo "$(GREEN)✅ Merged to $(BR_INTEG). Deploy: make deploy env=development$(RESET)";; \
		hotfix/*) \
			echo "$(YELLOW)$$BRANCH → $(BR_PROD), then back down into $(BR_REVIEW) and $(BR_INTEG)$(RESET)"; \
			git checkout $(BR_PROD) && git pull --quiet --ff-only && \
			git merge --no-ff "$$BRANCH" -m "Merge $$BRANCH" && git push && \
			git checkout $(BR_REVIEW) && git pull --quiet --ff-only && \
			git merge --no-ff $(BR_PROD) -m "Merge $(BR_PROD) (hotfix $$BRANCH)" && git push && \
			git checkout $(BR_INTEG) && git pull --quiet --ff-only && \
			git merge --no-ff $(BR_PROD) -m "Merge $(BR_PROD) (hotfix $$BRANCH)" && git push && \
			git checkout $(BR_PROD) && git branch -d "$$BRANCH" && \
			echo "$(GREEN)✅ On $(BR_PROD), merged down into $(BR_REVIEW) and $(BR_INTEG). Ship: make ship$(RESET)";; \
		*) \
			echo "$(RED)✗ finish works on feature/* and hotfix/* — you are on $$BRANCH$(RESET)"; \
			exit 1;; \
	esac

promote: ## Send ONE feature to staging, leaving the rest of develop behind
       ## (make promote name=my-feature)
	@if [ -z "$(name)" ]; then echo "$(RED)Usage: make promote name=my-feature$(RESET)"; exit 1; fi
	@git fetch --quiet origin 2>/dev/null || true
	@BR="feature/$(name)"; \
	if ! git rev-parse --verify --quiet "$$BR" >/dev/null && \
	   ! git rev-parse --verify --quiet "origin/$$BR" >/dev/null; then \
		echo "$(RED)✗ No such branch: $$BR$(RESET)"; \
		echo "$(YELLOW)Features in flight:$(RESET)"; \
		git branch -a --list '*feature/*' | sed 's/^/  /'; \
		exit 1; \
	fi
	@$(MAKE) --no-print-directory _ensure-clean-git
	@BR="feature/$(name)"; \
	git rev-parse --verify --quiet "$$BR" >/dev/null || git branch "$$BR" "origin/$$BR"; \
	echo "$(YELLOW)$$BR → $(BR_REVIEW) ($(BR_INTEG) is not merged)$(RESET)"; \
	git --no-pager log --oneline $(BR_REVIEW).."$$BR" | head -20; \
	read -p "Continue? Type 'yes': " reply; \
	if [ "$$reply" != "yes" ]; then echo "$(RED)✗ Cancelled$(RESET)"; exit 1; fi; \
	git checkout $(BR_REVIEW) && git pull --quiet --ff-only && \
	git merge --no-ff "$$BR" -m "Promote $$BR to $(BR_REVIEW)" && git push && \
	echo "$(GREEN)✅ $$BR is on $(BR_REVIEW). Deploy: make deploy env=staging$(RESET)"; \
	echo "$(YELLOW)   $(BR_INTEG) keeps its other features — they are untouched.$(RESET)"

release: ## Promote the review branch to the production branch (then: make ship)
	@if [ "$(HAS_PROD)" != "yes" ]; then \
		echo "$(RED)✗ No production environment in site.yml yet$(RESET)"; exit 1; fi
	@$(MAKE) --no-print-directory _ensure-clean-git
	@git fetch --quiet origin
	@git checkout $(BR_REVIEW) && git pull --quiet --ff-only
	@git checkout $(BR_PROD) && git pull --quiet --ff-only
	@echo "$(YELLOW)About to merge $(BR_REVIEW) → $(BR_PROD):$(RESET)"
	@git --no-pager log --oneline $(BR_PROD)..$(BR_REVIEW) | head -30
	@read -p "Continue? Type 'yes': " reply; \
	if [ "$$reply" != "yes" ]; then echo "$(RED)✗ Cancelled$(RESET)"; exit 1; fi
	@git merge --no-ff $(BR_REVIEW) -m "Release: merge $(BR_REVIEW)" && git push
	@echo "$(GREEN)✅ $(BR_PROD) updated. Ship with: make ship$(RESET)"

# === SYNC TOOLS ===

block-mail: ## Install the outgoing-mail block on staging or development
	@ENV="$(env)"; \
	$(MAKE) --no-print-directory _refuse-production env=$$ENV || exit 1; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	REMOTE=$$($(SITE) environments.$$ENV.path); \
	PROD=$$($(SITE) environments.production.url | sed -E 's#^https?://##; s#/$$##'); \
	sed "s|__PRODUCTION_HOST__|$$PROD|" scripts/remote/00-block-outgoing-mail.php \
		| ssh -q "$$HOST" "cat > $$REMOTE/$(CONTENT_DIR)/mu-plugins/00-block-outgoing-mail.php" || exit 1; \
	echo "$(YELLOW)  self-disables if it ever lands on $$PROD$(RESET)"; \
	echo "$(GREEN)✓ mail block installed on $$ENV$(RESET)"

refresh: ## Copy production data down to staging or development (make refresh env=staging)
	@ENV="$(env)"; \
	$(MAKE) --no-print-directory _refuse-production env=$$ENV || exit 1; \
	URL=$$($(SITE) environments.$$ENV.url); \
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


pull: ## Pull DB + third-party plugins from an environment down to local DDEV
       ## (make pull env=production [uploads=yes])
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
		echo "$(YELLOW)  uploads skipped (20GB) — add uploads=yes to include them$(RESET)"; \
	fi && \
	echo "$(GREEN)✅ local refreshed from $$ENV$(RESET)"

# === TEMPLATES ===

deployed: ## Show which commit runs on each environment
	@DIR=$$($(SITE) deploy.state_dir); \
	for e in $$($(SITE) environments); do \
		H=$$($(SITE) environments.$$e.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
		J=$$(ssh -qn "$$H" "cat $$DIR/$$e.json 2>/dev/null" || true); \
		if [ -z "$$J" ]; then \
			printf "  $(YELLOW)%-12s never deployed with this tool$(RESET)\n" "$$e"; \
		else \
			printf "  $(GREEN)%-12s$(RESET) %s\n" "$$e" "$$J"; \
		fi; \
	done

status: ## Show complete project status
	@echo "$(BLUE)╔════════════════════════════════════════╗$(RESET)"
	@echo "$(BLUE)║         PROJECT STATUS                 ║$(RESET)"
	@echo "$(BLUE)╚════════════════════════════════════════╝$(RESET)"
	@echo ""
	@echo "$(YELLOW)LOCAL:$(RESET)"
	@echo "  Branch: $(shell git branch --show-current 2>/dev/null || echo 'none')"
	@echo "  Changes: $(shell git status --porcelain 2>/dev/null | wc -l | tr -d ' ') files"
	@echo "  Commit: $(shell git log --oneline -1 2>/dev/null | head -c 50 || echo 'No commits')"
	@echo "  DDEV: $(shell if ddev describe >/dev/null 2>&1; then echo 'running'; else echo 'stopped'; fi)"
	@echo ""
	@echo "$(YELLOW)DEPLOYED:$(RESET)"
	@$(MAKE) --no-print-directory deployed

logs: ## Show DDEV logs
	@ddev logs -f

restart: ## Restart DDEV
	@ddev restart

stop: ## Stop DDEV
	@ddev stop

ssh: ## SSH to staging
	@ssh $(STAGING_HOST) -t "cd $(STAGING_PATH); bash"

ssh-prod: ## SSH to production
	@ssh $(PRODUCTION_HOST) -t "cd $(PRODUCTION_PATH); bash"

test: ## Run the deploy tooling tests (never contacts a server)
	@scripts/tests/deploy-test.sh

gate: ## Run this project's own test suite (commands.gate from site.yml)
	@G=$$($(SITE) commands.gate 2>/dev/null); \
	if [ -z "$$G" ]; then echo "$(RED)✗ No commands.gate in site.yml$(RESET)"; exit 1; fi; \
	echo "$(BLUE)$$G$(RESET)"; eval "$$G"

doctor: ## Check required tools and SSH connectivity
	@echo "$(BLUE)Tools$(RESET)"
	@for c in ddev git rsync ssh python3; do \
		command -v $$c >/dev/null 2>&1 \
			&& printf "  ✅ %s\n" "$$c" \
			|| printf "  $(RED)❌ %s (required)$(RESET)\n" "$$c"; \
	done
	@python3 -c "import yaml" 2>/dev/null && echo "  ✅ PyYAML (scripts/site)" || echo "  $(RED)❌ PyYAML — scripts/site cannot read site.yml$(RESET)"
	@echo ""
	@echo "$(BLUE)Environments (from site.yml)$(RESET)"
	@for e in $$($(SITE) environments); do \
		HOST=$$($(SITE) environments.$$e.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
		P=$$($(SITE) environments.$$e.path); \
		B=$$($(SITE) environments.$$e.branch); \
		U=$$($(SITE) environments.$$e.url); \
		printf "  %-12s %-10s %s\n" "$$e" "$$B" "$$U"; \
		if ssh -qn -o ConnectTimeout=5 "$$HOST" "test -d $$P" 2>/dev/null; then \
			printf "               $(GREEN)path ok$(RESET)  %s\n" "$$P"; \
		else \
			printf "               $(RED)UNREACHABLE$(RESET) %s\n" "$$P"; \
		fi; \
	done
	@echo ""
	@echo "$(BLUE)Payload$(RESET)"
	@for p in $$($(SITE) deploy.payload); do \
		if [ -d "$(WEBROOT)/$$p" ]; then printf "  ✅ %s\n" "$$p"; \
		else printf "  $(RED)❌ %s missing locally$(RESET)\n" "$$p"; fi; \
	done

health: ## Fleet health: ledger, server drift, deploy guards, branch topology, patched files
	@git fetch --quiet origin 2>/dev/null || true
	@echo "$(BLUE)Ledger — is each environment running its branch head?$(RESET)"
	@DIR=$$($(SITE) deploy.state_dir); \
	for e in $$($(SITE) environments); do \
		H=$$($(SITE) environments.$$e.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
		B=$$($(SITE) environments.$$e.branch); \
		S=$$(ssh -qn "$$H" "cat $$DIR/$$e.json 2>/dev/null" | sed -n 's/.*"sha":"\([0-9a-f]*\)".*/\1/p'); \
		HD=$$(git rev-parse --verify --quiet "origin/$$B" || true); \
		if [ -z "$$S" ]; then printf "  $(YELLOW)%-12s never deployed with this tool$(RESET)\n" "$$e"; \
		elif [ "$$S" = "$$HD" ]; then printf "  $(GREEN)%-12s in sync$(RESET)   %s\n" "$$e" "$$B"; \
		else printf "  $(YELLOW)%-12s BEHIND$(RESET)    %s: running %.8s, head %.8s\n" "$$e" "$$B" "$$S" "$$HD"; fi; \
	done
	@echo ""
	@echo "$(BLUE)Drift — has anyone edited a server by hand?$(RESET)"
	@EXCL=""; for x in $$($(SITE) deploy.exclude 2>/dev/null); do EXCL="$$EXCL --exclude=$$x"; done; \
	for e in $$($(SITE) environments); do \
		H=$$($(SITE) environments.$$e.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
		R=$$($(SITE) environments.$$e.path); \
		B=$$($(SITE) environments.$$e.branch); \
		git rev-parse --verify --quiet "origin/$$B" >/dev/null || { printf "  $(YELLOW)%-12s no origin/%s$(RESET)\n" "$$e" "$$B"; continue; }; \
		PAY=$$($(SITE) deploy.payload 2>/dev/null); \
		if [ -z "$$PAY" ]; then printf "  $(YELLOW)%-12s n/a$(RESET)      no deploy.payload (transport: %s) — drift is only measurable for rsync\n" "$$e" "$$($(SITE) deploy.method 2>/dev/null || echo unknown)"; continue; fi; \
		TMP=$$(mktemp -d); CH=0; DEL=0; \
		git archive "origin/$$B" | tar -x -C "$$TMP" 2>/dev/null; \
		for pp in $$($(SITE) deploy.payload); do \
			[ -d "$$TMP/$(WEBROOT)/$$pp" ] || continue; \
			O=$$(rsync -az --delete -e "ssh -q" --dry-run --itemize-changes $$EXCL \
				"$$TMP/$(WEBROOT)/$$pp/" "$$H:$$R/$$pp/" 2>/dev/null); \
			CH=$$((CH+$$(printf '%s\n' "$$O" | grep -cE '^[<>]f.s'))); \
			DEL=$$((DEL+$$(printf '%s\n' "$$O" | grep -c '^\*deleting'))); \
		done; \
		rm -rf "$$TMP"; \
		if [ "$$CH" -eq 0 ] && [ "$$DEL" -eq 0 ]; then printf "  $(GREEN)%-12s clean$(RESET)\n" "$$e"; \
		else printf "  $(RED)%-12s DRIFT$(RESET)  %s files differ, %s would be deleted — someone edited the server, or the branch was never deployed\n" "$$e" "$$CH" "$$DEL"; fi; \
	done
	@echo ""
	@echo "$(BLUE)Deploy guards$(RESET)"
	@M=$$($(SITE) deploy.method 2>/dev/null); \
	if [ "$$M" = "rsync" ]; then \
		for g in /memory/ /tasks/; do \
			if $(SITE) deploy.exclude 2>/dev/null | grep -qx "$$g"; then printf "  $(GREEN)✅ %s excluded$(RESET)\n" "$$g"; \
			else printf "  $(RED)❌ %s NOT in deploy.exclude — agent notes would be published to the web root$(RESET)\n" "$$g"; fi; \
		done; \
	else \
		for g in memory tasks; do \
			if [ -f .gitignore ] && grep -qE "^/?$$g/?$$" .gitignore; then printf "  $(GREEN)✅ %s/ gitignored$(RESET)\n" "$$g"; \
			else printf "  $(RED)❌ %s/ not gitignored — a %s deploy carries it to the server$(RESET)\n" "$$g" "$$M"; fi; \
		done; \
	fi
	@echo ""
	@echo "$(BLUE)Branch topology$(RESET)"
	@if [ "$(HAS_PROD)" = "yes" ]; then \
		for b in $(BR_REVIEW) $(BR_INTEG); do \
			[ "$$b" = "$(BR_PROD)" ] && continue; \
			N=$$(git rev-list --count "origin/$(BR_PROD)" "^origin/$$b" 2>/dev/null || echo "?"); \
			if [ "$$N" = "0" ]; then printf "  $(GREEN)✅ %s contains %s$(RESET)\n" "$$b" "$(BR_PROD)"; \
			else printf "  $(RED)❌ %s is missing %s commits from %s — production work can be reverted$(RESET)\n" "$$b" "$$N" "$(BR_PROD)"; fi; \
		done; \
	fi
	@if [ "$(BR_REVIEW)" != "$(BR_INTEG)" ]; then \
		N=$$(git rev-list --count "origin/$(BR_REVIEW)" "^origin/$(BR_INTEG)" 2>/dev/null || echo "?"); \
		if [ "$$N" = "0" ]; then printf "  $(GREEN)✅ %s contains %s$(RESET)\n" "$(BR_INTEG)" "$(BR_REVIEW)"; \
		else printf "  $(YELLOW)⚠  %s is %s commits behind %s — merge it down after a promote$(RESET)\n" "$(BR_INTEG)" "$$N" "$(BR_REVIEW)"; fi; \
	fi
	@for b in $$(git branch --format='%(refname:short)' | grep -vE '^(master|main)$$'); do \
		git rev-parse --verify --quiet "origin/$$b" >/dev/null || printf "  $(YELLOW)⚠  %s exists only locally — push it or lose it$(RESET)\n" "$$b"; \
	done
	@echo ""
	@echo "$(BLUE)Patched files outside the payload$(RESET)"
	@if $(SITE) health.markers >/dev/null 2>&1; then \
		$(SITE) health.markers | while IFS='|' read -r mp needle; do \
			[ -n "$$mp" ] || continue; \
			for e in $$($(SITE) environments); do \
				H=$$($(SITE) environments.$$e.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
				R=$$($(SITE) environments.$$e.path); \
				N=$$(ssh -qn "$$H" "grep -c -- '$$needle' '$$R/$$mp' 2>/dev/null" | tr -dc '0-9'); \
				if [ "$${N:-0}" -gt 0 ]; then printf "  $(GREEN)%-12s ✅$(RESET) %s\n" "$$e" "$$mp"; \
				else printf "  $(RED)%-12s ❌ PATCH GONE$(RESET) %s — an update reverted it, re-apply\n" "$$e" "$$mp"; fi; \
			done; \
		done; \
	else \
		echo "  (none declared — add health.markers to site.yml for third-party files you patch)"; \
	fi

rollback: ## Redeploy the previously deployed commit (make rollback env=production)
	@ENV="$(env)"; \
	if [ -z "$$ENV" ]; then echo "$(RED)✗ Usage: make rollback env=<name>$(RESET)"; exit 1; fi; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	DIR=$$($(SITE) deploy.state_dir); \
	PREV=$$(ssh -qn "$$HOST" "tail -2 $$DIR/$$ENV.log 2>/dev/null | head -1" | awk '{print $$2}'); \
	if [ -z "$$PREV" ]; then \
		echo "$(RED)✗ No previous deploy recorded for $$ENV$(RESET)"; exit 1; fi; \
	echo "$(YELLOW)Rolling $$ENV back to $$PREV$(RESET)"; \
	git --no-pager log --oneline -1 "$$PREV" || { \
		echo "$(RED)✗ Commit $$PREV is not in this repository$(RESET)"; exit 1; }; \
	read -p "Type 'yes' to roll back: " reply; \
	if [ "$$reply" != "yes" ]; then echo "$(RED)✗ Cancelled$(RESET)"; exit 1; fi; \
	WT=$$(mktemp -d); \
	git worktree add --detach --quiet "$$WT" "$$PREV"; \
	REMOTE=$$($(SITE) environments.$$ENV.path); \
	EXCL=""; \
	for e in $$($(SITE) deploy.exclude); do EXCL="$$EXCL --exclude=$$e"; done; \
	for p in $$($(SITE) deploy.payload); do \
		[ -d "$$WT/$(WEBROOT)/$$p" ] || continue; \
		echo "$(BLUE)  → $$p$(RESET)"; \
		rsync -az --delete -e "ssh -q" $$EXCL "$$WT/$(WEBROOT)/$$p/" "$$HOST:$$REMOTE/$$p/" || exit 1; \
	done; \
	git worktree remove --force "$$WT"; \
	WHEN=$$(date -Iseconds); WHO=$$(git config user.name); \
	printf '%s %s %s %s\n' "$$WHEN" "$$PREV" "rollback" "$$WHO" \
		| ssh -q "$$HOST" "cat >> $$DIR/$$ENV.log"; \
	printf '{"sha":"%s","branch":"rollback","at":"%s","by":"%s"}\n' "$$PREV" "$$WHEN" "$$WHO" \
		| ssh -q "$$HOST" "cat > $$DIR/$$ENV.json"; \
	$(MAKE) --no-print-directory _deploy-opcache env=$$ENV; \
	echo "$(GREEN)✅ $$ENV rolled back to $$PREV$(RESET)"

# === OPTIONAL: REMOTE REPO WORKFLOW ===
# Uncomment these if you prefer using GitHub/GitLab instead of bundles

# deploy-remote: ## Deploy via GitHub (alternative to bundle)
# 	@echo "$(BLUE)Deploying via remote repository...$(RESET)"
# 	@make _ensure-clean-git
# 	@git push origin $(shell git branch --show-current)
# 	@ssh $(STAGING_HOST) "cd $(STAGING_PATH) && \
# 		git fetch origin && \
# 		git reset --hard origin/$(shell git branch --show-current) && \
# 		composer install --no-dev && \
# 		wp cache flush --path=$(WP_CORE)"
# 	@echo "$(GREEN)✅ Deployed via remote repo$(RESET)"

# push: ## Push to remote repository
# 	@git push origin $(shell git branch --show-current)
# 	@echo "$(GREEN)✅ Pushed to remote$(RESET)"

# pull: ## Pull from remote repository
# 	@git pull origin $(shell git branch --show-current)
# 	@echo "$(GREEN)✅ Pulled from remote$(RESET)"

# === INTERNAL HELPERS (DO NOT CALL DIRECTLY) ===

# Transport moves the files. Everything around it — gate, backup, stamp,
# ledger, rollback — is identical whatever the method is.
_deploy-transport:
	@M=$$($(SITE) deploy.method); \
	case "$$M" in \
		rsync)    $(MAKE) --no-print-directory _deploy-rsync env=$(env) dryrun="$(dryrun)";; \
		git-push) $(MAKE) --no-print-directory _deploy-gitpush env=$(env) dryrun="$(dryrun)";; \
		*) echo "$(RED)✗ Unknown deploy.method: $$M (expected rsync or git-push)$(RESET)"; exit 1;; \
	esac

# Ploi/Bedrock. A push alone does NOT deploy: Ploi may have no repository
# connected, and PHP-FPM often runs opcache.validate_timestamps=0, so a pull
# stays invisible until FPM is reloaded. Every step is required, in order.
_deploy-gitpush:
	@ENV="$(env)"; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	REMOTE=$$($(SITE) environments.$$ENV.path); \
	BRANCH=$$($(SITE) environments.$$ENV.branch); \
	if [ -n "$(dryrun)" ]; then \
		echo "$(YELLOW)  would: git push origin $$BRANCH$(RESET)"; \
		echo "$(YELLOW)  would: ssh $$HOST 'cd $$REMOTE && git pull --ff-only origin $$BRANCH'$(RESET)"; \
		$(SITE) deploy.post_deploy_hooks 2>/dev/null | while read -r c; do \
			[ -n "$$c" ] && echo "$(YELLOW)  would: ssh $$HOST 'cd $$REMOTE && $$c'$(RESET)"; \
		done; \
		exit 0; \
	fi; \
	echo "$(BLUE)  → push $$BRANCH$(RESET)"; \
	git push --quiet origin "$$BRANCH" || exit 1; \
	echo "$(BLUE)  → pull on $$ENV$(RESET)"; \
	ssh -qn "$$HOST" "cd $$REMOTE && git pull --ff-only origin $$BRANCH" || exit 1; \
	$(SITE) deploy.post_deploy_hooks 2>/dev/null | while read -r c; do \
		[ -z "$$c" ] && continue; \
		echo "$(BLUE)  → $$c$(RESET)"; \
		ssh -qn "$$HOST" "cd $$REMOTE && $$c" || exit 1; \
	done


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
	: "runs on Combell for server-to-server, this one runs here for local."; \
	: "Change both or one path silently breaks (ERROR 1227 on the views)."; \
	ssh -qn "$$HOST" "cd $$SRC && wp db export --path=wp --default-character-set=utf8mb4 --single-transaction --quick - | gzip" \
		| gunzip \
		| sed -E 's/DEFINER=[^ ]+ / /g; s/SQL SECURITY DEFINER/SQL SECURITY INVOKER/g' \
		> /tmp/vad-pull.sql || exit 1; \
	ddev import-db --file=/tmp/vad-pull.sql || { rm -f /tmp/vad-pull.sql; exit 1; }; \
	rm -f /tmp/vad-pull.sql; \
	echo "$(YELLOW)Rewriting URLs: $$SRC_URL → $$LOCAL_URL$(RESET)"; \
	ddev wp search-replace "$$SRC_URL" "$$LOCAL_URL" --all-tables --precise --skip-columns=guid --quiet || exit 1; \
	echo "$(YELLOW)Forcing mail simulation locally...$(RESET)"; \
	ddev wp eval '$$o = get_option("fluentmail-settings", array()); if (!is_array($$o)) { $$o = array(); } if (empty($$o["misc"]) || !is_array($$o["misc"])) { $$o["misc"] = array(); } $$o["misc"]["simulate_emails"] = "yes"; update_option("fluentmail-settings", $$o); echo "simulate_emails=yes";' || true; \
	echo ""; \
	echo "$(GREEN)✓ local database refreshed$(RESET)"; \
	echo "$(YELLOW)  transients left alone on purpose$(RESET)"

_pull-plugins:
	@ENV="$(env)"; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	SRC=$$($(SITE) environments.$$ENV.path); \
	EXCL=""; \
	for p in $$($(SITE) deploy.payload); do EXCL="$$EXCL --exclude=$$(basename $$p)/"; done; \
	echo "$(YELLOW)Mirroring third-party plugins from $$ENV (git-owned ones and netdust-lti excluded)...$(RESET)"; \
	rsync -az --delete -e "ssh -q" --exclude=netdust-lti/ $$EXCL \
		"$$HOST:$$SRC/$(CONTENT_DIR)/plugins/" $(WEBROOT)/$(CONTENT_DIR)/plugins/ || exit 1; \
	TEXCL=""; \
	for p in $$($(SITE) deploy.payload); do \
		case "$$p" in content/themes/*) TEXCL="$$TEXCL --exclude=$$(basename $$p)/";; esac; \
	done; \
	echo "$(YELLOW)Mirroring themes (payload themes excluded)...$(RESET)"; \
	rsync -az --delete -e "ssh -q" $$TEXCL "$$HOST:$$SRC/$(CONTENT_DIR)/themes/" $(WEBROOT)/$(CONTENT_DIR)/themes/ || exit 1; \
	echo "$(GREEN)✓ third-party plugins and themes match $$ENV$(RESET)"

_pull-uploads:
	@ENV="$(env)"; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	SRC=$$($(SITE) environments.$$ENV.path); \
	echo "$(YELLOW)Mirroring uploads from $$ENV (20GB, incremental)...$(RESET)"; \
	rsync -az --delete -e "ssh -q" --info=stats1 \
		"$$HOST:$$SRC/$(CONTENT_DIR)/uploads/" $(WEBROOT)/$(CONTENT_DIR)/uploads/ || exit 1; \
	echo "$(GREEN)✓ uploads mirrored$(RESET)"


_refuse-production:
	@ENV="$(env)"; \
	if [ -z "$$ENV" ]; then echo "$(RED)✗ Usage: env=<staging|development>$(RESET)"; exit 1; fi; \
	if [ "$$ENV" = "production" ]; then \
		echo "$(RED)✗ Refused: data moves backward only, never into production$(RESET)"; exit 1; \
	fi; \
	if [ -z "$$($(SITE) environments.$$ENV.path)" ]; then \
		echo "$(RED)✗ Unknown environment: $$ENV$(RESET)"; exit 1; \
	fi

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
	echo "$(YELLOW)Mirroring third-party plugins (git-owned ones and netdust-lti excluded)...$(RESET)"; \
	ssh -qn "$$HOST" "rsync -a --delete --exclude=netdust-lti/ $$EXCL $$SRC/$(CONTENT_DIR)/plugins/ $$DST/$(CONTENT_DIR)/plugins/" || exit 1; \
	TEXCL=""; \
	for p in $$($(SITE) deploy.payload); do \
		case "$$p" in content/themes/*) TEXCL="$$TEXCL --exclude=$$(basename $$p)/";; esac; \
	done; \
	echo "$(YELLOW)Mirroring themes (payload themes excluded)...$(RESET)"; \
	ssh -qn "$$HOST" "rsync -a --delete $$TEXCL $$SRC/$(CONTENT_DIR)/themes/ $$DST/$(CONTENT_DIR)/themes/" || exit 1; \
	echo "$(GREEN)✓ third-party plugins and themes mirrored (mu-plugins untouched)$(RESET)"


_deploy-stamp:
	@ENV="$(env)"; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	DIR=$$($(SITE) deploy.state_dir); \
	SHA=$$(git rev-parse HEAD); \
	BRANCH=$$(git branch --show-current); \
	WHEN=$$(date -Iseconds); \
	WHO=$$(git config user.name); \
	printf '{"sha":"%s","branch":"%s","at":"%s","by":"%s"}\n' "$$SHA" "$$BRANCH" "$$WHEN" "$$WHO" \
		| ssh -q "$$HOST" "mkdir -p $$DIR && cat > $$DIR/$$ENV.json"; \
	printf '%s %s %s %s\n' "$$WHEN" "$$SHA" "$$BRANCH" "$$WHO" \
		| ssh -q "$$HOST" "cat >> $$DIR/$$ENV.log"; \
	git tag -f "deployed/$$ENV" >/dev/null; \
	git push -f --quiet origin "deployed/$$ENV" 2>/dev/null || \
		echo "$(YELLOW)  (tag not pushed — no network?)$(RESET)"; \
	echo "$(GREEN)✓ stamped $$ENV @ $$(git rev-parse --short HEAD)$(RESET)"

_deploy-opcache:
	@ENV="$(env)"; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	REMOTE=$$($(SITE) environments.$$ENV.path); \
	URL=$$($(SITE) environments.$$ENV.url); \
	NAME=".opcache-$$(git rev-parse --short HEAD)-$$$$.php"; \
	echo '<?php opcache_reset(); echo "ok"; unlink(__FILE__);' \
		| ssh -q "$$HOST" "cat > $$REMOTE/$$NAME"; \
	curl -fsS --max-time 20 "$$URL/$$NAME" >/dev/null 2>&1 || true; \
	ssh -qn "$$HOST" "rm -f $$REMOTE/$$NAME"; \
	echo "$(GREEN)✓ opcache reset on $$ENV$(RESET)"


_deploy-confirm:
	@ENV="$(env)"; \
	if [ "$$($(SITE) environments.$$ENV.confirm)" != "true" ]; then exit 0; fi; \
	echo "$(RED)╔════════════════════════════════════════╗$(RESET)"; \
	echo "$(RED)║   DEPLOY TO $$ENV$(RESET)"; \
	echo "$(RED)║   $$($(SITE) environments.$$ENV.role)$(RESET)"; \
	echo "$(RED)╚════════════════════════════════════════╝$(RESET)"; \
	git --no-pager log --oneline "deployed/$$ENV..HEAD" 2>/dev/null | head -20 || true; \
	read -p "Type 'yes' to deploy: " reply; \
	if [ "$$reply" != "yes" ]; then echo "$(RED)✗ Cancelled$(RESET)"; exit 1; fi

_deploy-rsync:
	@ENV="$(env)"; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	REMOTE=$$($(SITE) environments.$$ENV.path); \
	EXCL=""; \
	for e in $$($(SITE) deploy.exclude); do EXCL="$$EXCL --exclude=$$e"; done; \
	for p in $$($(SITE) deploy.payload); do \
		if [ ! -d "$(WEBROOT)/$$p" ]; then \
			echo "$(RED)✗ Payload path missing locally: $(WEBROOT)/$$p$(RESET)"; exit 1; \
		fi; \
		echo "$(BLUE)  → $$p$(RESET)"; \
		rsync -az --delete -e "ssh -q" $(dryrun) --itemize-changes $$EXCL \
			"$(WEBROOT)/$$p/" "$$HOST:$$REMOTE/$$p/" || exit 1; \
	done

_backup-payload:
	@ENV="$(env)"; \
	HOST=$$($(SITE) environments.$$ENV.ssh_host 2>/dev/null || $(SITE) deploy.ssh_host); \
	REMOTE=$$($(SITE) environments.$$ENV.path); \
	DIR=$$($(SITE) deploy.state_dir); \
	STAMP=$$(date +%Y%m%d-%H%M%S); \
	PATHS=$$($(SITE) deploy.payload | tr '\n' ' '); \
	echo "$(YELLOW)Backing up $$ENV payload directories...$(RESET)"; \
	ARCHIVE="$$DIR/backups/$$ENV-$$STAMP.tar.gz"; \
	: "GNU tar exits 1 for warnings (a file changed while being read) and 2"; \
	: "for real errors. Treating any non-zero as failure aborts a ship over a"; \
	: "warning, so check the archive itself instead."; \
	ssh -qn "$$HOST" "mkdir -p $$DIR/backups && cd $$REMOTE && tar czf $$ARCHIVE $$PATHS 2>/dev/null; rc=\$$?; [ \$$rc -le 1 ] || exit \$$rc"; \
	SIZE=$$(ssh -qn "$$HOST" "stat -c %s $$ARCHIVE 2>/dev/null || echo 0"); \
	if [ "$$SIZE" -lt 1024 ]; then \
		echo "$(RED)✗ Payload backup missing or empty ($$SIZE bytes) — not deploying$(RESET)"; exit 1; \
	fi; \
	echo "$(GREEN)✓ payload backed up: $$ARCHIVE ($$(( SIZE / 1024 )) KB)$(RESET)"


_deploy-gate:
	@ENV="$(env)"; \
	if [ -z "$$ENV" ]; then \
		echo "$(RED)✗ Usage: make deploy env=<development|staging|production>$(RESET)"; \
		exit 1; \
	fi; \
	WANT=$$($(SITE) environments.$$ENV.branch 2>/dev/null); \
	if [ -z "$$WANT" ]; then \
		echo "$(RED)✗ Unknown environment: $$ENV$(RESET)"; \
		echo "$(YELLOW)Known: development, staging, production$(RESET)"; \
		exit 1; \
	fi; \
	HAVE=$$(git branch --show-current); \
	if [ "$$HAVE" != "$$WANT" ]; then \
		echo "$(RED)✗ $$ENV deploys from '$$WANT' — you are on '$$HAVE'$(RESET)"; \
		exit 1; \
	fi; \
	if [ -n "$$(git status --porcelain)" ]; then \
		echo "$(RED)✗ Uncommitted changes — nothing uncommitted reaches a server$(RESET)"; \
		git status --short; \
		exit 1; \
	fi; \
	git fetch --quiet origin "$$WANT" 2>/dev/null || true; \
	if ! git merge-base --is-ancestor HEAD "origin/$$WANT" 2>/dev/null; then \
		echo "$(RED)✗ HEAD is not on origin/$$WANT — push before deploying$(RESET)"; \
		exit 1; \
	fi; \
	echo "$(GREEN)✓ gate passed: $$ENV ← $$WANT @ $$(git rev-parse --short HEAD)$(RESET)"


_check-requirements:
	@command -v ddev >/dev/null 2>&1 || { echo "$(RED)❌ DDEV not installed$(RESET)"; exit 1; }
	@command -v git >/dev/null 2>&1 || { echo "$(RED)❌ Git not installed$(RESET)"; exit 1; }
	@command -v rsync >/dev/null 2>&1 || { echo "$(RED)❌ rsync not installed$(RESET)"; exit 1; }
	@command -v ssh >/dev/null 2>&1 || { echo "$(RED)❌ SSH not installed$(RESET)"; exit 1; }

_check-ddev:
	@if ! ddev describe >/dev/null 2>&1; then \
		echo "$(RED)❌ DDEV not running. Run 'make dev' first$(RESET)"; \
		exit 1; \
	fi

_ensure-safe-branch:
	@BRANCH=$$(git branch --show-current 2>/dev/null || echo "none"); \
	if [ "$$BRANCH" = "main" ] || [ "$$BRANCH" = "master" ]; then \
		echo "$(YELLOW)master is deploy-only — switching to develop...$(RESET)"; \
		git checkout $(BR_INTEG) 2>/dev/null || git checkout -b $(BR_INTEG); \
	elif [ "$$BRANCH" = "none" ]; then \
		git checkout $(BR_INTEG) 2>/dev/null || git checkout -b $(BR_INTEG); \
	fi

_ensure-clean-git:
	@if [ -n "$$(git status --porcelain)" ]; then \
		echo "$(RED)❌ You have uncommitted changes$(RESET)"; \
		echo "$(YELLOW)Run 'make save' first$(RESET)"; \
		exit 1; \
	fi

_backup-production:
	@echo "$(YELLOW)Backing up production...$(RESET)"
	@mkdir -p backups
	@TIMESTAMP=$$(date +%Y%m%d-%H%M%S); \
	if ! ssh $(PRODUCTION_HOST) "cd $(PRODUCTION_PATH) && \
		wp db export --path=$(WP_CORE) - | gzip" > backups/production-$$TIMESTAMP.sql.gz; then \
		echo "$(RED)❌ Failed to backup production database$(RESET)"; \
		exit 1; \
	fi; \
	echo "$(GREEN)✅ Production backed up: backups/production-$$TIMESTAMP.sql.gz$(RESET)"


