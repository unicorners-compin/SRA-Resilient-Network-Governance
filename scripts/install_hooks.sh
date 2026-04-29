#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
git config core.hooksPath "$repo_root/.githooks"
chmod +x "$repo_root/.githooks/commit-msg"
echo "Installed git hooks from $repo_root/.githooks"
