# krisiserver — remote Ubuntu VPS (deployment target)

Personal VPS (Aruba/cloud.it), Ubuntu 24.04, 4 vCPU / 8 GB RAM / ~60 GB free.
This is the deployment target for bitch-stewie: the orchestrator (Flow
Manager) will run here as a docker compose stack and spawn Claude Code
instances via the SDK to fulfil tasks.

| | |
|---|---|
| Hostname | krisiserver |
| IPv4 | 194.182.86.101 |
| SSH user | `deploy` (key-only, passwordless sudo via `/etc/sudoers.d/deploy`) |
| SSH key | local `~/.ssh/id_ed25519` (pubkey comment `gitlab`) |
| Root login | **disabled** (`PermitRootLogin no`) — connect only as `deploy` |
| Password auth | **disabled** (`PasswordAuthentication no`) |
| Exposure policy | **nothing public** — all services bind `127.0.0.1`, access via SSH tunnel only |

## Connect

```bash
ssh deploy@194.182.86.101              # interactive
ssh deploy@194.182.86.101 '<command>'  # non-interactive (agents/scripts) — no prompts
ssh -L <port>:localhost:<port> deploy@194.182.86.101   # tunnel to a service
```

## Deployment

Full stack runs as docker compose from `docker/docker-compose.prod.yml`
(backend + worker + Postgres + Qdrant + Ollama + draw.io + frontend/nginx),
code pulled from `https://github.com/Kr1si/bitch-stewie` (public repo).
All published ports bind `127.0.0.1`.

From the local repo:

```bash
make deploy        # push main + git pull & compose up -d --build on the server
make deploy-logs   # tail stack logs
make deploy-ps     # stack status
make tunnel        # SSH tunnel: UI on http://localhost:3000, draw.io on 8080
```

- The frontend is built with `VITE_API_BASE=""`; nginx serves the SPA and
  proxies `/api` to the backend container — so the UI needs only the one
  tunnel port (3000). Diagram embeds additionally use `localhost:8080`
  (draw.io), hence the second forward in `make tunnel`.
- The backend image bundles Node 22 + the Claude Code CLI (the orchestrator
  spawns CC via the SDK); CC and the orchestrator both talk to the `ollama`
  container.
- **One-time after first start**: sign Ollama into the cloud account
  (`glm-5.2:cloud` relays through it):
  `sudo docker exec -it assistant-ollama ollama signin`
- Delegated repos live in `/home/deploy/projects` on the host, mounted at
  `/projects` in the backend and worker containers.
- Fresh databases — nothing migrated from the local dev machine.
- OpenHands was trialled here and **removed** (2026-07-10) — it couldn't act
  as the Flow Manager because it can't spawn real Claude Code instances; our
  orchestrator does this through the CC SDK.

Docker Engine 29.x is already installed (official Docker apt repo);
`deploy` is in the `docker` group.

## Hardening / security

- sshd hardening lives in **`/etc/ssh/sshd_config.d/99-hardening.conf`**
  (`PermitRootLogin no`, `PasswordAuthentication no`). Drop-in used because a
  routine `apt upgrade` of openssh-server once replaced the main
  `/etc/ssh/sshd_config` and silently re-enabled password auth. **After any
  big apt upgrade, re-verify:**
  ```bash
  sudo sshd -T | grep -E '^(permitrootlogin|passwordauthentication)'
  ```
- Fail2ban: jail config in `/etc/fail2ban/jail.local` — `[sshd]` enabled,
  `backend = systemd`, `maxretry = 5`, `findtime = 10m`, `bantime = 1w`.
  - Status: `sudo fail2ban-client status sshd`
  - Manual ban/unban: `sudo fail2ban-client set sshd banip <IP>` / `unbanip <IP>`

## Gotchas

- **Aruba web console mangles pasted multi-line scripts** (inserts literal
  newlines into wrapped lines). Never paste scripts there — pipe via SSH
  instead: `cat script.sh | ssh deploy@194.182.86.101 'bash -s'`.
- After an OS reinstall the host key changes; clear the stale entry with
  `ssh-keygen -R 194.182.86.101`.
- Docker may need `sudo` in non-login SSH sessions (`deploy` is in the
  `docker` group, but group membership only applies to fresh login sessions).
- A newer kernel (6.8.0-134) was installed during an apt upgrade but the
  server hasn't been rebooted onto it yet — reboot at a convenient moment.
