#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
env_file="$repo_root/.env.local"
env_example="$repo_root/.env.example"
required_packages=(
  git
  curl
  ca-certificates
  openssh-client
  sshpass
  rsync
  tar
  unzip
  jq
  python3
  python3-venv
  ripgrep
)
optional_tools=(
  make
  gcc
  g++
  pkg-config
  netcat
  lsof
  tree
  tmux
)

has_minio_mc() {
  command -v mc >/dev/null 2>&1 && mc --version 2>&1 | grep -q 'MinIO'
}

detect_minio_cli() {
  if [[ -n "${MINIO_CLIENT_BIN:-}" ]] && command -v "${MINIO_CLIENT_BIN}" >/dev/null 2>&1; then
    echo "${MINIO_CLIENT_BIN}"
    return 0
  fi
  if command -v mcli >/dev/null 2>&1; then
    echo "mcli"
    return 0
  fi
  if has_minio_mc; then
    echo "mc"
    return 0
  fi
  return 1
}

ensure_sshpass() {
  if command -v sshpass >/dev/null 2>&1; then
    return 0
  fi
  if command -v sudo >/dev/null 2>&1; then
    sudo apt-get update -y >/dev/null
    sudo apt-get install -y sshpass >/dev/null
  fi
}

ensure_required_packages() {
  local missing=()
  local pkg
  for pkg in "${required_packages[@]}"; do
    if ! dpkg -s "$pkg" >/dev/null 2>&1; then
      missing+=("$pkg")
    fi
  done
  if [[ ${#missing[@]} -eq 0 ]]; then
    return 0
  fi
  if command -v sudo >/dev/null 2>&1; then
    sudo apt-get update -y >/dev/null
    sudo apt-get install -y "${missing[@]}" >/dev/null
  else
    echo "Missing required packages: ${missing[*]}" >&2
  fi
}

check_optional_tools() {
  local missing=()
  local tool
  for tool in "${optional_tools[@]}"; do
    if ! command -v "$tool" >/dev/null 2>&1; then
      missing+=("$tool")
    fi
  done
  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "Optional tools not installed: ${missing[*]}" >&2
  fi
}

check_git_host_mapping() {
  local git_host="${GITEA_HOST:-git.compin.net}"
  if getent hosts "$git_host" >/dev/null 2>&1; then
    return 0
  fi
  echo "Warning: $git_host is not resolvable via current host lookup." >&2
}

check_git_ssh() {
  local git_host="${GITEA_HOST:-git.compin.net}"
  if command -v ssh >/dev/null 2>&1; then
    ssh -o BatchMode=yes -o StrictHostKeyChecking=no -T "git@${git_host}" >/dev/null 2>&1 || \
      echo "Warning: SSH auth to git@${git_host} is not ready yet." >&2
  fi
}

ensure_minio_cli() {
  if detect_minio_cli >/dev/null 2>&1; then
    return 0
  fi

  if command -v sudo >/dev/null 2>&1 && dpkg -s mc >/dev/null 2>&1; then
    sudo apt-get remove -y mc >/dev/null || true
  fi

  if command -v sudo >/dev/null 2>&1 && command -v curl >/dev/null 2>&1; then
    sudo curl -fsSL https://dl.min.io/client/mc/release/linux-amd64/mc -o /usr/local/bin/mc
    sudo chmod +x /usr/local/bin/mc
  fi
}

echo "Initializing repository workflow..."
bash "$repo_root/scripts/install_hooks.sh"

if [[ ! -f "$env_file" ]]; then
  cp "$env_example" "$env_file"
  cat >>"$env_file" <<'EOF'
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin123
EOF
  echo "Created .env.local with local MinIO defaults."
fi

set -a
source "$env_file"
set +a

ensure_required_packages
ensure_sshpass
ensure_minio_cli
check_optional_tools
check_git_host_mapping
check_git_ssh

if minio_cli="$(detect_minio_cli)"; then
  if ! "$minio_cli" alias list "${MINIO_ALIAS:-labminio}" >/dev/null 2>&1; then
    if [[ -n "${MINIO_ENDPOINT:-}" && -n "${MINIO_ACCESS_KEY:-}" && -n "${MINIO_SECRET_KEY:-}" ]]; then
      "$minio_cli" alias set "${MINIO_ALIAS}" "${MINIO_ENDPOINT}" "${MINIO_ACCESS_KEY}" "${MINIO_SECRET_KEY}" >/dev/null
      echo "Registered ${minio_cli} alias: ${MINIO_ALIAS} -> ${MINIO_ENDPOINT}"
    else
      echo "MinIO alias not registered: missing MINIO_ENDPOINT / MINIO_ACCESS_KEY / MINIO_SECRET_KEY in .env.local" >&2
    fi
  fi
else
  echo "MinIO client is unavailable after bootstrap. Install mcli/mc or ensure curl+sudo work." >&2
fi

cat <<'EOF'

Repository workflow initialized.

Required rules:
  1. Start from a Gitea issue.
  2. Work on a branch like feature/<issue>-<topic>.
  3. Use commit messages like [#123] short summary.
  4. Put formal outputs under results/issue-<issue>/.
  5. Publish formal evidence with bash scripts/publish_evidence.sh <issue>.
  6. Outputs outside results/issue-<issue>/ are not treated as formal evidence by default.

Local MinIO defaults:
  - alias: labminio
  - endpoint: http://192.168.0.5:9000
  - bucket: lab-evidence
  - prefix: repos
  - client: mcli or MinIO mc

Key files:
  - README.md
  - AGENTS.md
  - docs/spec.md
  - docs/workflow.md

EOF
