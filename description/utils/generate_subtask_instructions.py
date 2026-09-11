"""
Generate the language instruction of every atomic action (subtask) of the collected
episodes.

The data collection (`script/collect_data.py`) writes one file per episode in
`<save_path>/<task_name>/<setting>/subtasks/episode<i>.json` holding the key frames of
the episode, i.e. the frame indices at which the executed action changes:

    {
        "episode_index": 0,
        "num_frames": 903,
        "key_frames": [0, 121, 254, ...],
        "subtasks": [
            {"index": 0, "action": "pick", "start_frame": 0, "end_frame": 121,
             "info": {"{A}": "red block", "{a}": "left"}},
            ...
        ]
    }

This script fills the instruction templates of `description/subtask_instruction/` with
the parameters of each subtask and writes the result next to the episode instructions:

    <save_path>/<task_name>/<setting>/instructions/episode<i>_subtasks.json

Usage:
    python utils/generate_subtask_instructions.py <task_name> <setting> <max_num>
"""

import argparse
import json
import os
import random
import re
from typing import Any, Dict, List

import yaml
from tqdm import tqdm

current_file_path = os.path.abspath(__file__)
parent_directory = os.path.dirname(current_file_path)

SUBTASK_INSTRUCTION_DIR = os.path.join(parent_directory, "../subtask_instruction")
OBJECTS_DESCRIPTION_DIR = os.path.join(parent_directory, "../objects_description")
DEFAULT_TEMPLATE_FILE = "_default"
ARTICLES = ("the ", "a ", "an ", "its ", "his ", "her ", "their ")


def extract_placeholders(instruction: str) -> List[str]:
    """Extract all placeholders of the form {X} from an instruction."""
    return re.findall(r"{([^}]+)}", instruction)


def load_templates(task_name: str) -> Dict[str, Any]:
    """
    Load the atomic action templates of a task.
    The task specific file (if any) overrides `_default.json` action by action.
    """
    templates = {}
    for name in (DEFAULT_TEMPLATE_FILE, task_name):
        file_path = os.path.join(SUBTASK_INSTRUCTION_DIR, f"{name}.json")
        if not os.path.exists(file_path):
            continue
        with open(file_path, "r") as f:
            data = json.load(f)
        for action, action_templates in data.items():
            if action.startswith("_"):  # comments
                continue
            templates[action] = action_templates
    if not templates:
        print(f"\033[1mERROR: No subtask instruction templates found for '{task_name}'.\033[0m")
        exit(1)
    return templates


def render_value(key: str, value: str) -> str:
    """
    Render one placeholder value.

    - single lower case letters are arm tags       -> "the left arm"
    - values pointing to `objects_description/<value>.json` -> "the <raw_description>"
    - everything else                              -> "the <value>"

    The article is added here and never written in the templates, so that object
    descriptions and plain names can be used interchangeably.
    """
    value = str(value)

    if len(key) == 1 and "a" <= key <= "z":
        return f"the {value} arm"

    json_path = os.path.join(OBJECTS_DESCRIPTION_DIR, value + ".json")
    if os.path.exists(json_path):
        with open(json_path, "r") as f:
            json_data = json.load(f)
        return f"the {json_data.get('raw_description', value)}"
    if "\\" in value or "/" in value:
        print(f"\033[1mERROR: '{json_path}' looks like a description file, but does not exist.\033[0m")
        exit(1)

    if value.lower().startswith(ARTICLES):
        return value
    return f"the {value}"


def replace_placeholders(instruction: str, params: Dict[str, str]) -> str:
    """Fill every {X} placeholder of the instruction with its rendered value."""
    for key, value in params.items():
        instruction = instruction.replace("{" + key + "}", render_value(key, value))
    return instruction


def strip_braces(info: Dict[str, str]) -> Dict[str, str]:
    return {key.strip("{}"): value for key, value in info.items()}


def filter_templates(instructions: List[str], params: Dict[str, str]) -> List[str]:
    """Keep only the templates whose placeholders are all provided by the subtask."""
    available = set(params.keys())
    return [i for i in instructions if set(extract_placeholders(i)).issubset(available)]


def generate_instructions(
    templates: List[str],
    params: Dict[str, str],
    max_num: int,
) -> List[str]:
    """Fill up to `max_num` templates, shuffled so that the order is not informative."""
    templates = filter_templates(templates, params)
    if not templates:
        return []
    templates = random.sample(templates, len(templates))
    return [replace_placeholders(t, params) for t in templates[:max_num]]


def load_subtask_data(subtask_dir: str) -> List[Dict[str, Any]]:
    """Load every `episode<i>.json` key frame file, ordered by episode index."""
    if not os.path.isdir(subtask_dir):
        print(f"\033[1mERROR: Subtask directory '{subtask_dir}' not found. "
              f"Collect the data with a task that labels its subtasks first.\033[0m")
        exit(1)

    episodes = []
    for file_name in os.listdir(subtask_dir):
        match = re.fullmatch(r"episode(\d+)\.json", file_name)
        if match is None:
            continue
        with open(os.path.join(subtask_dir, file_name), "r") as f:
            data = json.load(f)
        data.setdefault("episode_index", int(match.group(1)))
        episodes.append(data)

    episodes.sort(key=lambda ep: ep["episode_index"])
    return episodes


def generate_episode_subtask_descriptions(
    task_name: str,
    episodes: List[Dict[str, Any]],
    max_num: int = 100,
) -> List[Dict[str, Any]]:
    templates = load_templates(task_name)
    missing_actions = set()
    results = []

    for episode in tqdm(episodes, desc=f"Generating subtask instructions for {task_name} task"):
        described_subtasks = []
        for subtask in episode.get("subtasks", []):
            action = subtask["action"]
            params = strip_braces(subtask.get("info", {}))
            action_templates = templates.get(action)

            if action_templates is None:
                missing_actions.add(action)
                seen, unseen = [], []
            else:
                seen = generate_instructions(action_templates.get("seen", []), params, max_num)
                unseen = generate_instructions(action_templates.get("unseen", []), params, max_num)
                if not seen and not unseen:
                    print(f"Episode {episode['episode_index']}, subtask {subtask['index']} "
                          f"({action}): no template matches the parameters {sorted(params)}")

            described_subtasks.append({
                "index": subtask["index"],
                "action": action,
                "start_frame": subtask["start_frame"],
                "end_frame": subtask["end_frame"],
                "info": subtask.get("info", {}),
                "seen": seen,
                "unseen": unseen,
            })

        results.append({
            "episode_index": episode["episode_index"],
            "num_frames": episode.get("num_frames"),
            "key_frames": episode.get("key_frames", []),
            "subtasks": described_subtasks,
        })

    for action in sorted(missing_actions):
        print(f"\033[1mWARNING: No instruction template for the atomic action '{action}'. "
              f"Add it to description/subtask_instruction/{task_name}.json.\033[0m")

    return results


def save_subtask_descriptions(output_dir: str, descriptions: List[Dict[str, Any]]):
    os.makedirs(output_dir, exist_ok=True)
    for episode in descriptions:
        output_file = os.path.join(output_dir, f"episode{episode['episode_index']}_subtasks.json")
        with open(output_file, "w") as f:
            json.dump(episode, f, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate the instructions of the atomic actions of every episode")
    parser.add_argument("task_name", type=str, help="Name of the task")
    parser.add_argument("setting", type=str, help="Setting name used to construct the data directory path")
    parser.add_argument("max_num", type=int, default=100, help="Maximum number of instructions per subtask")
    args = parser.parse_args()

    setting_file = os.path.join(parent_directory, f"../../task_config/{args.setting}.yml")
    with open(setting_file, "r", encoding="utf-8") as f:
        setting_args = yaml.load(f.read(), Loader=yaml.FullLoader)

    data_dir = os.path.join(parent_directory, f"../../{setting_args['save_path']}/{args.task_name}/{args.setting}")

    episodes = load_subtask_data(os.path.join(data_dir, "subtasks"))
    results = generate_episode_subtask_descriptions(args.task_name, episodes, args.max_num)
    save_subtask_descriptions(os.path.join(data_dir, "instructions"), results)
    print("Successfully Saved Subtask Instructions")
