"""Path resolution and import bootstrap for the btvla policy.

Everything btvla needs lives inside this folder: the behavior tree planner is
vendored under ``betr_xp_llm`` (see its VENDOR.md) and the VLM prompt resources
come with it.  The vendored packages import each other by their top level names
(``planner``, ``behaviors``, ``interfaces``, ``vlm``), so :func:`bootstrap` puts
``betr_xp_llm`` on ``sys.path`` rather than rewriting the copied sources.

RobotWin itself resolves ``./assets/...`` and ``./task_config/<config>.yml``
against the current working directory, so the process has to run from the
RobotWin root; ``script/eval_policy.py`` is always launched from there, and
:func:`bootstrap` moves there as well for anything started by hand.
"""

import os
import sys
from pathlib import Path

#: ``robotwin/policy/btvla``
BTVLA_DIR = Path(__file__).resolve().parent
#: ``robotwin``
ROBOTWIN_ROOT = BTVLA_DIR.parents[1]

#: Vendored behavior tree planner (see betr_xp_llm/VENDOR.md).
BETR_XP_LLM_DIR = BTVLA_DIR / "betr_xp_llm"
#: Prompt/skill resources the VLM prompter reads and the planner writes to.
VLM_RESOURCES_DIR = BETR_XP_LLM_DIR / "vlm" / "resources"
#: Per-task VLM working folders (plan.txt, execution_history.txt, ...).
TASKS_DIR = Path(os.environ.get("BTVLA_TASKS_DIR", BTVLA_DIR / "Tasks"))

POLICY_NAME = "btvla"

_bootstrapped = False


def bootstrap(chdir=True):
    """Make the vendored planner and RobotWin importable. Safe to call twice."""
    global _bootstrapped
    if _bootstrapped:
        return

    for path in (str(BETR_XP_LLM_DIR), str(ROBOTWIN_ROOT)):
        if path not in sys.path:
            sys.path.insert(0, path)

    if chdir and Path.cwd() != ROBOTWIN_ROOT:
        os.chdir(ROBOTWIN_ROOT)

    _bootstrapped = True


def task_dir(task_name):
    """Working folder the VLM prompter writes to for ``task_name``."""
    path = TASKS_DIR / task_name
    path.mkdir(parents=True, exist_ok=True)
    return path


def collect_planner_artifacts(destination):
    """Move the ``planned_bt.*`` files the planner renders into the cwd.

    ``planner.plan`` renders the final tree with a hard-coded relative path, so
    the files land in the RobotWin root; move them next to the rest of the
    episode output instead.
    """
    destination = Path(destination)
    moved = []
    artifacts = list(Path.cwd().glob("planned_bt.*"))
    if artifacts:
        destination.mkdir(parents=True, exist_ok=True)
    for artifact in artifacts:
        target = destination / artifact.name
        artifact.replace(target)
        moved.append(target)
    return moved
