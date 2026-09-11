#!/usr/bin/env python
"""Interactive session with the VLA policy, without the behavior tree.

Evaluation goes through ``script/eval_policy.py`` (see eval.sh); this is the
standalone path for driving the robot by typing instructions:

    cd robotwin/policy/btvla
    ../pi05/.venv/bin/python hri.py --task stack_blocks_four_r --model 16
"""

import argparse
import os
import sys

# Import the package the same way script/eval_policy.py does, so both routes
# share one module identity no matter which directory this is started from.
_POLICY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _POLICY_DIR not in sys.path:
    sys.path.insert(0, _POLICY_DIR)

from btvla import registry  # noqa: E402


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Drive the pi0.5 policy with typed instructions.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--task", default="stack_blocks_four_r", help="task name or registry id")
    parser.add_argument("--task_config", default="demo_clean", help="config in robotwin/task_config")
    parser.add_argument("--model", default="16", help="model name or registry id")
    parser.add_argument("--pi0_step", type=int, default=10, help="policy steps per inference call")
    parser.add_argument("--seed", type=int, default=0, help="episode seed")
    parser.add_argument("--step_lim", type=int, default=1500, help="simulation step limit")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        task = registry.resolve_task(args.task)
        model = registry.resolve_model(args.model)
    except KeyError as error:
        print(error.args[0], file=sys.stderr)
        return 2

    from btvla import bt_planner

    vla_model = bt_planner.load_vla_model(
        model["train_config_name"], model["model_name"], model["checkpoint_id"], args.pi0_step)
    world = bt_planner.create_world_interface(
        task["name"],
        task_config=args.task_config,
        seed=args.seed,
        gripper_bias=task["gripper_bias"],
        vla_model=vla_model,
        step_lim=args.step_lim,
    )
    print(f"World interface initialized with objects: {bt_planner.object_names(world)}")

    try:
        while True:
            world.hri_mode()
    except (KeyboardInterrupt, EOFError):
        print("\nEnding session.")
    finally:
        world.reset_vla()
        world.close_env(clear_cache=True)
        if world.render_freq:
            world.viewer.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
