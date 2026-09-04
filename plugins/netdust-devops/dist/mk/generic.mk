# ─────────────────────────────────────────────────────────────────────────────
# mk/generic.mk — no local loop, no data ops. The flow, deploy, ledger and
# health verbs from Makefile.netdust are all this stack gets.
#
# Also the fallback when STACK names a file that does not exist.
# Vendored by netdust-devops. Do not edit in a project.
# ─────────────────────────────────────────────────────────────────────────────

_help-stack:
	@echo "$(YELLOW)LOCAL$(RESET)        (stack: $(STACK) — no local-loop verbs)"
	@echo ""

_status-stack:
	@:

_doctor-stack:
	@:

# ship refuses rather than backing up nothing. A project with genuinely no
# server-side state says so in site.yml; it is never assumed.
_backup-data:
	@if [ "$$($(SITE) deploy.skip_data_backup 2>/dev/null)" = "true" ]; then \
		echo "$(YELLOW)⚠  no server-side data to back up (deploy.skip_data_backup: true)$(RESET)"; \
	else \
		echo "$(RED)✗ stack '$(STACK)' defines no data backup, and ship refuses to back up nothing$(RESET)"; \
		echo "$(YELLOW)  Set deploy.skip_data_backup: true in site.yml if this project keeps no$(RESET)"; \
		echo "$(YELLOW)  server-side state, or add a _backup-data recipe to mk/$(STACK).mk.$(RESET)"; \
		exit 1; \
	fi

.PHONY: _help-stack _status-stack _doctor-stack _backup-data
