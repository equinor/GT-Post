[![SCM Compliance](https://scm-compliance-api.radix.equinor.com/repos/equinor/88107a7f-e19e-4ec7-8478-c38c9eaf1ca3/badge)](https://scm-compliance-api.radix.equinor.com/repos/equinor/88107a7f-e19e-4ec7-8478-c38c9eaf1ca3/badge)

# GT-post - Postprocessing of Delft3D-Geotool models

## Overview

GT-Post provides preprocessing and postprocessing tools for Delft3D-Geotool simulation models. It runs as a containerized service that can be orchestrated by Radix.

## Container Entrypoint

The container uses `entrypoint.sh` to coordinate job execution. It supports three job modes controlled by the `JOB_MODE` environment variable.

### Job Modes

| Mode | Description | Input | Output |
|------|-------------|-------|--------|
| `preprocess` | Generates Delft3D input files from templates | Payload JSON with `ini_parameters` | `main_dir/orch-{id}/preprocess/` |
| `process` | Runs during simulation (incremental processing) | `main_dir/orch-{id}/simulation/` | Same directory (in-place) |
| `postprocess` | Runs after simulation completes | `main_dir/orch-{id}/simulation/` | Same directory (in-place) |

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `JOB_MODE` | `postprocess` | Job mode: `preprocess`, `process`, or `postprocess` |
| `WORK_DIR` | `./tmp/work` | Temporary working directory |
| `MAIN_DIR` | `./tmp/main` | Final storage location for artifacts |
| `ARGS_FOLDER` | `./tmp/args` | Directory containing the payload JSON file |

### Payload Format

The entrypoint expects a JSON payload file at `${ARGS_FOLDER}/payload`:

```json
{
  "orchestration_id": "S123",
  "run_id": "R001",
  "ini_parameters": {
    "template": { "value": "River_dominated_delta" },
    "basinslope": { "value": 0.04 },
    "simstoptime": { "value": 320.5 }
  }
}
```

- `orchestration_id` (or `orchestrationId`) — used to build folder paths
- `run_id` (or `runId`) — used for preprocess work directory naming
- `ini_parameters` (or `iniParameters`) — converted to `input.ini` for preprocessing

### Directory Structure

After running jobs, the following structure is created:

```
main_dir/
└── orch-{orchestration_id}/
    ├── preprocess/
    │   ├── input/      # Input files (including input.ini)
    │   └── output/     # Generated Delft3D files
    └── simulation/     # Simulation output (used by process/postprocess)
```

### Docker Usage

```bash
# Build the image
docker build -t gtpost:latest .

# Run preprocess
docker run --rm \
  -e JOB_MODE=preprocess \
  -e WORK_DIR=/tmp/work \
  -e MAIN_DIR=/tmp/main \
  -e ARGS_FOLDER=/args \
  -v ./work:/tmp/work \
  -v ./main:/tmp/main \
  -v ./args:/args:ro \
  gtpost:latest

# Run postprocess (after simulation has written to main_dir/orch-{id}/simulation/)
docker run --rm \
  -e JOB_MODE=postprocess \
  -e MAIN_DIR=/tmp/main \
  -e ARGS_FOLDER=/args \
  -v ./main:/tmp/main \
  -v ./args:/args:ro \
  gtpost:latest
```

### Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 2 | Failed to extract IDs from payload |
| 3 | Payload handler failed |
| 4 | Failed to copy input artifacts |
| 5 | Failed to copy output artifacts |
| 6 | Process mode missing orchestration_id |
| 7 | Postprocess mode missing orchestration_id |
| 8 | Unknown JOB_MODE |

## CI/CD

This repository uses GitHub Actions for CI and container image publishing. See `docs/ci-cd.md` for full details (tests, release-please integration, and the reusable build-and-publish workflow).

