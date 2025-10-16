from collect_data import *
import time
import pandas as pd

TASKS = {
    1: {"name": "adjust_bottle", "gripper_bias": None, "works": False},  # Fails (Bottle slips)
    2: {"name": "beat_block_hammer", "gripper_bias": 0.135, "works": True},  # Works
    3: {"name": "blocks_ranking_rgb", "gripper_bias": 0.17, "works": True},  # Works
    4: {"name": "blocks_ranking_size", "gripper_bias": 0.16, "works": True},  # Works
    5: {"name": "click_alarmclock", "gripper_bias": 0.135, "works": True},  # Works
    6: {"name": "click_bell", "gripper_bias": 0.135, "works": True},  # Works
    7: {"name": "dump_bin_bigbin", "gripper_bias": 0.155, "works": True},  # Works
    8: {"name": "grab_roller", "gripper_bias": 0.165, "works": True},  # Works
    9: {"name": "handover_block", "gripper_bias": None, "works": False},  # Fails (Does not place block)
    10: {"name": "handover_mic", "gripper_bias": None, "works": False},  # Fails (hard to adjust gripper bias)
    11: {"name": "hanging_mug", "gripper_bias": None, "works": False},  # Fails (aligns correctly, Does not hang)
    12: {"name": "lift_pot", "gripper_bias": None, "works": False},  # Fails (grasps, does not lift)
    13: {"name": "move_can_pot", "gripper_bias": 0.16, "works": True},  # Works
    14: {"name": "move_pillbottle_pad", "gripper_bias": 0.16, "works": True},  # Works
    15: {"name": "move_playingcard_away", "gripper_bias": 0.16, "works": True},  # Works
    16: {"name": "move_stapler_pad", "gripper_bias": 0.16, "works": True},  # Works
    17: {"name": "open_laptop", "gripper_bias": 0.155, "works": False},  # Works
    18: {"name": "open_microwave", "gripper_bias": 0.14, "works": False},  # Works
    19: {"name": "pick_diverse_bottles", "gripper_bias": 0.15, "works": False},  # Works (Low success rate)
    20: {"name": "pick_dual_bottles", "gripper_bias": 0.15, "works": False},  # Works
    21: {"name": "place_a2b_left", "gripper_bias": 0.155, "works": True},  # Works
    22: {"name": "place_a2b_right", "gripper_bias": 0.155, "works": True},  # Works
    23: {"name": "place_bread_basket", "gripper_bias": 0.155, "works": True},  # Works
    24: {"name": "place_bread_skillet", "gripper_bias": 0.16, "works": True},  # Works
    25: {"name": "place_burger_fries", "gripper_bias": 0.165, "works": True},  # Works
    26: {"name": "place_can_basket", "gripper_bias": 0.16, "works": True},  # Works
    27: {"name": "place_cans_plasticbox", "gripper_bias": 0.17, "works": True},  # Works
    28: {"name": "place_container_plate", "gripper_bias": 0.16, "works": True},  # Works
    29: {"name": "place_dual_shoes", "gripper_bias": None, "works": False},  # Fails (Collision always check fails)
    30: {"name": "place_empty_cup", "gripper_bias": 0.16, "works": True},  # Works
    31: {"name": "place_fan", "gripper_bias": 0.16, "works": True},  # Works
    32: {"name": "place_mouse_pad", "gripper_bias": 0.16, "works": True},  # Works
    33: {"name": "place_object_basket", "gripper_bias": 0.16, "works": True},  # Works
    34: {"name": "place_object_scale", "gripper_bias": 0.16, "works": True},  # Works
    35: {"name": "place_object_stand", "gripper_bias": 0.16, "works": True},  # Works
    36: {"name": "place_phone_stand", "gripper_bias": None, "works": False},  # Fails (Placing offset)
    37: {"name": "place_shoe", "gripper_bias": 0.16, "works": True},  # Works
    38: {"name": "press_stapler", "gripper_bias": 0.16, "works": True},  # Works
    39: {"name": "put_bottles_dustbin", "gripper_bias": None, "works": False},  # Fails (Handover issues)
    40: {"name": "put_object_cabinet", "gripper_bias": None, "works": False},  # Fails (Collides with cabinet, Initial pose may need adjustment)
    41: {"name": "rotate_qrcode", "gripper_bias": 0.16, "works": True},  # Works
    42: {"name": "scan_object", "gripper_bias": 0.16, "works": False},  # Fails (Seems to work but task returns failure)
    43: {"name": "shake_bottle", "gripper_bias": 0.155, "works": False},  # Fails (Bottle slips because it is too big)
    44: {"name": "shake_bottle_horizontally", "gripper_bias": 0.155, "works": False},  # Fails (Bottle slips because it is too big)
    45: {"name": "stack_blocks_three", "gripper_bias": 0.17, "works": True},  # Works
    46: {"name": "stack_blocks_two", "gripper_bias": 0.17, "works": True},  # Works
    47: {"name": "stack_bowls_three", "gripper_bias": 0.16, "works": True},  # Works
    48: {"name": "stack_bowls_two", "gripper_bias": 0.16, "works": True},  # Works
    49: {"name": "stamp_seal", "gripper_bias": 0.155, "works": True},  # Works
    50: {"name": "turn_switch", "gripper_bias": 0.15, "works": False},  # Fails (Very low success rate due collisions)
    51: {"name": "pick_obj", "gripper_bias": 0.16, "works": True},  # Works
}

def get_embodiment_config(robot_file, gripper_bias=None):
    robot_config_file = os.path.join(robot_file, "config.yml")
    with open(robot_config_file, "r", encoding="utf-8") as f:
        embodiment_args = yaml.load(f.read(), Loader=yaml.FullLoader)
    if gripper_bias is not None:
        embodiment_args["gripper_bias"] = gripper_bias
    return embodiment_args

def main(task_name=None, task_config=None, gripper_bias=None):

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

    args["left_embodiment_config"] = get_embodiment_config(args["left_robot_file"], gripper_bias=gripper_bias)
    args["right_embodiment_config"] = get_embodiment_config(args["right_robot_file"], gripper_bias=gripper_bias)

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
    run(task, args)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("task_id", type=int)
    parser.add_argument("task_config", type=str)
    parser = parser.parse_args()
    task_id = parser.task_id
    config = parser.task_config
    task_info = TASKS[task_id]
    
    if not task_info["works"]: # Skip tasks that are known to fail
        print(f"Skipping task {task_id}: {task_info['name']} as it is marked as not working.")
        exit(0)
        
    from test_render import Sapien_TEST
    Sapien_TEST()
    import torch.multiprocessing as mp
    mp.set_start_method("spawn", force=True)

    print(f"Running task {task_id}: {task_info['name']} with gripper bias {task_info['gripper_bias']}")
    task_name = task_info["name"]
    gripper_bias = task_info["gripper_bias"]
    print(f"  Starting {config}...")
    start_time = time.time()
    main(task_name=task_name, task_config=config, gripper_bias=gripper_bias)
    elapsed = time.time() - start_time
    print(f"  Finished {task_info['name']}:{config} in {elapsed:.2f} seconds.")
    
    # create a small json file to record the completion
    record = {
        "task_id": task_id,
        "task_name": task_name,
        "task_config": config,
        "gripper_bias": gripper_bias,
        "success": True,
        "elapsed_time": elapsed
    }
    record_path = os.path.join("./data", task_name, config, "completion_record.json")
    with open(record_path, "w", encoding="utf-8") as f:
        json.dump(record, f, indent=4)