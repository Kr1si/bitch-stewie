---
name: krisiserver
description: Connect to and manage krisiserver (194.182.86.101), the remote Ubuntu VPS where bitch-stewie is deployed. Use when a task involves the remote server, deployment, SSH access, tunnels, fail2ban, or the docker stack running there.
---

# krisiserver operations

Full reference: `docs/krisiserver.md` in this repo — read it first for
anything non-trivial.

## Quick facts

- **Host**: `194.182.86.101` (Ubuntu 24.04, 4 vCPU / 8 GB RAM)
- **User**: `deploy` — key-only auth (local `~/.ssh/id_ed25519`), NOPASSWD sudo
- **Root SSH and password auth are disabled by design** — never try
  `ssh root@...`; a "Permission denied (publickey)" for root is expected,
  not a bug.
- **Nothing is exposed publicly.** All services bind `127.0.0.1`; access is
  SSH-tunnel-only. Never publish a port on `0.0.0.0` without explicit user
  approval.

## Commands

```bash
# run a command remotely (non-interactive, no prompts)
ssh deploy@194.182.86.101 '<command>'

# tunnel a service to your local machine
ssh -L <port>:localhost:<port> deploy@194.182.86.101

# pipe a multi-line script (NEVER paste scripts into the Aruba web console —
# it mangles line wraps)
cat script.sh | ssh deploy@194.182.86.101 'bash -s'
```

## Rules

1. Prefix docker commands with `sudo` in non-login SSH sessions.
2. After any large `apt upgrade`, verify sshd hardening survived:
   `sudo sshd -T | grep -E '^(permitrootlogin|passwordauthentication)'`
   (both must be `no`; the drop-in is `/etc/ssh/sshd_config.d/99-hardening.conf`).
3. Fail2ban jail `sshd` is active (`bantime = 1w`). Check with
   `sudo fail2ban-client status sshd` before assuming a connectivity problem
   is network-related — you may have banned yourself.
4. If the host key changes unexpectedly, stop and tell the user — unless
   they just reinstalled the OS (`ssh-keygen -R 194.182.86.101` clears it).
