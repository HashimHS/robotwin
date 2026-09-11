#!/usr/bin/env bash
#
# Collect episodes of a subtask-labeled RoboTwin task and convert them into a LeRobot
# dataset, with the atomic actions (pick / place / ...) labeled per frame.
#
#   bash collect_to_lerobot.sh [episode_num] [task_name] [task_config] [repo_id] [gpu_id]
#
# Defaults collect 100 episodes of stack_blocks_three_atomic into the LeRobot repo
# "stack_sample":
#
#   bash collect_to_lerobot.sh
#   bash collect_to_lerobot.sh 100 stack_blocks_three_atomic demo_clean stack_sample 0
#
# Environment overrides:
#   CONDA_ENV=robotwin     conda environment holding the RoboTwin dependencies
#   MODE=image             LeRobot image storage: "image" (PNG frames) or "video" (mp4,
#                          roughly 10x smaller, needs a working video backend)
#   SPLIT=0                1 = one LeRobot episode per atomic action instead of one per
#                          demonstration
#   CLEAN_PROCESSED=0      1 = delete the intermediate processed_data/ after converting
#
# Collection is resumable: seeds already in data/<task>/<config>/seed.txt and episodes
# that already have an hdf5 file are kept, so re-running tops the dataset up to
# episode_num instead of starting over. Conversion, in contrast, always rebuilds the
# LeRobot dataset at repo_id from scratch (the existing one is deleted).

set -euo pipefail

EPISODE_NUM=${1:-100}
TASK_NAME=${2:-stack_blocks_three_atomic}
TASK_CONFIG=${3:-demo_clean}
REPO_ID=${4:-stack_sample}
GPU_ID=${5:-0}

CONDA_ENV=${CONDA_ENV:-robotwin}
MODE=${MODE:-image}
SPLIT=${SPLIT:-0}
CLEAN_PROCESSED=${CLEAN_PROCESSED:-0}

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

TASK_CFG_FILE="task_config/${TASK_CONFIG}.yml"
PROCESSED_DIR="policy/pi05/processed_data/${TASK_NAME}-${TASK_CONFIG}-${EPISODE_NUM}"

log() { echo -e "\n\033[1;34m==> $*\033[0m"; }

[ -f "envs/${TASK_NAME}.py" ] || { echo "No such task: envs/${TASK_NAME}.py"; exit 1; }
[ -f "$TASK_CFG_FILE" ] || { echo "No such task config: $TASK_CFG_FILE"; exit 1; }

# The task config decides where the episodes land.
SAVE_PATH=$(awk -F':[[:space:]]*' '/^save_path:/ {print $2}' "$TASK_CFG_FILE" | tr -d '"\r ')
SAVE_PATH=${SAVE_PATH:-./data}
RAW_DIR="${SAVE_PATH}/${TASK_NAME}/${TASK_CONFIG}"
if [ "$SAVE_PATH" != "./data" ] && [ "$SAVE_PATH" != "data" ]; then
    echo "WARNING: ${TASK_CFG_FILE} sets save_path: ${SAVE_PATH}, but"
    echo "policy/pi05/scripts/process_data.py always reads ../../data - steps 2 and 3"
    echo "will not find the episodes."
fi

# ---------------------------------------------------------------- environment
if ! python -c "import sapien" >/dev/null 2>&1; then
    log "Activating conda environment '${CONDA_ENV}'"
    CONDA_BASE="$(conda info --base)"
    # shellcheck disable=SC1091
    source "${CONDA_BASE}/etc/profile.d/conda.sh"
    conda activate "$CONDA_ENV"
fi
export CUDA_VISIBLE_DEVICES="$GPU_ID"

# ---------------------------------------------------------------- disk budget
# Measured on stack_blocks_three_atomic: ~20 MB raw + ~33 MB processed + ~101 MB
# LeRobot (image mode) per episode. Video mode is far smaller but harder to predict.
if [ "$MODE" = "image" ]; then PER_EP_MB=154; else PER_EP_MB=60; fi
NEED_MB=$(( EPISODE_NUM * PER_EP_MB ))
FREE_MB=$(df -Pm . | awk 'NR==2 {print $4}')
log "Disk: ~${NEED_MB} MB needed for ${EPISODE_NUM} episodes, ${FREE_MB} MB free"
if [ "$FREE_MB" -lt "$NEED_MB" ]; then
    echo "Not enough free disk space. Options: MODE=video (much smaller), fewer"
    echo "episodes, or CLEAN_PROCESSED=1 to drop the intermediate hdf5 copies."
    exit 1
fi

# ------------------------------------------------------- 1. collect episodes
# episode_num lives in the task config, so patch it and restore on exit.
CFG_BACKUP="$(mktemp)"
cp "$TASK_CFG_FILE" "$CFG_BACKUP"
restore_cfg() { cp "$CFG_BACKUP" "$TASK_CFG_FILE"; rm -f "$CFG_BACKUP"; }
trap restore_cfg EXIT
sed -i -E "s/^episode_num:.*/episode_num: ${EPISODE_NUM}/" "$TASK_CFG_FILE"

log "Collecting ${EPISODE_NUM} episodes of ${TASK_NAME} (${TASK_CONFIG}) on GPU ${GPU_ID}"
bash collect_data.sh "$TASK_NAME" "$TASK_CONFIG" "$GPU_ID"

restore_cfg
trap - EXIT

COLLECTED=$(find "${RAW_DIR}/data" -name 'episode*.hdf5' | wc -l)
LABELED=$(find "${RAW_DIR}/subtasks" -name 'episode*.json' 2>/dev/null | wc -l)
log "Collected ${COLLECTED} episodes, ${LABELED} of them with subtask key frames"
if [ "$LABELED" -eq 0 ]; then
    echo "WARNING: ${TASK_NAME} does not label its atomic actions - the LeRobot dataset"
    echo "will fall back to whole-episode instructions. See the Subtask Labeling section"
    echo "of README.md to annotate play_once with self.subtask(...)."
fi

# ------------------------------------------- 2. RoboTwin hdf5 -> pi05 hdf5
log "Processing ${COLLECTED} episodes into ${PROCESSED_DIR}"
cd policy/pi05
mkdir -p processed_data training_data
bash process_data_pi0.sh "$TASK_NAME" "$TASK_CONFIG" "$COLLECTED"

# ------------------------------------------------------- 3. LeRobot dataset
# # Converted straight from processed_data/. The training_data/ copy in the RoboTwin doc
# # only exists to merge several tasks into one dataset, and would duplicate every frame.
# CONVERT_ARGS=(--raw_dir "processed_data/${TASK_NAME}-${TASK_CONFIG}-${COLLECTED}"
#               --repo_id "$REPO_ID" --mode "$MODE")
# [ "$SPLIT" = "1" ] && CONVERT_ARGS+=(--split-subtask-episodes)

# log "Converting to LeRobot dataset '${REPO_ID}' (mode=${MODE}, split=${SPLIT})"
# export XDG_CACHE_HOME="${REPO_ROOT}/policy/pi05/.cache"
# uv run examples/kuka/convert_kuka_data_to_lerobot_robotwin.py "${CONVERT_ARGS[@]}"

# if [ "$CLEAN_PROCESSED" = "1" ]; then
#     log "Removing intermediate ${PROCESSED_DIR}"
#     rm -rf "processed_data/${TASK_NAME}-${TASK_CONFIG}-${COLLECTED}"
# fi

# # ------------------------------------------------------------------ summary
# OUT_DIR="${XDG_CACHE_HOME}/huggingface/lerobot/${REPO_ID}"
# log "Done"
# python - "$OUT_DIR" <<'PY'
# import json, sys, pathlib
# out = pathlib.Path(sys.argv[1])
# info = json.loads((out / "meta/info.json").read_text())
# tasks = [json.loads(l)["task"] for l in (out / "meta/tasks.jsonl").open()]
# print(f"  dataset  : {out}")
# print(f"  episodes : {info['total_episodes']}   frames: {info['total_frames']}   fps: {info['fps']}")
# print(f"  tasks    : {info['total_tasks']} distinct language instructions")
# for task in tasks[:8]:
#     print(f"      - {task}")
# if len(tasks) > 8:
#     print(f"      ... and {len(tasks) - 8} more")
# PY
