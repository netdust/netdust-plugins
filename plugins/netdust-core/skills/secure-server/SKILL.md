---
name: secure-server
description: >
  Use when hardening a fresh Hetzner VPS provisioned by Ploi.
  Triggers on "secure server", "harden server", "lock down VPS",
  "setup server security", or when a new Ploi server is created.
  Covers SSH hardening, fail2ban, UFW, unattended upgrades, and
  optional Tailscale private networking — while preserving Ploi
  deployment access and owner SSH access.
---

# Secure Hetzner VPS (Ploi-managed)

Harden a fresh Hetzner VPS that Ploi provisions, while keeping both Ploi's deployment user and the owner's SSH access intact.

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

Once answers are collected, execute sections 1-9 in order via SSH. Substitute `<USERNAME>`, `<SSH_PUBLIC_KEY>`, `<SERVER>`, and `<TAILSCALE_AUTH_KEY>` accordingly. Skip section 8 if user said no to Tailscale.

## Execution

Run all commands on the remote server via SSH as root. Use `ssh <SERVER> 'commands'` or establish an interactive session.

**CRITICAL: Keep your current SSH session open until section 7 verification passes. If you lock yourself out, Ploi console access is the recovery path.**

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

### 5. SSH Hardening

```bash
cat > /etc/ssh/sshd_config << 'EOF'
PermitRootLogin no
PasswordAuthentication no
PubkeyAuthentication yes
KbdInteractiveAuthentication no
PermitEmptyPasswords no
StrictModes yes

LoginGraceTime 30
MaxAuthTries 10
MaxSessions 5
ClientAliveInterval 300
ClientAliveCountMax 2

# Both Ploi deploy user and admin user
AllowUsers ploi <USERNAME>

AllowAgentForwarding no
AllowTcpForwarding no
X11Forwarding no
PrintMotd no
LogLevel VERBOSE
UsePAM yes

Subsystem sftp /usr/lib/openssh/sftp-server
EOF

systemctl restart ssh
```

**IMPORTANT:** `AllowUsers` includes both `ploi` (Ploi's deploy user) and `<USERNAME>`. Removing `ploi` breaks Ploi deployments.

### 6. Fail2ban

```bash
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime  = 1h
findtime = 10m
maxretry = 5
ignoreip = 127.0.0.1/8

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
```

If the user has a static home/office IP, add it to `ignoreip`.

### 7. Unattended Security Upgrades

```bash
apt install -y unattended-upgrades
dpkg-reconfigure --priority=low unattended-upgrades

cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF
```

### 8. Firewall (UFW)

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
systemctl status fail2ban
fail2ban-client status sshd
ufw status verbose
id <USERNAME>
# If Tailscale:
tailscale status
```

Then verify in a **new terminal**:
```bash
ssh <USERNAME>@<server-ip>     # Must work
ssh root@<server-ip>            # Must be rejected
```

## Post-Setup: Update SSH Config

Add to the user's `~/.ssh/config`:

```
Host <site>-server
    HostName <server-ip-or-tailscale-ip>
    User <USERNAME>
    IdentityFile ~/.ssh/id_ed25519
```

This follows the project's SSH pattern (e.g., `ploi-staging`).

## Common Mistakes

| Mistake | Consequence |
|---------|-------------|
| Omitting `ploi` from `AllowUsers` | Ploi deployments break silently |
| Closing SSH session before verifying new login | Locked out if config is wrong |
| Forgetting ports 80/443 in UFW | Web traffic blocked |
| Locking to Tailscale SSH before testing it | Locked out completely |
| Running `dpkg-reconfigure` non-interactively | Unattended upgrades not properly enabled |
