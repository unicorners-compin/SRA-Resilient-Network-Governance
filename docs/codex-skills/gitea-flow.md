# gitea-flow

Use this workflow when repository work follows the local Gitea issue/branch/commit/PR model.

Core rules:

- start formal work from a Gitea issue
- use branches like:
  - `feature/<issue>-<topic>`
  - `fix/<issue>-<topic>`
  - `exp/<issue>-<topic>`
- use commits like:
  - `[#123] short summary`
- do not work directly on `main` for formal issue-driven changes

If work produces formal outputs:

- place them under `results/issue-<issue>/`
- publish them with the repository evidence script

If humans need to know:

- notify them through `msg`
