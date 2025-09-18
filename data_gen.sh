#!/bin/bash

gpu_id=${1}
task_config=${2}

./script/.update_path.sh > /dev/null 2>&1

export CUDA_VISIBLE_DEVICES=${gpu_id}

PYTHONWARNINGS=ignore::UserWarning \
seq 1 50 | xargs -P 3 -I {} python script/data_gen.py {} ${task_config}