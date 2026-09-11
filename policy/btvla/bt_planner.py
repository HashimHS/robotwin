"""Behavior tree glue between RobotWin and the vendored BETR-XP-LLM planner.

The planner needs a ``WorldInterface``: an object that is both the RobotWin task
environment and the behavior tree's view of the world.  Standalone (``hri.py``)
it builds its own environment, but under ``script/eval_policy.py`` the harness
owns the environment, so :func:`attach_world_interface` wraps the environment
the harness already set up instead of creating a second one.
"""

import os
from collections import defaultdict

from . import paths

# Puts the vendored planner and RobotWin on sys.path; must precede the imports below.
paths.bootstrap()

from behaviors import robotwin_behaviors as behaviors  # noqa: E402
from behaviors.common_behaviors import VLMPrompter  # noqa: E402
from envs.utils.actor_utils import Actor  # noqa: E402
from interfaces.base_world_interface import BaseWorldInterface  # noqa: E402
from interfaces.robotwin_world_interface import WorldInterface  # noqa: E402
from planner import planner  # noqa: E402
from policy.pi05.deploy_policy import get_model as get_pi0_model  # noqa: E402

DEFAULT_GPT_VERSION = "gpt-4o"

_mixed_classes = {}


def load_vla_model(train_config_name, model_name, checkpoint_id, pi0_step):
    """Load the pi0.5 checkpoint that executes the behavior tree's skills."""
    return get_pi0_model({
        "train_config_name": train_config_name,
        "model_name": model_name,
        "checkpoint_id": checkpoint_id,
        "pi0_step": pi0_step,
    })


def make_vlm(task_name, vlm_run=False, gpt_version=DEFAULT_GPT_VERSION, api_key=None):
    """Create the VLM prompter, writing its per-task scratch files under Tasks/."""
    if api_key is None:
        api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        if vlm_run:
            raise ValueError("VLM reflection is enabled but $OPENAI_API_KEY is not set.")
        # The prompter rejects an empty key even when it never calls the API.
        api_key = "N/A"
    return VLMPrompter(
        gpt_version=gpt_version,
        api_key=api_key,
        task_name=task_name,
        root_folder_path=str(paths.TASKS_DIR),
        resources=str(paths.VLM_RESOURCES_DIR),
        vlm_run=vlm_run,
    )


def _mixed_class(env_class):
    """``WorldInterface`` mixed with a RobotWin task class, built once per task."""
    if env_class not in _mixed_classes:
        _mixed_classes[env_class] = type("WorldInterface", (WorldInterface, env_class), {})
    return _mixed_classes[env_class]


def attach_world_interface(task_env, vla_model, movable_objects=None, graspable_objects=None,
                           table_offset=0):
    """Return a behavior tree world interface backed by an existing task environment.

    The returned object shares ``task_env``'s attribute dictionary, so the planner
    and the evaluation harness act on exactly the same simulation, but ``task_env``
    itself keeps its own class - the harness still runs the scripted expert check on
    an unmodified environment.  Call once per episode, after ``setup_demo``, so the
    actor list matches the scene that was just built.
    """
    world = object.__new__(_mixed_class(type(task_env)))
    world.__dict__ = task_env.__dict__

    BaseWorldInterface.__init__(
        world,
        cfree_interface=None,
        movable_objects=movable_objects,
        graspable_objects=graspable_objects,
        table_offset=table_offset,
    )
    world.vla_model = vla_model
    world.actors = [item for item in list(vars(world).values()) if isinstance(item, Actor)]
    world._build_name_to_actor()
    world.beat_count = defaultdict(int)
    world.toggled = defaultdict(bool)
    for actor in world.actors:
        world.toggled[actor.get_name()] = False
    return world


def create_world_interface(task_name, task_config="demo_clean", seed=0, gripper_bias=None,
                           vla_model=None, step_lim=None):
    """Build a standalone environment and world interface (no evaluation harness)."""
    world = WorldInterface(
        task_name=task_name,
        task_config=task_config,
        seed=seed,
        gripper_bias=gripper_bias,
        vla_model=vla_model,
    )
    if step_lim is not None:
        world.step_lim = step_lim
    return world


def object_names(world):
    """Names of the actors in the scene, in the order goal builders index them."""
    return [actor.get_name() for actor in world.actors]


def plan_and_execute(world, vlm, goal_builder):
    """Back-chain a behavior tree from the goal conditions and run it to completion."""
    objects = object_names(world)
    print(f"World interface initialized with objects: {objects}")
    goal_conditions = goal_builder(behaviors, objects, world)
    string_bt, tree = planner.plan(world, behaviors, vlm, goal_conditions)
    return string_bt, tree
