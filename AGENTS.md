# AGENTS.md

This repository follows a Codex-first internal workflow based on:

- `Gitea` for issues, branches, commits, and pull requests
- fixed `results/` directories for experiment artifacts
- automatic evidence collection into MinIO and daily audit

## Default Codex Skills

When working in this repository, Codex should treat these skills as the default operating model:

- `gitea-flow` for issue / branch / commit / PR workflow
- `evidence-publish` for formal evidence under `results/issue-*` and MinIO publication
- `team-msg` for formal notifications, `@user` / `@team`, and traceable delivery
- `gemini-advisor` for high-difficulty external technical consultation when needed

Repository copies of these skill definitions are kept under:

- `docs/codex-skills/`

## Required Repository Layout

The repository should keep these top-level directories:

- `docs/`
- `src/`
- `tests/`
- `scripts/`
- `configs/`
- `results/`
- `issues/`
- `paper/`
- `data/`
- `third_party/`

Codex should preserve this layout and place new files in the correct directory.

## Required Workflow

1. Work must begin from a Gitea issue.
2. Create a branch named after that issue.
3. Keep all related code changes on that branch.
4. Commit with the issue number in the commit message.
5. If the work produces experiment or benchmark artifacts, write them under `results/issue-<issue>/`.
6. Open or update the PR.

## Required Git Rules

- Branches should follow one of:
  - `feature/<issue>-<topic>`
  - `fix/<issue>-<topic>`
  - `exp/<issue>-<topic>`
- All non-merge commits must include:
  - `[#<issue>]`
- Preferred commit message format:
  - `[#123] short summary`

## Result Directory Rules

- Put generated outputs under:
  - `results/issue-<issue>/`
- Formal test outputs, benchmark outputs, experiment outputs, generated analysis artifacts, and script result files must be placed under `results/issue-<issue>/`.
- Each result directory should contain a short `README.md` that explains:
  - what was run
  - what the main output files are
  - what the result means
- Recommended minimum structure for a formal result directory:
  - `results/issue-<issue>/README.md`
  - `results/issue-<issue>/artifacts/` for main generated outputs
  - `results/issue-<issue>/figures/` for plots, screenshots, and diagrams when applicable
  - `results/issue-<issue>/logs/` for logs when applicable
- Codex should prefer placing generated files into `artifacts/`, `figures/`, or `logs/` instead of dropping many unrelated files directly in `results/issue-<issue>/`.
- Outputs outside `results/issue-<issue>/` are not treated as formal evidence by default.
- Do not manually invent MinIO object paths.
- Do not manually maintain external evidence indexes.
- Use the repository publish script as the only default publication entrypoint:
  - `bash scripts/publish_evidence.sh <issue>`
- Default MinIO publication rules are:
  - client: `mcli` or MinIO `mc`
  - alias: `labminio`
  - endpoint: `http://192.168.0.5:9000`
  - bucket: `lab-evidence`
  - prefix root: `repos/<repo>/issues/<issue>/`
  - source directory: `results/issue-<issue>/`
- Codex should not guess or invent alternative MinIO paths unless the repository explicitly overrides them in committed documentation or configuration.

## Directory Rules

- `docs/`
  - Put project specifications, architecture, workflow, and decisions here.
  - Do not put raw experiment outputs here.
- `src/`
  - Put maintained source code here.
  - Do not put throwaway scripts or generated files here.
- `tests/`
  - Put test code, regression checks, and validation scripts here.
  - Do not mix production source into this directory.
- `scripts/`
  - Put operational helpers, setup scripts, automation, and tooling entrypoints here.
  - Keep scripts focused and callable from the command line.
- `configs/`
  - Put configuration templates, experiment parameters, and runtime settings here.
  - Do not hardcode machine-local secrets into committed config files.
- `results/`
  - Put issue-scoped outputs here only.
  - Use `results/issue-<issue>/`.
  - Each meaningful result directory should contain a short `README.md`.
  - Prefer subdirectories such as `artifacts/`, `figures/`, and `logs/` inside each issue result directory.
- `issues/`
  - Put local backups, exported issue notes, and offline issue snapshots here.
  - Gitea remains the primary issue system.
- `paper/`
  - Put reading notes, references, figures, and writing materials here.
  - Do not use this directory as a dump for unrelated PDFs.
- `data/`
  - Put small sample datasets, metadata, or checked-in reference data here.
  - Large generated outputs belong in `results/`, not `data/`.
- `third_party/`
  - Put vendored external code, imported assets, or pinned third-party material here.
  - Keep provenance clear.

## Pull Request Rules

- PR titles should contain the issue number.
- PR descriptions should mention the result directory when code changes produce artifacts.
- Do not merge issue-driven work that lacks the issue number in commit history.

## Message Rules

Codex may use `msg` when notification is part of the task outcome.

Codex should send `msg` for:

- formal result publication
- review or verification requests
- task completion notifications when someone needs to know immediately
- evidence publication that points reviewers to `results/issue-<issue>/`

Codex should not send `msg` for:

- every small edit
- routine intermediate progress that is already visible in Git history
- duplicate notifications with no new decision, result, or action request

When publishing formal evidence, Codex should prefer the repository publication script and then notify relevant users or teams with `msg`, instead of manually constructing ad hoc MinIO links.

## What Codex Should Do

- Read the current branch name before making changes.
- Infer the active issue number from the branch and preserve it in commits.
- Prefer small, reviewable commits.
- If the task produces outputs, write them into `results/issue-<issue>/`.
- Add or update `results/issue-<issue>/README.md` when artifacts are meaningful.
- Treat `results/issue-<issue>/` as the only default location for formal evidence.
- Use `bash scripts/publish_evidence.sh <issue>` as the default way to publish formal evidence to MinIO.
- Use `msg` only when the task outcome requires human notification, review, or confirmation.
- Put new files into the correct standard directory instead of creating ad hoc top-level folders.
- Update `docs/spec.md` or `docs/architecture.md` when a change materially affects requirements or design.
- Do not bypass local hooks or CI checks.

## What Codex Must Not Do

- Do not create issue-driven commits without `[#<issue>]`.
- Do not write artifacts outside `results/` unless the project explicitly requires it.
- Do not assume outputs outside `results/issue-<issue>/` will be scanned, uploaded, or audited as formal evidence.
- Do not handcraft MinIO publication targets when `scripts/publish_evidence.sh` exists.
- Do not spam `msg` with low-signal updates.
- Do not create random top-level directories when an existing standard directory fits.
- Do not rewrite branch naming conventions.
- Do not add unrelated formatting-only changes unless explicitly requested.
