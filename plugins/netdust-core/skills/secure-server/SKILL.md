---
name: secure-server
description: >
  Use when hardening a fresh Hetzner VPS provisioned by Ploi, OR when
  auditing an existing server for security drift. Triggers on "secure
  server", "harden server", "lock down VPS", "setup server security",
  "audit server security", "is my server secure", "security drift check",
  or when a new Ploi server is created. Covers SSH hardening (drop-in
  based, root disabled), fail2ban, UFW, unattended upgrades, service
  exposure review (memcached/MySQL/Redis binds, docker publish), and
  optional Tailscale private networking — while preserving Ploi
  deployment access and owner SSH access.
---

# Secure Hetzner VPS (Ploi-managed)

Harden a fresh Hetzner VPS that Ploi provisions, while keeping both Ploi's deployment user and the owner's SSH access intact. Also usable in **re-audit mode** against an existing server (see "Drift re-audit" at the end) — configuration drifts back over time; the 2026-07-03 netdust-web audit found root SSH re-allowed, memcached on `0.0.0.0`, and MySQL bound to `*`, all silently shielded by nothing but UFW.

## Prerequisites

- Root SSH access to the server (Ploi provides this initially)
- The server IP or hostname
- Owner's SSH public key

## Step 0: Gather Information

Ask the user these questions **one at a time**, waiting for each answer:

1. **Server:** "What's the server IP or SSH alias? (e.g., `root@203.0.113.10`)"
2. **Username:** "What admin username do you want? (This becomes the only user allowed to SSH in, besides `ploi`.)"
3. **SSH public key:** "Paste your SSH public key (or multiple keys, one per line)."
4. **Tailscale:** "Set up Tailscale for private network access? (yes/no)"
   - If yes: "Paste your Tailscale auth key. Generate one at https://login.tailscale.com/admin/settings/keys (use reusable if adding multiple devices)."

Once answers are collected, execute sections 1-10 in order via SSH. Substitute `<USERNAME>`, `<SSH_PUBLIC_KEY>`, `<SERVER>`, and `<TAILSCALE_AUTH_KEY>` accordingly. Skip section 9 if user said no to Tailscale.

## Execution

Run all commands on the remote server via SSH as root. Use `ssh <SERVER> 'commands'` or establish an interactive session.

**CRITICAL: Keep your current SSH session open until section 8 verification passes. If you lock yourself out, Ploi console access is the recovery path.**

### 1. System Baseline

```bash
apt update && apt upgrade -y
apt install -y fail2ban curl git vim ufw
```

### 2. Create Admin User

```bash
useradd -m -s /bin/bash -G sudo,adm <USERNAME>
chmod 750 /home/<USERNAME>
```

The `adm` group grants read access to `/var/log`.

### 3. SSH Key Setup

```bash
mkdir -p /home/<USERNAME>/.ssh
cat > /home/<USERNAME>/.ssh/authorized_keys << 'EOF'
<SSH_PUBLIC_KEY>
EOF
chmod 700 /home/<USERNAME>/.ssh
chmod 600 /home/<USERNAME>/.ssh/authorized_keys
chown -R <USERNAME>:<USERNAME> /home/<USERNAME>/.ssh
```

### 4. Passwordless Sudo

```bash
echo "<USERNAME> ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/<USERNAME>
chmod 440 /etc/sudoers.d/<USERNAME>
```

### 5. SSH Hardening (drop-in based — never overwrite sshd_config)

Do **not** `cat >` over `/etc/ssh/sshd_config`. A wholesale overwrite discards distro/Ploi settings, collides with openssh package updates (dpkg conffile prompts), and is how hardening silently drifts back later. Use a drop-in.

**5a. Confirm the include exists** (Ubuntu 22.04+ default, first line of `sshd_config`):

```bash
grep -q '^Include /etc/ssh/sshd_config.d/' /etc/ssh/sshd_config && echo include-ok
```

If missing (rare), add `Include /etc/ssh/sshd_config.d/*.conf` as the FIRST line.

**5b. Neutralize competing drop-ins.** sshd uses **first-obtained-wins** per keyword, and drop-ins are read in lexical order. Cloud images ship `50-cloud-init.conf` (often `PasswordAuthentication yes`) — a `99-` hardening file would LOSE to it. So: name ours `00-` and remove the cloud-init override:

```bash
ls /etc/ssh/sshd_config.d/
rm -f /etc/ssh/sshd_config.d/50-cloud-init.conf
```

**5c. Write the hardening drop-in** — global directives only, NO `Match` blocks here (see 5d for why):

```bash
cat > /etc/ssh/sshd_config.d/00-netdust-hardening.conf << 'EOF'
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
KbdInteractiveAuthentication no
PermitEmptyPasswords no
StrictModes yes

LoginGraceTime 30
MaxAuthTries 6
MaxSessions 5
ClientAliveInterval 300
ClientAliveCountMax 2

# Both Ploi deploy user and admin user. Add per-site users here when created.
AllowUsers ploi <USERNAME>

AllowAgentForwarding no
AllowTcpForwarding no
X11Forwarding no
LogLevel VERBOSE
EOF
```

**5d. TCP forwarding for the admin user only** — admin UIs (NocoDB, Directus, etc.) should be bound to `127.0.0.1` (section 8), and the sanctioned way to reach them is an SSH tunnel (`ssh -L`). So forwarding is off globally, on for `<USERNAME>`. `Match` blocks capture **every directive parsed after them** — a `Match` inside an early drop-in would swallow the other drop-ins and the rest of the main file (breaking e.g. `Subsystem`). So the Match block goes at the very END of the MAIN config:

```bash
grep -q 'netdust-match' /etc/ssh/sshd_config || cat >> /etc/ssh/sshd_config << 'EOF'

# netdust-match — keep at end of file
Match User <USERNAME>
    AllowTcpForwarding yes
EOF
```

**5e. Test BEFORE restarting, then verify effective values** — one typo in a heredoc is a lockout:

```bash
sshd -t && systemctl restart ssh
sshd -T | grep -iE '^(permitrootlogin|passwordauthentication|allowusers)'
sshd -T -C user=<USERNAME>,host=localhost,addr=127.0.0.1 | grep -i allowtcpforwarding   # expect: yes
sshd -T -C user=ploi,host=localhost,addr=127.0.0.1 | grep -i allowtcpforwarding          # expect: no
```

Expected: `permitrootlogin no`, `passwordauthentication no`, AllowUsers exactly `ploi <USERNAME>` (+ deliberate site users). **`AllowUsers` must not contain `root`.**

**IMPORTANT:** `AllowUsers` includes both `ploi` (Ploi's deploy user) and `<USERNAME>`. Removing `ploi` breaks Ploi deployments.

### 6. Fail2ban

```bash
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5
ignoreip = 127.0.0.1/8
backend  = systemd

[sshd]
enabled  = true
port     = ssh
filter   = sshd
maxretry = 3
bantime  = 24h
ignoreip = 127.0.0.1/8 ::1
EOF

systemctl enable fail2ban
systemctl restart fail2ban
fail2ban-client status sshd
```

If the user has a static home/office IP, add it to `ignoreip`. (`backend = systemd` reads the journal directly — works whether or not rsyslog writes `auth.log`.)

### 7. Unattended Security Upgrades

Do NOT run `dpkg-reconfigure` here — it opens an interactive TUI that hangs a scripted SSH session. The config files are the whole story:

```bash
apt install -y unattended-upgrades

cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

systemctl enable --now unattended-upgrades
systemctl status apt-daily-upgrade.timer --no-pager | head -3
```

### 8. Firewall (UFW) + service exposure review

**8a. Firewall:**

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw --force enable
```

If Tailscale is being set up, also run:
```bash
ufw allow in on tailscale0
```

**Note:** Ploi serves web traffic, so ports 80/443 must be open.

**8b. Service exposure review — the firewall must not be the only layer.** Ploi installs several services listening on all interfaces by default. List everything reachable on non-loopback addresses:

```bash
ss -tlnp | grep -vE '127\.0\.0\.1|\[::1\]'
```

Every line must be justified. Standard fixes:

- **memcached** — `/etc/memcached.conf`: set `-l 127.0.0.1`, then `systemctl restart memcached`. (Restart = cold object cache; brief slowdown on busy WP sites, do it in a quiet window.)
- **MySQL/MariaDB** — `/etc/mysql/mariadb.conf.d/50-server.cnf`: `bind-address = 127.0.0.1`, then `systemctl restart mariadb` (seconds of downtime for hosted sites). **Skip if Ploi's remote-database access feature is actively used** — it needs the wide bind + a UFW rule instead.
- **Redis** — `/etc/redis/redis.conf`: `bind 127.0.0.1 ::1` (usually already the default; verify).
- **Docker** — docker's iptables rules **bypass UFW entirely**. A container published as `-p 8080:80` is internet-reachable no matter what `ufw status` says. ALWAYS publish loopback-only: `-p 127.0.0.1:8080:80` (compose: `"127.0.0.1:8080:80"`), and reach admin UIs through an SSH tunnel or Tailscale.

**8c. Verify from OUTSIDE** (run on your laptop, not the server) — the only test that counts:

```bash
for p in 22 80 443 8080 8055 3306 6379 11211; do
  (timeout 3 bash -c "echo > /dev/tcp/<SERVER-IP>/$p" 2>/dev/null && echo "port $p: OPEN") || echo "port $p: closed/filtered"
done
```

Expected: ONLY 22, 80, 443 open.

### 9. Tailscale (skip if user said no)

```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up --authkey=<TAILSCALE_AUTH_KEY> --ssh
systemctl enable tailscaled
```

The `--ssh` flag enables Tailscale SSH — access the server over private network without exposing port 22 publicly.

After confirming Tailscale SSH works, **optionally** lock down public SSH:
```bash
ufw delete allow 22/tcp
ufw allow in on tailscale0 to any port 22 comment 'SSH via Tailscale only'
ufw reload
```

**Only do this after confirming Tailscale access works, or you will lock yourself out.**

## Verification Checklist

Run these after all steps complete:

```bash
systemctl status ssh
sshd -t
sshd -T | grep -iE '^(permitrootlogin|passwordauthentication)'   # both must be "no"
systemctl status fail2ban
fail2ban-client status sshd
ufw status verbose
ss -tlnp | grep -vE '127\.0\.0\.1|\[::1\]'                        # every line justified
id <USERNAME>
# If Tailscale:
tailscale status
```

Then verify in a **new terminal**:
```bash
ssh <USERNAME>@<server-ip>     # Must work
ssh root@<server-ip>            # Must be rejected
ssh -L 9999:127.0.0.1:80 <USERNAME>@<server-ip> true   # Tunnel must work (admin user)
```

Plus the external port probe from section 8c, run from your own machine.

## Drift re-audit (existing servers)

Trigger: "audit server security", "is <server> secure", periodic check, or before putting anything new on an old box. Read-only; report findings before changing anything. Run via SSH:

```bash
sudo sshd -T | grep -iE '^(permitrootlogin|passwordauthentication|allowusers|port) '   # root must be absent from allowusers
sudo ufw status verbose | head -15                                                     # default deny incoming?
systemctl is-active fail2ban && sudo fail2ban-client status sshd | grep -E 'Currently|Total'
cat /etc/apt/apt.conf.d/20auto-upgrades
sudo ss -tlnp | grep -vE '127\.0\.0\.1|\[::1\]'                                        # exposure review, section 8b
sudo docker ps --format '{{.Names}} -> {{.Ports}}' 2>/dev/null                          # every publish must say 127.0.0.1
apt list --upgradable 2>/dev/null | grep -c upgradable; [ -f /var/run/reboot-required ] && echo REBOOT-REQUIRED
```

…and the external port probe (8c) from another machine. Compare against this skill's expected end-state; each mismatch is a finding with a named fix from the sections above. Known drift patterns seen in this fleet: `PermitRootLogin` reverting via config overwrite, `AllowUsers root` creeping in, memcached/MySQL listening wide (Ploi defaults), a dev process started with `-a 0.0.0.0` by an agent.

## Common Mistakes

| Mistake | Consequence |
|---------|-------------|
| Omitting `ploi` from `AllowUsers` | Ploi deployments break silently |
| Overwriting `/etc/ssh/sshd_config` wholesale | Distro/Ploi settings lost; package updates conflict; hardening drifts back on the next tool that edits it |
| Naming the drop-in `99-*.conf` | Loses to `50-cloud-init.conf` — first-obtained wins, lexical read order |
| Putting a `Match` block in an early drop-in | Captures every directive parsed after it (other drop-ins + rest of main file); `Subsystem` under Match = broken config |
| Restarting ssh without `sshd -t` first | One heredoc typo = locked out |
| `AllowTcpForwarding no` with no admin `Match` exception | Blocks the SSH tunnels that are the sanctioned path to loopback-bound admin UIs |
| Publishing docker ports without `127.0.0.1:` | Docker bypasses UFW — container is internet-exposed despite "deny incoming" |
| Trusting `ufw status` instead of an external probe | iptables/docker interactions only show from outside |
| Closing SSH session before verifying new login | Locked out if config is wrong |
| Forgetting ports 80/443 in UFW | Web traffic blocked |
| Locking to Tailscale SSH before testing it | Locked out completely |
| Running `dpkg-reconfigure` in a scripted session | Interactive TUI hangs the SSH pipeline |
