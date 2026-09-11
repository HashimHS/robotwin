#!/bin/bash
# Behavior tree + VLA evaluation, run through RobotWin's script/eval_policy.py.
#
#   ./eval.sh <task_name> <task_config> <train_config_name> <model_name> \
#             <checkpoint> <pi0_step> <seed> <gpu_id>
#
# The checkpoint triple can come from the registry:
#   ./eval.sh stack_blocks_four_r demo_clean $(python ../../policy/btvla/registry.py --model-args 16) 10 0 0
#
# The per-task gripper bias is looked up in registry.py; override it with
# BTVLA_GRIPPER_BIAS, and pick a different interpreter with BTVLA_VENV.

export PYTHONIOENCODING=utf-8
export LC_ALL=en_US.UTF-8

policy_name=btvla
task_name=${1}
task_config=${2}
train_config_name=${3}
model_name=${4}
checkpoint=${5}
pi0_step=${6}
seed=${7:-0}
gpu_id=${8:-0}

export CUDA_VISIBLE_DEVICES=${gpu_id}
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export XLA_PYTHON_CLIENT_MEM_FRACTION=0.5
echo -e "\033[33mgpu id (to use): ${gpu_id}\033[0m"

script_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# The behavior tree drives the pi0.5 policy, so it runs in the pi05 environment.
source "${BTVLA_VENV:-${script_dir}/../pi05/.venv}/bin/activate"
cd "${script_dir}/../.." # move to root

gripper_bias=${BTVLA_GRIPPER_BIAS:-$(python policy/btvla/registry.py --gripper-bias ${task_name})}
echo -e "\033[33mgripper bias: ${gripper_bias}\033[0m"

PYTHONWARNINGS=ignore::UserWarning \
python script/eval_policy.py --config policy/$policy_name/deploy_policy.yml \
    --overrides \
    --task_name ${task_name} \
    --task_config ${task_config} \
    --train_config_name ${train_config_name} \
    --model_name ${model_name} \
    --seed ${seed} \
    --checkpoint_id ${checkpoint} \
    --pi0_step ${pi0_step} \
    --gripper_bias ${gripper_bias} \
    --ckpt_setting ${model_name}-${checkpoint} \
    --policy_name ${policy_name} \
    "${@:9}"
