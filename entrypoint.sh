#!/usr/bin/env bash
# Enable Bash 'strict' mode for safety in container entrypoints:
#  -u : treat unset variables as an error and exit
#  -o pipefail : cause a pipeline to fail if any command in it fails
set -u -o pipefail

# Source pixi shell hook if present so pixi-managed environment is available
if [ -f /shell-hook ]; then
  # shellcheck disable=SC1091
  source /shell-hook
fi

# Defaults
JOB_MODE="${JOB_MODE:-postprocess}"    # 'preprocess' or 'postprocess' or 'process'
WORK_DIR="${WORK_DIR:-./tmp/work}"
MAIN_DIR="${MAIN_DIR:-./tmp/main}"      # If preprocess/process/postprocess scripts succeed, results will be moved from WORK_DIR to MAIN_DIR
ARGS_DIR="${ARGS_DIR:-./tmp/args}"

# Initialize variables that may be referenced later to avoid errors with 'set -u'
# can run even when no payload is provided.
SIM_ID=""
RUN_ID=""
extract_out=""
WORK_INPUT_DIR="./${WORK_DIR%/}/input"
WORK_OUTPUT_DIR="${WORK_DIR%/}/output"
MAIN_INPUT_DIR="${MAIN_DIR%/}/input"
MAIN_OUTPUT_DIR="${MAIN_DIR%/}/output"
JOB_RC=""

## Radix payload placement
PAYLOAD_FILE="${ARGS_DIR}/payload"

if [ -f "${PAYLOAD_FILE}" ]; then
  echo "Found payload JSON: ${PAYLOAD_FILE}"
  # Extract SIM_ID and RUN_ID (fail fast if the extractor script errors)
  extract_out=""
  if ! extract_out=$(pixi exec python /app/scripts/extract_ids.py "${PAYLOAD_FILE}" 2>&1); then
    echo "ERROR: extract_ids.py failed for payload=${PAYLOAD_FILE}:" >&2
    echo "${extract_out}" >&2
    exit 2
  fi
  # parse the two tokens from extractor stdout
  read -r SIM_ID RUN_ID <<<"${extract_out}"
  if [ -n "${SIM_ID}" ] && [ -n "${RUN_ID}" ]; then
    # Normalize names as requested (prefix sim- / run-)
    BASE_SIM="sim-${SIM_ID}"
    BASE_RUN="run-${RUN_ID}"
    WORK_INPUT_DIR="${WORK_DIR%/}/${BASE_SIM}/${BASE_RUN}/input"
    WORK_OUTPUT_DIR="${WORK_DIR%/}/${BASE_SIM}/${BASE_RUN}/output"
    MAIN_INPUT_DIR="${MAIN_DIR%/}/${BASE_SIM}/${JOB_MODE}/input"
    MAIN_OUTPUT_DIR="${MAIN_DIR%/}/${BASE_SIM}/${JOB_MODE}/output"

    echo "ENTRYPOINT: computed WORK_INPUT_DIR=${WORK_INPUT_DIR}, WORK_OUTPUT_DIR=${WORK_OUTPUT_DIR} from payload"
  fi
  # Run the payload handler (writes ini if present) and export assignments; pass WORK_DIR as base
  echo "Payload-derived WORK_INPUT_DIR=${WORK_INPUT_DIR} WORK_OUTPUT_DIR=${WORK_OUTPUT_DIR}"
  # Ensure the payload-provided dirs exist (input and output)
  mkdir -p "${WORK_INPUT_DIR}" "${WORK_OUTPUT_DIR}"
  # Call payload_handler with positional args: <payload.json> <save_dir>
  # If payload handling fails we should terminate the job with an error.
  if ! pixi exec python /app/scripts/payload_handler.py "${PAYLOAD_FILE}" "${WORK_INPUT_DIR}"; then
    echo "ERROR: payload_handler failed for payload=${PAYLOAD_FILE}, save_dir=${WORK_INPUT_DIR}" >&2
    echo "Removing created input/output dirs to avoid partial data retention."
    rm -rf "${WORK_INPUT_DIR}" "${WORK_OUTPUT_DIR}"
    exit 3
  fi
fi

if [ "${JOB_MODE}" = "preprocess" ]; then
  INI_FILE="${INI_FILE:-${WORK_INPUT_DIR%/}/input.ini}"
  echo "Running preprocess: inifile=${INI_FILE}, output=${WORK_OUTPUT_DIR}"
  pixi run python -m gtpost.interface.preprocess "${INI_FILE}" "${WORK_OUTPUT_DIR}"
  JOB_RC=$?
  CMD_DESC="preprocess"
elif [ "${JOB_MODE}" = "postprocess" ]; then
  echo "Running postprocess: input=${WORK_INPUT_DIR}, output=${WORK_OUTPUT_DIR}"
  pixi run python -m gtpost.interface.process "${WORK_INPUT_DIR}" "${WORK_OUTPUT_DIR}"
  JOB_RC=$?
  CMD_DESC="postprocess"
else
  echo "Unknown JOB_MODE='${JOB_MODE}', falling back to 'pixi run'" >&2
  exec pixi run
fi

# If we ran a preprocess/process command above, check its exit status and
# on success copy work artifacts into the main output folders for further work.
if [ -n "${JOB_RC-}" ]; then
  if [ ${JOB_RC} -ne 0 ]; then
    echo "ERROR: ${CMD_DESC} job failed with exit code ${JOB_RC}" >&2
    exit ${JOB_RC}
  fi

  echo "${CMD_DESC} completed successfully — copying artifacts to main dir"
  mkdir -p "${MAIN_INPUT_DIR}" "${MAIN_OUTPUT_DIR}"

  # copy input contents
  if ! cp -a "${WORK_INPUT_DIR}/." "${MAIN_INPUT_DIR}/"; then
    echo "ERROR: failed to copy input from ${WORK_INPUT_DIR} to ${MAIN_INPUT_DIR}" >&2
    echo "Removing created input/output dirs to avoid partial data retention."
    rm -rf "${WORK_INPUT_DIR}" "${WORK_OUTPUT_DIR}" "${MAIN_INPUT_DIR}" "${MAIN_OUTPUT_DIR}"
    exit 4
  fi
  # copy output contents
  if ! cp -a "${WORK_OUTPUT_DIR}/." "${MAIN_OUTPUT_DIR}/"; then
    echo "ERROR: failed to copy output from ${WORK_OUTPUT_DIR} to ${MAIN_OUTPUT_DIR}" >&2
    echo "Removing created input/output dirs to avoid partial data retention."
    rm -rf "${WORK_INPUT_DIR}" "${WORK_OUTPUT_DIR}" "${MAIN_INPUT_DIR}" "${MAIN_OUTPUT_DIR}"
    exit 5
  fi

  echo "Artifacts copied to: ${MAIN_INPUT_DIR} ${MAIN_OUTPUT_DIR}"
  exit 0
fi
