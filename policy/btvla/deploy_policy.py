"""RobotWin policy interface for btvla, driven by ``script/eval_policy.py``.

The harness calls ``get_model`` once, then per episode ``reset_model`` followed by
``eval`` in a loop until the episode succeeds or runs out of steps.  A behavior
tree owns its episode from start to finish, so the first ``eval`` call of an
episode plans and executes the whole task and then reports the step budget as
spent, which ends the harness loop for that seed.
"""

import importlib.util
import os
import traceback
from pathlib import Path

from . import bt_planner
from . import goals as goal_registry
from . import paths


class BTVLAPolicy:
    """The pi0.5 model plus the behavior tree state for the current episode."""

    def __init__(self, vla_model, task_name, goal_builder, vlm_run=False, step_lim=None,
                 stop_on_error=False):
        self.vla_model = vla_model
        self.task_name = task_name
        self.goal_builder = goal_builder
        self.vlm_run = vlm_run
        self.step_lim = step_lim
        self.stop_on_error = stop_on_error
        self.planned = False

    # script/eval_policy.py records these in the result file.
    @property
    def train_config_name(self):
        return self.vla_model.train_config_name

    @property
    def model_name(self):
        return self.vla_model.model_name

    @property
    def checkpoint_id(self):
        return self.vla_model.checkpoint_id

    @property
    def pi0_step(self):
        return self.vla_model.pi0_step

    def reset(self):
        self.vla_model.reset_obsrvationwindows()
        self.planned = False


def load_goal_builder(goals_module_path):
    """Load ``build_goals`` from a user supplied python file."""
    path = os.path.abspath(goals_module_path)
    spec = importlib.util.spec_from_file_location("btvla_user_goals", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load goals module '{path}'")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if not hasattr(module, "build_goals"):
        raise AttributeError(
            f"'{path}' does not define build_goals(behaviors, object_dict, world_interface)")
    return module.build_goals


def get_model(usr_args):
    """Build the policy: the pi0.5 checkpoint and the goal conditions to plan for."""
    task_name = usr_args["task_name"]
    goals_module = usr_args.get("goals_module")
    # Resolved up front so a missing goal definition fails before the checkpoint loads.
    goal_builder = (load_goal_builder(goals_module) if goals_module
                    else goal_registry.get_builder(task_name))

    vla_model = bt_planner.load_vla_model(
        usr_args["train_config_name"],
        usr_args["model_name"],
        usr_args["checkpoint_id"],
        usr_args["pi0_step"],
    )
    return BTVLAPolicy(
        vla_model,
        task_name,
        goal_builder,
        vlm_run=bool(usr_args.get("vlm", False)),
        step_lim=usr_args.get("step_lim"),
        stop_on_error=bool(usr_args.get("stop_on_error", False)),
    )


def eval(TASK_ENV, model, observation):
    """Plan and execute one episode of the task."""
    if not model.planned:
        model.planned = True
        if model.step_lim:
            TASK_ENV.step_lim = model.step_lim

        world = bt_planner.attach_world_interface(TASK_ENV, model.vla_model)
        vlm = bt_planner.make_vlm(model.task_name, vlm_run=model.vlm_run)
        try:
            bt_planner.plan_and_execute(world, vlm, model.goal_builder)
        except Exception:
            # Without this the harness would abort the whole sweep mid-way.
            traceback.print_exc()
            if model.stop_on_error:
                raise
        finally:
            _save_planner_artifacts(TASK_ENV, model.task_name)

    _finish_episode(TASK_ENV)


def reset_model(model):
    model.reset()


def _finish_episode(TASK_ENV):
    """Report the step budget as spent so the harness moves on to the next seed."""
    TASK_ENV.take_action_cnt = max(TASK_ENV.take_action_cnt, TASK_ENV.step_lim)


def _save_planner_artifacts(TASK_ENV, task_name):
    """File the rendered behavior tree with the episode it belongs to."""
    episode = getattr(TASK_ENV, "test_num", 0)
    save_dir = getattr(TASK_ENV, "eval_video_path", None)
    if save_dir is None:
        save_dir = paths.task_dir(task_name)
    paths.collect_planner_artifacts(Path(save_dir) / f"episode{episode}_bt")
