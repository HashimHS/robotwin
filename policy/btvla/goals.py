"""Goal conditions the behavior tree planner back-chains from.

A goal builder receives the ``robotwin_behaviors`` module, the list of actor
names in the scene (``object_dict``) and the world interface, and returns the
list of goal condition nodes for one episode.  Builders are registered per task
name so a task can be evaluated without editing code; set ``goals_module`` in
deploy_policy.yml (or override it on the eval.sh command line) to point at your
own ``build_goals`` for one-off experiments.
"""

GOAL_BUILDERS = {}


def register_goal(*task_names):
    """Register a goal builder for one or more task names."""

    def decorator(builder):
        for task_name in task_names:
            GOAL_BUILDERS[task_name] = builder
        return builder

    return decorator


def at_pos(behaviors, world_interface, obj, relation, relative_object=None):
    """Shorthand for the ``AtPos`` condition node."""
    parameters = {"object": obj, "relation": relation}
    if relative_object is not None:
        parameters["relative_object"] = relative_object
    return behaviors.AtPos("", parameters, world_interface)


def stack(count):
    """Stack ``count`` blocks in the centre of the table, bottom-up."""

    def builder(behaviors, object_dict, world_interface):
        _require_objects(object_dict, count)
        conditions = [at_pos(behaviors, world_interface, object_dict[1], "on", "the center")]
        for index in range(2, count + 1):
            conditions.append(
                at_pos(behaviors, world_interface, object_dict[index], "on", object_dict[index - 1])
            )
        return conditions

    return builder


def rank():
    """Line the three blocks up left / centre / right of the table."""

    def builder(behaviors, object_dict, world_interface):
        _require_objects(object_dict, 3)
        return [
            at_pos(behaviors, world_interface, object_dict[2], "on", "left side"),
            at_pos(behaviors, world_interface, object_dict[1], "on", "the center"),
            at_pos(behaviors, world_interface, object_dict[3], "on", "right side"),
        ]

    return builder


def _require_objects(object_dict, count):
    if len(object_dict) <= count:
        raise ValueError(
            f"Goal needs {count} manipulable objects but the scene only contains "
            f"{object_dict}. Check that the task and its goal builder match."
        )


register_goal("stack_blocks_two")(stack(2))
register_goal("stack_blocks_three", "stack_blocks_three_atomic", "stack_blocks_three_r")(stack(3))
register_goal("stack_blocks_four_r")(stack(4))
register_goal("blocks_ranking_rgb", "blocks_ranking_rgb_atomic", "blocks_ranking_rgb_r")(rank())


def get_builder(task_name):
    """Return the goal builder registered for ``task_name``."""
    try:
        return GOAL_BUILDERS[task_name]
    except KeyError:
        raise KeyError(
            f"No goal conditions registered for task '{task_name}'. Add a builder in "
            f"{__file__} with @register_goal('{task_name}'), or pass --goals-module "
            "pointing at a python file that defines build_goals(behaviors, object_dict, "
            "world_interface)."
        ) from None


def build_goals(task_name, behaviors, object_dict, world_interface):
    """Build the goal conditions registered for ``task_name``."""
    return get_builder(task_name)(behaviors, object_dict, world_interface)


# Other goal shapes supported by the RobotWin behavior set, for reference when
# adding a task (see behaviors/robotwin_behaviors.py for the full list):
#
#   behaviors.Grasped("", {"object": "020_hammer", "arm_tag": "left"}, world_interface)
#   behaviors.Beaten("", {"target": "box", "tool": "020_hammer", "count": 1}, world_interface)
#   behaviors.Toggled("", {"object": "046_alarm-clock"}, world_interface)
#   behaviors.Opened("", {"interact_object": "fridge"}, world_interface)
#   at_pos(behaviors, world_interface, obj, "inside", "110_basket")
#   at_pos(behaviors, world_interface, obj, "to_left_of", other_obj)
#   at_pos(behaviors, world_interface, obj, "away")
