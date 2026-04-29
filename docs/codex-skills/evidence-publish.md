# evidence-publish

Use this workflow for formal evidence publication.

Core rules:

- formal evidence is only recognized by default under:
  - `results/issue-<issue>/`
- preferred publication entry:
  - `bash scripts/publish_evidence.sh <issue>`

Default MinIO rules:

- alias: `labminio`
- endpoint: `http://192.168.0.5:9000`
- bucket: `lab-evidence`
- prefix root: `repos`
- target shape:
  - `labminio/lab-evidence/repos/<repo>/issues/<issue>/`

Recommended minimum structure:

- `results/issue-<issue>/README.md`
- `results/issue-<issue>/artifacts/`
- `results/issue-<issue>/figures/`
- `results/issue-<issue>/logs/`
