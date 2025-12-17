#!/usr/bin/env bash

# Source pixi shell hook if present so pixi-managed environment is available
[[ -f /shell-hook ]] && source /shell-hook

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
JOB_MODE="${JOB_MODE:-postprocess}"       # 'preprocess', 'process', or 'postprocess'
WORK_DIR="${WORK_DIR:-./tmp/work}"
MAIN_DIR="${MAIN_DIR:-./tmp/main}"        # Final storage location
ARGS_FOLDER="${ARGS_FOLDER:-./tmp/args}"
PAYLOAD_FILE="${ARGS_FOLDER}/payload"

# Default paths (may be overridden by payload)
WORK_INPUT_DIR="${WORK_DIR%/}/input"
WORK_OUTPUT_DIR="${WORK_DIR%/}/output"
MAIN_INPUT_DIR="${MAIN_DIR%/}/input"
MAIN_OUTPUT_DIR="${MAIN_DIR%/}/output"
SIM_DIR=""  # Simulation directory for process/postprocess modes

# -----------------------------------------------------------------------------
# Helper functions
# -----------------------------------------------------------------------------
cleanup_dirs() {
  echo "Removing created dirs to avoid partial data retention."
  rm -rf "${WORK_INPUT_DIR}" "${WORK_OUTPUT_DIR}" "${MAIN_INPUT_DIR}" "${MAIN_OUTPUT_DIR}"
}

fail() {
  echo "ERROR: $1" >&2
  ${2:-false} && cleanup_dirs
  exit "${3:-1}"
}

# -----------------------------------------------------------------------------
# Payload processing (optional)
# -----------------------------------------------------------------------------
if [[ -f "${PAYLOAD_FILE}" ]]; then
  echo "Found payload JSON: ${PAYLOAD_FILE}"

  # Extract ORCH_ID and RUN_ID
  if ! extract_out=$(pixi exec python /app/scripts/extract_ids.py "${PAYLOAD_FILE}" 2>&1); then
    fail "extract_ids.py failed: ${extract_out}" false 2
  fi
  read -r ORCH_ID RUN_ID <<<"${extract_out}"

  # Compute paths from payload IDs
  if [[ -n "${ORCH_ID}" ]]; then
    BASE_ORCH="orch-${ORCH_ID}"
    BASE_RUN="run-${RUN_ID}"
    
    # Simulation directory (used by process/postprocess)
    SIM_DIR="${MAIN_DIR%/}/${BASE_ORCH}/simulation"
    
    # Preprocess uses work dirs and copies to main
    WORK_INPUT_DIR="${WORK_DIR%/}/${BASE_ORCH}/${BASE_RUN}/input"
    WORK_OUTPUT_DIR="${WORK_DIR%/}/${BASE_ORCH}/${BASE_RUN}/output"
    MAIN_INPUT_DIR="${MAIN_DIR%/}/${BASE_ORCH}/preprocess/input"
    MAIN_OUTPUT_DIR="${MAIN_DIR%/}/${BASE_ORCH}/preprocess/output"
    
    echo "Computed paths: BASE_ORCH=${BASE_ORCH}, SIM_DIR=${SIM_DIR}"
  fi

  # For preprocess: create work dirs and write input.ini
  if [[ "${JOB_MODE}" == "preprocess" ]]; then
    mkdir -p "${WORK_INPUT_DIR}" "${WORK_OUTPUT_DIR}"
    if ! pixi exec python /app/scripts/payload_handler.py "${PAYLOAD_FILE}" "${WORK_INPUT_DIR}"; then
      rm -rf "${WORK_INPUT_DIR}" "${WORK_OUTPUT_DIR}"
      fail "payload_handler failed for payload=${PAYLOAD_FILE}" false 3
    fi
  fi
fi

# -----------------------------------------------------------------------------
# Job execution
# -----------------------------------------------------------------------------
case "${JOB_MODE}" in
  preprocess)
    INI_FILE="${INI_FILE:-${WORK_INPUT_DIR%/}/input.ini}"
    echo "Running preprocess: ini=${INI_FILE}, output=${WORK_OUTPUT_DIR}"
    if ! pixi run python -m gtpost.interface.preprocess "${INI_FILE}" "${WORK_OUTPUT_DIR}"; then
      rc=$?
      fail "preprocess failed with exit code ${rc}" true ${rc}
    fi
    
    # Copy artifacts to main directory
    echo "Preprocess completed — copying artifacts to main dir"
    mkdir -p "${MAIN_INPUT_DIR}" "${MAIN_OUTPUT_DIR}"
    cp -a "${WORK_INPUT_DIR}/." "${MAIN_INPUT_DIR}/" || fail "failed to copy input" true 4
    cp -a "${WORK_OUTPUT_DIR}/." "${MAIN_OUTPUT_DIR}/" || fail "failed to copy output" true 5
    echo "Artifacts copied to: ${MAIN_INPUT_DIR} ${MAIN_OUTPUT_DIR}"
    ;;
    
  process)
    # Process runs on simulation output (while simulation is running)
    # Uses SIM_DIR as both input and output
    if [[ -z "${SIM_DIR}" ]]; then
      fail "process mode requires orchestration_id in payload to determine simulation directory" false 6
    fi
    echo "Running process: dir=${SIM_DIR} (in-place)"
    if ! pixi run python -m gtpost.interface.process "${SIM_DIR}" "${SIM_DIR}"; then
      rc=$?
      fail "process failed with exit code ${rc}" false ${rc}
    fi
    echo "Process completed"
    ;;
    
  postprocess)
    # Postprocess runs on simulation output (after simulation completes)
    # Uses SIM_DIR as both input and output
    if [[ -z "${SIM_DIR}" ]]; then
      fail "postprocess mode requires orchestration_id in payload to determine simulation directory" false 7
    fi
    echo "Running postprocess: dir=${SIM_DIR} (in-place)"
    if ! pixi run python -m gtpost.interface.postprocess "${SIM_DIR}" "${SIM_DIR}"; then
      rc=$?
      fail "postprocess failed with exit code ${rc}" false ${rc}
    fi
    echo "Postprocess completed"
    ;;
    
  *)
    fail "Unknown JOB_MODE='${JOB_MODE}'. Valid modes: preprocess, process, postprocess" false 8
    ;;
esac
