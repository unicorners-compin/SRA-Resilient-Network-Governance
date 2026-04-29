# Workflow

## Goal

Use one lightweight workflow to connect:

- code changes in Gitea
- evidence artifacts in MinIO
- Codex-driven development
- automatic evidence scanning

The primary linkage is:

- issue number
- branch name
- commit SHA
- fixed result directory location

## Standard Flow

1. Create or select a Gitea issue.
2. Create a working branch named after the issue.
3. Develop normally on that branch.
4. Commit with the issue number.
5. If the work produces artifacts, write them under `results/issue-<issue>/`.
6. Publish formal evidence with the repository script.
7. Open or update the PR.

## Branch Naming

- `feature/<issue>-<topic>`
- `fix/<issue>-<topic>`
- `exp/<issue>-<topic>`

Examples:

- `feature/177-srv6-policy`
- `fix/42-parser-bug`
- `exp/88-dpdk-throughput`

## Commit Naming

Required:

```text
[#<issue>] short summary
```

Examples:

```text
[#177] fix policy parser
[#42] add dpdk perf probe
```

## Result Directory

If work produces outputs, use:

```text
results/issue-<issue>/
```

Examples:

```text
results/issue-177/
results/issue-177/README.md
results/issue-177/artifacts/summary.json
results/issue-177/figures/plot.png
results/issue-177/logs/run.log
```

Recommended minimum structure:

```text
results/issue-<issue>/
results/issue-<issue>/README.md
results/issue-<issue>/artifacts/
results/issue-<issue>/figures/
results/issue-<issue>/logs/
```

Not every task needs every subdirectory, but Codex should prefer these locations instead of dropping many unrelated files directly in the issue root.

The `README.md` in that directory should briefly explain:

- what was run
- what the key output files are
- what the result means

Formal evidence is only recognized by default when it is stored under:

```text
results/issue-<issue>/
```

If outputs are written outside that location, they should be treated as temporary or exploratory unless the project explicitly defines another collection rule.

## Evidence Collection

This template assumes evidence collection is standardized.

The default publication rule is:

- source directory:
  - `results/issue-<issue>/`
- MinIO alias:
  - `labminio`
- MinIO endpoint:
  - `http://192.168.0.5:9000`
- MinIO bucket:
  - `lab-evidence`
- MinIO prefix root:
  - `repos/`
- target prefix:
  - `lab-evidence/repos/<repo>/issues/<issue>/`

The default publication command is:

```bash
bash scripts/publish_evidence.sh <issue>
```

That script is the default boundary between:

- local formal evidence
- MinIO publication
- later `msg` notification or audit

Codex should prefer this script over handcrafting custom `mc cp` commands.

The system can later scan:

- current repository
- current branch
- current commit
- `results/issue-<issue>/`

and associate published evidence with repo, commit, and issue.

## Message Use

Use `msg` when a human needs to know about:

- a formal result
- a review request
- a completion event

Do not use `msg` for routine low-value progress noise.

## Standard Directories

Use these directories consistently:

- `docs/`: design and project documentation
- `src/`: source code
- `tests/`: test code and validation logic
- `scripts/`: developer and operations scripts
- `configs/`: config files and experiment parameters
- `results/`: generated issue-scoped outputs
- `issues/`: local issue snapshots and backups
- `paper/`: references, notes, and figures
- `data/`: small checked-in sample data
- `third_party/`: vendored external material

Codex should prefer these standard directories over inventing new top-level folders.

## Enforcement

Local:

- `.githooks/commit-msg`

Remote:

- `.gitea/workflows/validate.yml`

Codex:

- follows `AGENTS.md`
