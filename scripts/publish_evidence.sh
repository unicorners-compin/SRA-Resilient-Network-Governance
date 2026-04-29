#!/usr/bin/env bash
set -euo pipefail

issue="${1:-}"
shift || true

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
env_file="$repo_root/.env.local"

if [[ -f "$env_file" ]]; then
  set -a
  source "$env_file"
  set +a
fi

detect_minio_cli() {
  if [[ -n "${MINIO_CLIENT_BIN:-}" ]] && command -v "${MINIO_CLIENT_BIN}" >/dev/null 2>&1; then
    echo "${MINIO_CLIENT_BIN}"
    return 0
  fi
  if command -v mcli >/dev/null 2>&1; then
    echo "mcli"
    return 0
  fi
  if command -v mc >/dev/null 2>&1 && mc --version 2>&1 | grep -q 'MinIO'; then
    echo "mc"
    return 0
  fi
  return 1
}

if [[ -z "$issue" ]]; then
  echo "usage: bash scripts/publish_evidence.sh <issue> [--notify <user-or-@team>]..." >&2
  exit 1
fi

if [[ ! "$issue" =~ ^[0-9]+$ ]]; then
  echo "invalid issue number: $issue" >&2
  exit 1
fi

repo_name="$(basename "$repo_root")"
result_dir="$repo_root/results/issue-$issue"
minio_alias="${MINIO_ALIAS:-labminio}"
minio_bucket="${MINIO_BUCKET:-lab-evidence}"
minio_prefix="${MINIO_PREFIX:-repos}"
target="${minio_alias}/${minio_bucket}/${minio_prefix}/${repo_name}/issues/${issue}"

notify_targets=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --notify)
      [[ $# -ge 2 ]] || { echo "missing value for --notify" >&2; exit 1; }
      notify_targets+=("$2")
      shift 2
      ;;
    *)
      echo "unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ ! -d "$result_dir" ]]; then
  echo "missing result directory: $result_dir" >&2
  exit 1
fi

if [[ ! -f "$result_dir/README.md" ]]; then
  echo "missing required result README: $result_dir/README.md" >&2
  exit 1
fi

if ! minio_cli="$(detect_minio_cli)"; then
  echo "no MinIO client found (expected mcli or MinIO mc)" >&2
  exit 1
fi

if ! "$minio_cli" alias list "$minio_alias" >/dev/null 2>&1; then
  echo "unknown MinIO alias: $minio_alias" >&2
  exit 1
fi

current_branch="$(git -C "$repo_root" branch --show-current 2>/dev/null || true)"
current_commit="$(git -C "$repo_root" rev-parse HEAD 2>/dev/null || true)"

"$minio_cli" cp --recursive "$result_dir" "$target"

echo "published evidence"
echo "repo:   $repo_name"
echo "issue:  $issue"
echo "branch: ${current_branch:-"-"}"
echo "commit: ${current_commit:-"-"}"
echo "local:  $result_dir"
echo "minio:  $target"

if [[ ${#notify_targets[@]} -gt 0 ]]; then
  body=$(
    cat <<EOF
formal evidence published
repo: $repo_name
issue: #$issue
branch: ${current_branch:-"-"}
commit: ${current_commit:-"-"}
result: $result_dir
minio: $target
EOF
  )
  msg send "${notify_targets[@]}" -b "$body" --link evidence="$target"
fi
