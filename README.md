# Compin Workflow Template

This repository is a template for projects that use:

- `Gitea` for code, issues, and pull requests
- `MinIO` for evidence artifacts
- `msg` for internal notification and audit delivery
- Codex as the primary execution agent for day-to-day development

## First Step After Clone

Run this immediately after cloning:

```bash
bash bootstrap.sh
```

This will:

- install the local git hooks
- print the core workflow rules
- make local commit checks active before the first commit
- create `.env.local` with local MinIO defaults
- ensure `sshpass` is available
- replace the wrong Ubuntu `mc` package when needed
- register the `labminio` alias for the MinIO client

## Quick Start

1. Create an issue in Gitea.
2. Create a branch:

```bash
git checkout -b feature/123-routing-fix
```

3. Work normally on that branch.

4. Commit using the required format:

```bash
git commit -m "[#123] fix route validation"
```

5. If the task produces outputs, write them under:

```bash
results/issue-123/
```

Add a short summary file when needed:

```bash
results/issue-123/README.md
```

6. Publish formal evidence:

```bash
bash scripts/publish_evidence.sh 123
```

7. Open a PR in Gitea.

## Install Hooks

```bash
bash scripts/install_hooks.sh
```

## Repository Layout

- `AGENTS.md`: Codex-facing workflow rules
- `docs/workflow.md`: human-readable workflow guide
- `.githooks/commit-msg`: local commit message validator
- `.gitea/workflows/validate.yml`: server-side workflow validation
- `docs/`: specifications, architecture, workflow, design decisions
- `src/`: maintained source code
- `tests/`: tests and validation
- `scripts/`: automation and operational scripts
- `configs/`: configuration and parameter files
- `results/`: issue-scoped outputs and experiment artifacts
- `issues/`: local issue snapshots and backups
- `paper/`: references, notes, and figures
- `data/`: small checked-in datasets and metadata
- `third_party/`: vendored dependencies or imported assets

## Required Commit Format

```text
[#<issue>] short summary
```

Example:

```text
[#42] add dpdk forwarding check
```

## Result Convention

If work produces experiment, benchmark, or generated artifacts, place them under:

```text
results/issue-<issue>/
```

Example:

```text
results/issue-42/
results/issue-42/README.md
results/issue-42/artifacts/throughput.csv
results/issue-42/figures/plot.png
results/issue-42/logs/run.log
```

Recommended minimum structure:

```text
results/issue-<issue>/
results/issue-<issue>/README.md
results/issue-<issue>/artifacts/
results/issue-<issue>/figures/
results/issue-<issue>/logs/
```

Use only the subdirectories that make sense for the task, but keep `README.md` at the top of the issue result directory.

Formal evidence is only recognized by default when it is stored under:

```text
results/issue-<issue>/
```

Outputs written elsewhere may exist for temporary exploration, but they are not considered formal evidence for automatic collection, MinIO publishing, or audit.

This template assumes your internal system will later:

- scan `results/`
- infer the active issue from branch and commit history
- associate artifacts with repo, branch, commit, and issue
- publish evidence to MinIO automatically

## Default MinIO Publication Rule

This template defines one default publication target so Codex does not need to guess:

- MinIO alias: `labminio`
- MinIO endpoint: `http://192.168.0.5:9000`
- MinIO bucket: `lab-evidence`
- MinIO prefix root: `repos/`
- Source directory: `results/issue-<issue>/`
- Target prefix: `lab-evidence/repos/<repo>/issues/<issue>/`

Default publication should go through:

```bash
bash scripts/publish_evidence.sh <issue>
```

Do not handcraft ad hoc MinIO paths when this script exists.

## Message Convention

`msg` should be used for:

- formal result publication
- review requests
- completion notifications that need human attention

It should not be used for noisy low-signal progress chatter.

## Initial Files

The template includes these starter files:

- `docs/spec.md`
- `docs/architecture.md`
- `docs/workflow.md`
- `docs/decisions.md`
- `results/.gitkeep`
- `issues/.gitkeep`
- `paper/refs/.gitkeep`
- `paper/notes/.gitkeep`
- `paper/figures/.gitkeep`
- `data/samples/.gitkeep`
