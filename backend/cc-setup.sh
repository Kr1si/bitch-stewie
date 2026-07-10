#!/bin/sh
# Build-time provisioning of the Claude Code runtime used by delegated
# instances (spawned via the SDK by the orchestrator). Runs in the image build.
set -eu

# Commits CC makes in delegated repos need an identity; mounted repos are
# owned by the host user, so trust all paths.
git config --global user.name  "bitch-stewie"
git config --global user.email "assistant@krisiserver"
git config --global --add safe.directory '*'
git config --global init.defaultBranch main

# Plugins for delegated sessions. The runner passes every subdir of $ENABLED
# that has a .claude-plugin/plugin.json via the SDK plugins= option — plugin
# installs at user scope are invisible to sessions running with
# setting_sources=["project"], so this is the only mechanism that works.
ROOT=/opt/cc-plugins
ENABLED=$ROOT/enabled
mkdir -p "$ENABLED"

git clone --depth 1 https://github.com/affaan-m/ECC.git "$ROOT/ecc-repo"
git clone --depth 1 https://github.com/anthropics/claude-plugins-official.git "$ROOT/official-repo"

link_plugin() {
    # $1 = repo to search, $2 = plugin name (matched against plugin.json)
    manifest=$(grep -rls "\"name\": \"$2\"" --include=plugin.json "$1" | head -1)
    if [ -z "$manifest" ]; then
        echo "WARN: plugin $2 not found under $1 - skipping" >&2
        return 0
    fi
    ln -s "$(dirname "$(dirname "$manifest")")" "$ENABLED/$2"
}

link_plugin "$ROOT/ecc-repo" ecc
link_plugin "$ROOT/official-repo" frontend-design
link_plugin "$ROOT/official-repo" claude-code-setup

echo "enabled CC plugins:"
ls -l "$ENABLED"
