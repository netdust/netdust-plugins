<overview>
Node.js / Bun sweep playbook. Loaded when shake-out detects a Node.js or Bun project without WordPress indicators.
</overview>

<prerequisites>
```bash
# Can the project build?
npm run build 2>&1 | tail -20
# or: bun run build

# Dependencies intact?
ls node_modules/.package-lock.json 2>/dev/null || echo "node_modules may need reinstall"
```
</prerequisites>

<sweep_checklist>

<smoke_test>
**1. Smoke Test**

```bash
# Does it start without crashing?
timeout 10 node [entry-point] 2>&1 | head -20
# Expected: No uncaught exceptions, process stays alive

# If server — is the port listening?
curl -sI http://localhost:[port]/ | head -5

# If CLI tool — does help work?
node [entry-point] --help
# Expected: Usage output, exit 0

# Check for unhandled promise rejections
node -e "process.on('unhandledRejection', (r) => { console.error('UNHANDLED:', r); process.exit(1); }); require('./[entry-point]');"
```
</smoke_test>

<core_functionality>
**2. Core Functionality**

For each primary feature the build created:

```bash
# Run the main operation
node [entry-point] [args]
# Capture stdout, stderr, exit code

# Verify output format (if JSON expected)
node [entry-point] [args] | node -e "
  let data = '';
  process.stdin.on('data', d => data += d);
  process.stdin.on('end', () => {
    try { JSON.parse(data); console.log('VALID JSON'); }
    catch(e) { console.log('INVALID JSON:', e.message); }
  });
"
```
</core_functionality>

<api_endpoints>
**3. API Endpoints (if HTTP server)**

```bash
# Each route responds correctly
curl -s -w "\n%{http_code}" http://localhost:[port]/[route]

# POST with expected body
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"key": "value"}' \
  http://localhost:[port]/[route]

# Bad input returns 400, not 500
curl -s -X POST -H "Content-Type: application/json" \
  -d '{}' \
  http://localhost:[port]/[route]
# Expected: 4xx with error message

# Auth-required routes reject anonymous
curl -s -w "\n%{http_code}" http://localhost:[port]/[protected-route]
# Expected: 401 or 403
```
</api_endpoints>

<frontend_chrome>
**4. Frontend (chrome-devtools MCP)**

If the project serves HTML/UI:

```
# Open the app
mcp__chrome-devtools__new_page  url: "http://localhost:[port]"

# Check for JS errors
mcp__chrome-devtools__list_console_messages  level: "error"

# Critical elements render
mcp__chrome-devtools__evaluate_script  expression: "document.querySelector('[selector]') ? 'FOUND' : 'MISSING'"

# Forms work
mcp__chrome-devtools__fill  selector: "[input-selector]"  value: "test value"
mcp__chrome-devtools__click  selector: "[submit-selector]"
mcp__chrome-devtools__evaluate_script  expression: "document.querySelector('[result-selector]')?.textContent || 'NO RESULT'"

# Screenshot for human review
mcp__chrome-devtools__take_screenshot
```
</frontend_chrome>

<environment_config>
**5. Environment & Config**

```bash
# Required env vars present
node -e "
  const required = ['API_KEY', 'DATABASE_URL'];
  const missing = required.filter(k => !process.env[k]);
  console.log(missing.length ? 'MISSING: ' + missing.join(', ') : 'ALL SET');
"

# Config files exist and parse
node -e "
  try { require('./config'); console.log('CONFIG OK'); }
  catch(e) { console.log('CONFIG ERROR:', e.message); }
"
```
</environment_config>

<external_dependencies>
**6. External Dependencies**

```bash
# Database connection (if applicable)
node -e "
  const db = require('./db');
  db.query('SELECT 1').then(() => console.log('DB OK')).catch(e => console.log('DB FAIL:', e.message));
"

# External API reachable (if applicable)
curl -sI https://[external-api-url] | head -5

# File system access
node -e "
  const fs = require('fs');
  const dir = './[output-dir]';
  console.log(fs.existsSync(dir) ? 'DIR EXISTS' : 'DIR MISSING');
  try { fs.accessSync(dir, fs.constants.W_OK); console.log('WRITABLE'); }
  catch { console.log('NOT WRITABLE'); }
"
```
</external_dependencies>

<error_handling>
**7. Error Handling**

```bash
# Malformed requests (if HTTP server)
curl -s -X POST http://localhost:[port]/[route] -d "not json"
# Expected: Graceful error, not crash

# Missing required fields
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"wrong": "fields"}' \
  http://localhost:[port]/[route]

# Process still alive after errors
curl -sI http://localhost:[port]/ | head -1
```
</error_handling>

</sweep_checklist>

<manual_checklist_guidance>

After automated sweep, generate manual checks ONLY for:

1. Visual output verification (if UI exists)
2. Interactive flows requiring human judgment
3. External service integration that can't be tested programmatically
4. Performance feel (is it fast enough?)

Keep to 5-10 items. Be specific to what was built.

</manual_checklist_guidance>
