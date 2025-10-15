## Entrypoint & Quickstart — concise reference

This page documents the container entrypoint (`entrypoint.sh`) and the local quickstart helper (`scripts/quickstart.sh`). It's intended to be a short, actionable reference for developers and CI operators.

### Files
- `entrypoint.sh` — container entrypoint. Coordinates payload handling, preprocessing/processing, and copying artifacts from a temporary `WORK_DIR` to a `MAIN_DIR`.
- `scripts/quickstart.sh` — local helper that creates a Python venv, installs `pixi`, runs `pixi install`, and executes a sample preprocess using `tests/data/input.ini`.

---

### High-level behavior (entrypoint)
- Looks for a scheduler payload file at `${ARGS_DIR:-/args}/payload`.
- If present, extracts `simulation_id` and `run_id` using `scripts/extract_ids.py` and computes per-run folders under `WORK_DIR` (defaults to `/tmp/work`).
- Calls `scripts/payload_handler.py <payload.json> <save_dir>` to write a run-specific `input.ini` into the run `input` folder (the handler also prints an `export INPUT='...'` line for debugging).
- Runs one of the pipeline modes depending on `JOB_MODE`:
  - `preprocess` → `pixi run -- python -m gtpost.interface.preprocess <input.ini> <output_dir>`
  - `postprocess` / `process` → `pixi run -- python -m gtpost.interface.process <input_dir> <output_dir>`
- On success, copies artifacts from the run `WORK_DIR` into `MAIN_DIR` for preservation or downstream use.
- The script performs explicit error checks and exits with non-zero codes on failure.

### High-level behavior (quickstart)
- Creates and activates a local Python venv (defaults to `.venv`) and installs `pixi` command.
- Runs `pixi install` to populate the local pixi environment for the repository.
- Invokes sample preprocess using the `tests/data/input.ini` bundled in the repo and writes output to the chosen `OUT_DIR`.

---

### Requirements
- Docker (for running the container) OR a local Python 3.11+ interpreter to run `scripts/quickstart.sh`.
- Pixi (installed inside the container image by the Dockerfile, or installed by `scripts/quickstart.sh`).
- On the host: sufficient disk space and permissions for the `WORK_DIR` and `MAIN_DIR` mounts (e.g., `/tmp/gtpost_test/work`).
- If running in Docker, rebuild the image after edits that change `pyproject.toml` or pixi features: `docker build -t gtpost-local:dev .`.

Notes about pixi and container images
- Do NOT copy your host `.pixi` folder into the image. A `.dockerignore` is included to prevent this. If host `.pixi` is present in the build context it can cause relocation errors at runtime.
- Best practice for local Docker runs: build a self-contained image that runs `pixi install` at build time and *do not mount `/app`* at runtime. Mount only `WORK_DIR`, `MAIN_DIR`, and `ARGS_DIR`.

---

### Environment variables used by `entrypoint.sh`
- `JOB_MODE` — `preprocess` (default when running quickstart) or `postprocess` / `process`.
- `WORK_DIR` — base working directory inside the container (default: `/tmp/work`). Entrypoint creates per-run subfolders here.
- `MAIN_DIR` — final storage location where artifacts will be copied on success (default: `/tmp/main`).
- `ARGS_DIR` — where to look for the scheduler payload (default: `/args`).

Example runtime assignment (docker):

```bash
docker run --rm -it \
  -e JOB_MODE=preprocess \
  -e WORK_DIR=/tmp/work \
  -e ARGS_DIR=/args \
  -e MAIN_DIR=/tmp/main \
  -v ./tmp/gtpost_test/work:/tmp/work \
  -v ./tmp/gtpost_test/args:/args:ro \
  -v ./tmp/gtpost_test/main:/tmp/main \
  gtpost-local:dev
```

---

### Payload format (minimal)
The entrypoint expects a JSON file at `${ARGS_DIR}/payload`. Common keys:

```json
{

"simulation_id": "S123",

"run_id": "R001",

"ini_parameters": {

"template": {

"value": "River dominated delta"

},

"basinslope": {

"name": "Basin slope",

"value": 0.04,

"description": "This is the bed level slope between the coastline and the offshore model boundary."

},

"composition": {

"name": "Sediment classes",

"value": "fine-sand",

"description": "This is the grain size distribution (vol-%) of the fluvial sediment input and the initial bed composition. Coarse sand: 10% vc, 10% c, 15% m, 35% f, 20% vf, 10% mud; Medium sand: 5% vc, 5% c, 10% m, 35% f, 35% vf, 10% mud; Fine sand: 2% vc, 3% c, 5% m, 30% f, 45% vf, 15% mud; Very fine sand: 2% vc, 3% c, 5% m, 25% f, 35% vf, 30% mud; Coarse silt: 5% c, 5% m, 25% f, 35% vf, 15% mud A, 15% mud B."

},

"riverlength": {

"name": "River length",

"value": 100,

"description": "This is the number of cells between the landward model boundary and the coastline. This parameter is only for the use of the preprocessing scripts but is not editable."

},

"simstoptime": {

"name": "Simulation time",

"value": 320.5,

"description": "This is the total hydrodynamic simulation time of a model run."

},

"channelwidth": {

"name": "Channel width",

"value": 500,

"description": "This is the width of the river channel excluding the floodplains (not availalbe for the Roda and Sobrarbe templates)."

},

"subsidencesea": {

"name": "Subsidence at seaward model boundary",

"value": 10,

"description": "This is the amount by which the bed level at the seaward model boundary will be subsided by the end of the simulation (constant subsidence rate between 0 m and the chosen value). If this value coincides with the value chosen for the area between the landward model boundary and the coastline, a uniform subsidence for the whole model domain is applied. If the values differ, a spatially varying subsidence is applied based on a linear interpolation between both values."

},

"wavedirection": {

"name": "Mean wave direction relative to North",

"value": 0,

"description": "This is the mean wave direction according to the nautical convention (0 degrees = waves from the North/orthogonal to the coast)."

},

"waveheightfin": {

"name": "Final significant wave height",

"value": 0.5,

"description": "This is the final significant wave height applied to the model. If this value coincides with the value chosen for the initial significant wave height, a constant wave height is applied during the entire simulation. If the values differ, a time varying wave height is applied based on a linear interpolation between the values for the initial and the final wave heights."

},

"waveheightini": {

"name": "Initial significant wave height",

"value": 0.5,

"description": "This is the initial significant wave height applied to the model. If this value coincides with the value chosen for the final significant wave height, a constant wave height is applied during the entire simulation. If the values differ, a time varying wave height is applied based on a linear interpolation between the values for the initial and the final wave heights."

},

"outputinterval": {

"name": "Output interval",

"value": 1,

"description": "This is the output interval used for the map output (2D and 3D), observation point output and the profile output."

},

"subsidenceland": {

"name": "Subsidence between landward model boundary and coastline",

"value": 10,

"description": "This is the amount by which the bed level between the landward model boundary and the coastline will be subsided by the end of the simulation (constant subsidence rate between 0 m and the chosen value). If this value coincides with the value chosen for the seaward model boundary, a uniform subsidence for the whole model domain is applied. If the values differ, a spatially varying subsidence is applied based on a linear interpolation between both values."

},

"tidalamplitude": {

"name": "Tidal amplitude",

"value": 2,

"description": "This is the tidal amplitude at the offshore model boundary."

},

"riverdischargefin": {

"name": "Final river discharge per channel",

"value": 2000,

"description": "This is the final river discharge per channel (one channel in the case of River dominated delta, Gule Horn/Neslen and Roda; four channels in the case of Sobrarbe). If this value coincides with the value chosen for the initial river discharge, a constant discharge is applied during the entire simulation. If the values differ, a time varying river discharge is applied based on a linear interpolation between the values for the initial and the final river discharges."

},

"riverdischargeini": {

"name": "Initial river discharge per channel",

"value": 2000,

"description": "This is the initial river discharge per channel (one channel in the case of River dominated delta, Gule Horn/Neslen and Roda; four channels in the case of Sobrarbe). If this value coincides with the value chosen for the final river discharge, a constant discharge is applied during the entire simulation. If the values differ, a time varying river discharge is applied based on a linear interpolation between the values for the initial and the final river discharges."

}

}

}
```

- `simulation_id` / `simulationId` and `run_id` / `runId` are used to compute per-run folders.
- `ini_parameters` (or `iniParameters`) is a dict of INI sections and values; `payload_handler.py` converts this into a `input.ini` under the run `input` folder.

---

### Quick examples

Local quickstart (creates venv, installs pixi, runs sample preprocess):

```bash
./scripts/quickstart.sh /tmp/gtpost_preprocess_out
```

Build & run container (use baked image; do not mount `/app`):

```bash
mkdir -p ./tmp/gtpost_test/work ./tmp/gtpost_test/main ./tmp/gtpost_test/args
docker build --no-cache -t gtpost-local:dev .
docker run --rm -it \
  -e JOB_MODE=preprocess \
  -e WORK_DIR=/tmp/work \
  -e ARGS_DIR=/args \
  -e MAIN_DIR=/tmp/main \
  -v ./tmp/gtpost_test/work:/tmp/work \
  -v ./tmp/gtpost_test/args:/args:ro \
  -v ./tmp/gtpost_test/main:/tmp/main \
  gtpost-local:dev
```

If you mount the repository into the container (for development) mount it somewhere other than `/app` to avoid hiding the baked `/app/.pixi` created during build.

---

### Troubleshooting (common errors)
- Error: "The environment directory seems have to moved! Environments are non-relocatable" — Cause: host `.pixi` was copied into the image or you mounted a host `.pixi` at `/app/.pixi`. Fix: ensure `.pixi` is excluded from build context (`.dockerignore`) and rebuild the image; do not mount `/app` at runtime.
- Error: "python3: command not found" — Fix: rebuild the image so `pixi install` runs during `docker build`; for local quickstart, ensure a Python 3.11 interpreter is available on PATH.
- Error: `input.ini` not found / `PreProcess` missing `inidata` — Means payload had no `ini_parameters` or `payload_handler.py` failed to write `input.ini`. Check `/args/payload` and inspect `/tmp/work/<sim>/<run>/input/input.ini` on the host.

---

### Where to look for logs & output
- Entrypoint/stdout — container logs (visible in the terminal running `docker run`).
- `WORK_DIR` — intermediate per-run files (trim.nc, .sed, generated inputs). Useful for debugging.
- `MAIN_DIR` — final preserved artifacts after successful runs.
- `tests/` — contains a sample `tests/data/input.ini` you can use with `scripts/quickstart.sh`.

---
