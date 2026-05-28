<overview>
Generic sweep playbook. Loaded when shake-out detects a project that is neither WordPress nor Node.js. Covers HTTP services, CLI tools, file-processing scripts, and general application checks.

Adapt these checks to what was actually built. Skip sections that don't apply.
</overview>

<sweep_checklist>

<smoke_test>
**1. Smoke Test — Does it run?**

```bash
# Application starts without error
[start-command] 2>&1 | head -20
# Expected: No fatal errors, process stays alive (if daemon) or exits 0 (if CLI)

# If it's a service — is it listening?
curl -sI http://localhost:[port]/ | head -5
# or: ss -tlnp | grep [port]

# If it's a CLI tool — basic invocation
[command] --help
# Expected: Usage output, exit 0

# If it's a script — runs to completion
[script] [args] 2>&1
echo "Exit code: $?"
# Expected: exit 0
```
</smoke_test>

<http_endpoints>
**2. HTTP Endpoints (if applicable)**

```bash
# Each route responds
curl -s -w "\nHTTP %{http_code}\n" http://localhost:[port]/[route]

# POST/PUT with expected body
curl -s -X POST -H "Content-Type: application/json" \
  -d '[expected-body]' \
  http://localhost:[port]/[route]

# Bad input returns 4xx, not 5xx
curl -s -X POST -H "Content-Type: application/json" \
  -d '{}' \
  http://localhost:[port]/[route]

# Auth-protected routes reject anonymous
curl -s -w "\nHTTP %{http_code}\n" http://localhost:[port]/[protected-route]

# Headers and CORS (if relevant)
curl -sI -H "Origin: http://example.com" http://localhost:[port]/[route] | grep -i "access-control"
```
</http_endpoints>

<frontend_chrome>
**3. Frontend (chrome-devtools MCP)**

If the project serves any browser-accessible UI:

```
# Open the page
mcp__chrome-devtools__new_page  url: "http://localhost:[port]"

# JS errors in console
mcp__chrome-devtools__list_console_messages  level: "error"

# Critical elements present
mcp__chrome-devtools__evaluate_script  expression: "document.querySelector('[selector]') ? 'FOUND' : 'MISSING'"

# Screenshot for human review
mcp__chrome-devtools__take_screenshot
```
</frontend_chrome>

<filesystem>
**4. File System**

```bash
# Expected output files created
ls -la [output-path]
# Expected: Files exist with reasonable size

# Output content valid
file [output-file]
# Expected: Correct file type

# Directories writable
test -w [dir] && echo "WRITABLE" || echo "NOT WRITABLE"

# Config files exist and are well-formed
[validate-config-command]
```
</filesystem>

<database>
**5. Database (if applicable)**

```bash
# Connection works
[db-cli] -e "SELECT 1;"

# Expected tables exist
[db-cli] -e "SHOW TABLES;" | grep [expected-table]

# Expected data present
[db-cli] -e "SELECT COUNT(*) FROM [table];"

# Schema matches expectations
[db-cli] -e "DESCRIBE [table];"
```
</database>

<process_health>
**6. Process Health**

```bash
# Service running
ps aux | grep [process-name] | grep -v grep

# Memory reasonable
ps -o rss,vsz,comm -p [pid]

# No zombie processes
ps aux | grep [process-name] | grep 'Z'

# Logs clean
tail -50 [log-path] | grep -i "error\|fatal\|exception"
```
</process_health>

<error_handling>
**7. Error Handling**

```bash
# Bad input doesn't crash the process
[command] --invalid-flag 2>&1
echo "Exit code: $?"
# Expected: Non-zero exit, helpful error message, process doesn't hang

# Missing required config
env -u [REQUIRED_VAR] [command] 2>&1
# Expected: Clear error about missing config

# If service: still alive after bad requests
curl -sI http://localhost:[port]/ | head -1
```
</error_handling>

</sweep_checklist>

<manual_checklist_guidance>

After automated sweep, generate manual checks ONLY for:

1. Visual/UI verification (if applicable)
2. Flows requiring human judgment
3. External integrations that can't be tested locally
4. Performance perception
5. Cross-platform behavior (if relevant)

Keep to 5-10 items. Be specific to what was built.

</manual_checklist_guidance>
