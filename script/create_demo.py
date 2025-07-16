import sys

sys.path.append("./")

import sapien.core as sapien
from sapien.render import clear_cache
from collections import OrderedDict
import pdb
from envs import *
import yaml
import importlib
import json
import traceback
import os
import time
from argparse import ArgumentParser

current_file_path = os.path.abspath(__file__)
parent_directory = os.path.dirname(current_file_path)

# from envs.beat_block_hammer import *
from collect_data import class_decorator, get_camera_config, get_embodiment_config

TASKS = {
    1: "adjust_bottle", # Fails (Bottle slips)
    2: "beat_block_hammer", # Works (gripper_bias=0.1)
    3: "blocks_ranking_rgb", # Works (gripper_bias=0.125)
    4: "blocks_ranking_size", # Works (gripper_bias=0.125)
    5: "click_alarmclock", # Works (gripper_bias=0.1)
    6: "click_bell", # Works (gripper_bias=0.1)
    7: "dump_bin_bigbin", # Works (gripper_bias=0.11)
    8: "grab_roller", # Works (gripper_bias=0.125)
    9: "handover_block", # Fails (Does not place block)
    10: "handover_mic", # Fails (hard to adjust gripper bias)
    11: "hanging_mug", # Fails (aligns correctly, Does not hang)
    12: "lift_pot", # Fails (grasps, does not lift)
    13: "move_can_pot", # Works (gripper_bias=0.13)
    14: "move_pillbottle_pad", # Works (gripper_bias=0.13)
    15: "move_playingcard_away", # Works (gripper_bias=0.13)
    16: "move_stapler_pad", # Works (gripper_bias=0.13)
    17: "open_laptop", # Works (gripper_bias=0.12)
    18: "open_microwave", # Works (gripper_bias=0.105)
    19: "pick_diverse_bottles", # Works (Low success rate, gripper_bias=0.11)
    20: "pick_dual_bottles", # Works (gripper_bias=0.11)
    21: "place_a2b_left", # Works (gripper_bias=0.12)
    22: "place_a2b_right", # Works (gripper_bias=0.12)
    23: "place_bread_basket", # Works (gripper_bias=0.12)
    24: "place_bread_skillet", # Works (gripper_bias=0.125)
    25: "place_burger_fries", # Works (gripper_bias=0.125)
    26: "place_can_basket", # Works (gripper_bias=0.125)
    27: "place_cans_plasticbox", # Works (gripper_bias=0.125)
    28: "place_container_plate", # Works (gripper_bias=0.125)
    29: "place_dual_shoes", # Fails (Collision always check fails)
    30: "place_empty_cup", # Works (gripper_bias=0.125)
    31: "place_fan", # Works (gripper_bias=0.125)
    32: "place_mouse_pad", # Works (gripper_bias=0.125)
    33: "place_object_basket", # Works (gripper_bias=0.125)
    34: "place_object_scale", # Works (gripper_bias=0.125)
    35: "place_object_stand", # Works (gripper_bias=0.125)
    36: "place_phone_stand", # Fails (Placing offset)
    37: "place_shoe", # Works (gripper_bias=0.125)
    38: "press_stapler", # Works (gripper_bias=0.125)
    39: "put_bottles_dustbin", # Fails (Handover issues)
    40: "put_object_cabinet", # Fails (Collides with cabinet, Initial pose may need adjustment)
    41: "rotate_qrcode", # Works (gripper_bias=0.125)
    42: "scan_object", # Fails (gripper_bias=0.125, Seems to work but task returns failure)
    43: "shake_bottle", # Fails (gripper_bias=0.12, Bottle slips because it is too big)
    44: "shake_bottle_horizontally", # Fails (gripper_bias=0.12, Bottle slips because it is too big)
    45: "stack_blocks_three", # Works (gripper_bias=0.12)
    46: "stack_blocks_two", # Works (gripper_bias=0.12)
    47: "stack_bowls_three", # Works (gripper_bias=0.125)
    48: "stack_bowls_two", # Works (gripper_bias=0.125)
    49: "stamp_seal", # Works (gripper_bias=0.12)
    50: "turn_switch", # Fails (gripper_bias=0.115, Very low success rate due collisions)
}

def create_demo(task_name, task_config, seed=0):
    
    task = class_decorator(task_name)
    config_path = f"./task_config/{task_config}.yml"

    with open(config_path, "r", encoding="utf-8") as f:
        args = yaml.load(f.read(), Loader=yaml.FullLoader)

    args['task_name'] = task_name

    embodiment_type = args.get("embodiment")
    embodiment_config_path = os.path.join(CONFIGS_PATH, "_embodiment_config.yml")

    with open(embodiment_config_path, "r", encoding="utf-8") as f:
        _embodiment_types = yaml.load(f.read(), Loader=yaml.FullLoader)

    def get_embodiment_file(embodiment_type):
        robot_file = _embodiment_types[embodiment_type]["file_path"]
        if robot_file is None:
            raise "missing embodiment files"
        return robot_file

    if len(embodiment_type) == 1:
        args["left_robot_file"] = get_embodiment_file(embodiment_type[0])
        args["right_robot_file"] = get_embodiment_file(embodiment_type[0])
        args["dual_arm_embodied"] = True
    elif len(embodiment_type) == 3:
        args["left_robot_file"] = get_embodiment_file(embodiment_type[0])
        args["right_robot_file"] = get_embodiment_file(embodiment_type[1])
        args["embodiment_dis"] = embodiment_type[2]
        args["dual_arm_embodied"] = False
    else:
        raise "number of embodiment config parameters should be 1 or 3"

    args["left_embodiment_config"] = get_embodiment_config(args["left_robot_file"])
    args["right_embodiment_config"] = get_embodiment_config(args["right_robot_file"])

    if len(embodiment_type) == 1:
        embodiment_name = str(embodiment_type[0])
    else:
        embodiment_name = str(embodiment_type[0]) + "+" + str(embodiment_type[1])

    # show config
    print("============= Config =============\n")
    print("\033[95mMessy Table:\033[0m " + str(args["domain_randomization"]["cluttered_table"]))
    print("\033[95mRandom Background:\033[0m " + str(args["domain_randomization"]["random_background"]))
    if args["domain_randomization"]["random_background"]:
        print(" - Clean Background Rate: " + str(args["domain_randomization"]["clean_background_rate"]))
    print("\033[95mRandom Light:\033[0m " + str(args["domain_randomization"]["random_light"]))
    if args["domain_randomization"]["random_light"]:
        print(" - Crazy Random Light Rate: " + str(args["domain_randomization"]["crazy_random_light_rate"]))
    print("\033[95mRandom Table Height:\033[0m " + str(args["domain_randomization"]["random_table_height"]))
    print("\033[95mRandom Head Camera Distance:\033[0m " + str(args["domain_randomization"]["random_head_camera_dis"]))

    print("\033[94mHead Camera Config:\033[0m " + str(args["camera"]["head_camera_type"]) + f", " +
          str(args["camera"]["collect_head_camera"]))
    print("\033[94mWrist Camera Config:\033[0m " + str(args["camera"]["wrist_camera_type"]) + f", " +
          str(args["camera"]["collect_wrist_camera"]))
    print("\033[94mEmbodiment Config:\033[0m " + embodiment_name)
    print("\n==================================")

    args["embodiment_name"] = embodiment_name
    args['task_config'] = task_config
    args["save_path"] = os.path.join(args["save_path"], str(args["task_name"]), args["task_config"])
    args["seed"] = seed
    return task, args


def add_obj(demo, obj="020_hammer_2", pose=None):
    """Add an object to the scene for visualization."""
    demo.dummy, demo.dummy_data = create_glb(
        demo.scene,
        pose=sapien.Pose(pose[:3],pose[3:]),
        modelname=obj,
    )

def pick_obj(demo, obj="020_hammer_2", arm_tag=None):
    block_pose = demo.block.get_functional_point(0, "pose").p
    if arm_tag is None:
        arm_tag = ArmTag("left" if block_pose[0] < 0 else "right")

    # Grasp the hammer with the selected arm
    demo.move(demo.grasp_actor(demo.block, arm_tag=arm_tag, pre_grasp_dis=0.12, grasp_dis=0.01))
    # Move the hammer upwards
    demo.move(demo.move_by_displacement(arm_tag, z=0.07, move_axis="arm"))


# Move the gripper to a specific pose
def move_gripper_to_pose(demo, pose=sapien.Pose(np.array([0, 0, 1]),np.array([0.0, -1.0, 0.0, 1.0])), arm_tag="left"):
    """Move the gripper to a specific pose."""
    actions = [Action(arm_tag, "move", target_pose=pose)]
    demo.move((arm_tag, actions))


def run_demo(task_name, task_config="demo_clean", seed=0):
    

    print(f"Running task: {task_name}")
    success = False
    for i in range(seed, seed + 3):
        try:
            demo, args = create_demo(task_name, task_config, seed=seed)
            demo.setup_demo(**args)
            demo.play_once() # if you want to run the task
            if demo.plan_success and demo.check_success():
                print(f"simulate {task_name} success!")
                success = True
            else:
                print(f"simulate data episode fail!")
            break

        except Exception as e:
            print(f"Failed to create demo for task {task_name}: {e}")
            traceback.print_exc()
            try:
                if args["render_freq"]:
                    demo.close_env()
                    demo.viewer.close()
            except:
                pass
            continue

    if args["render_freq"]:
        while not demo.viewer.closed:
            demo.scene.step()
            demo.scene.update_render()
            demo.viewer.render()

        demo.close_env()
        demo.viewer.close()
    
    return success

if __name__ == "__main__":
    # task_name = input("Enter task name or number (e.g., block_hammer_beat): ")
    # task_name = TASKS[int(task_name)] if task_name.isdigit() else task_name
    task_name = TASKS[31]
    seed = np.random.randint(0, 1000)  # Random seed for demo
    run_demo(task_name, task_config="demo_clean", seed=seed)