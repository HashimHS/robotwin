from ._base_task import Base_Task
from .utils import *
import sapien
import math
import numpy as np


class stack_blocks_four_r(Base_Task):

    def setup_demo(self, **kwags):
        super()._init_task_env_(**kwags)

    def load_actors(self):
        block_half_size = 0.025

        def sample_block_pose():
            return rand_pose(
                xlim=[-0.28, 0.28],
                ylim=[-0.08, 0.05],
                zlim=[0.741 + block_half_size],
                qpos=[1, 0, 0, 0],
                ylim_prop=True,
                rotate_rand=True,
                rotate_lim=[0, 0, 0.75],
            )

        def check_block_pose(block_pose, block_pose_lst):
            if abs(block_pose.p[0]) < 0.05:
                return False
            if np.sum(pow(block_pose.p[:2] - np.array([0, -0.1]), 2)) < 0.0225:
                return False
            for j in range(len(block_pose_lst)):
                if (np.sum(pow(block_pose.p[:2] - block_pose_lst[j].p[:2], 2)) < 0.01):
                    return False
            return True

        # Four blocks can crowd the sampling area, so a partially filled layout may
        # leave no room for the remaining blocks. Give up on such a layout and
        # resample all of the blocks instead of retrying a single one forever.
        while True:
            block_pose_lst = []
            for i in range(4):
                block_pose = None
                for _ in range(100):
                    candidate_pose = sample_block_pose()
                    if check_block_pose(candidate_pose, block_pose_lst):
                        block_pose = candidate_pose
                        break
                if block_pose is None:
                    break
                block_pose_lst.append(deepcopy(block_pose))
            if len(block_pose_lst) == 4:
                break

        def create_block(block_pose, color, name):
            return create_box(
                scene=self,
                pose=block_pose,
                half_size=(block_half_size, block_half_size, block_half_size),
                color=color,
                name=name,
            )

        blocks = {
            0: {"color": (1, 0, 0), "name": "red block"},
            1: {"color": (0, 1, 0), "name": "green block"},
            2: {"color": (0, 0, 1), "name": "blue block"},
            3: {"color": (1, 1, 0), "name": "yellow block"},
        }

        # We shuffle the order of blocks to increase the diversity of demonstrations.
        # `np.random` is seeded with the episode seed (`random` is not), so the episode
        # is reproducible from its seed.
        block_indices = [int(i) for i in np.random.permutation(4)]
        colors = [blocks[i]["color"] for i in block_indices]
        names = [blocks[i]["name"] for i in block_indices]

        self.block1 = create_block(block_pose_lst[0], colors[0], name=names[0])
        self.block1.name = names[0]
        self.block2 = create_block(block_pose_lst[1], colors[1], name=names[1])
        self.block2.name = names[1]
        self.block3 = create_block(block_pose_lst[2], colors[2], name=names[2])
        self.block3.name = names[2]
        self.block4 = create_block(block_pose_lst[3], colors[3], name=names[3])
        self.block4.name = names[3]
        self.add_prohibit_area(self.block1, padding=0.05)
        self.add_prohibit_area(self.block2, padding=0.05)
        self.add_prohibit_area(self.block3, padding=0.05)
        self.add_prohibit_area(self.block4, padding=0.05)
        target_pose = [-0.04, 0, 0.04, -0.05]
        self.prohibited_area.append(target_pose)
        self.block1_target_pose = [0, 0, 0.75 + self.table_z_bias, 0, 1, 0, 0]

        self.failure_types = {
            0: "Wrong stack sequence",
            1: "Manipulation failure",
        }

    def get_info(self):
        # Store information about the blocks and which arms were used
        self.info["info"]["{A}"] = self.block1.name
        self.info["info"]["{B}"] = self.block2.name
        self.info["info"]["{C}"] = self.block3.name
        self.info["info"]["{D}"] = self.block4.name
        return self.info

    def play_once(self):
        # Initialize tracking variables for last used gripper and actor
        self.last_gripper = None
        self.last_actor = None

        # Pick and place the bottom block and get which arm was used
        arm_tag1 = self.pick_and_place_block(self.block1)
        # Pick and place the second block and get which arm was used
        arm_tag2 = self.pick_and_place_block(self.block2)
        # Pick and place the third block and get which arm was used
        arm_tag3 = self.pick_and_place_block(self.block3)
        # Pick and place the top block and get which arm was used
        arm_tag4 = self.pick_and_place_block(self.block4)

        # Store information about the blocks and which arms were used
        self.info["info"] = {
            "{A}": self.block1.name,
            "{B}": self.block2.name,
            "{C}": self.block3.name,
            "{D}": self.block4.name,
            "{a}": str(arm_tag1),
            "{b}": str(arm_tag2),
            "{c}": str(arm_tag3),
            "{d}": str(arm_tag4),
        }
        return self.info

    def pick_and_place_block(self, block: Actor):
        block_pose = block.get_pose().p
        arm_tag = ArmTag("left" if block_pose[0] < 0 else "right")

        if self.last_gripper is not None and (self.last_gripper != arm_tag):
            self.move(
                self.grasp_actor(block, arm_tag=arm_tag, pre_grasp_dis=0.09),  # arm_tag
                self.back_to_origin(arm_tag=arm_tag.opposite),  # arm_tag.opposite
            )
        else:
            self.move(self.grasp_actor(block, arm_tag=arm_tag, pre_grasp_dis=0.09))  # arm_tag

        self.move(self.move_by_displacement(arm_tag=arm_tag, z=0.07))  # arm_tag

        if self.last_actor is None:
            target_pose = [0, 0, 0.75 + self.table_z_bias, 0, 1, 0, 0]
        else:
            target_pose = self.last_actor.get_functional_point(1)

        self.move(
            self.place_actor(
                block,
                target_pose=target_pose,
                arm_tag=arm_tag,
                functional_point_id=0,
                pre_dis=0.05,
                dis=0.,
                pre_dis_axis="fp",
            ))
        self.move(self.move_by_displacement(arm_tag=arm_tag, z=0.07))  # arm_tag

        self.last_gripper = arm_tag
        self.last_actor = block
        return str(arm_tag)

    def check_success(self):
        block1_pose = self.block1.get_pose().p
        block2_pose = self.block2.get_pose().p
        block3_pose = self.block3.get_pose().p
        block4_pose = self.block4.get_pose().p
        eps = [0.025, 0.025, 0.012]

        return (
            np.all(abs(block2_pose - np.array(block1_pose[:2].tolist() + [block1_pose[2] + 0.05])) < eps)
            and np.all(abs(block3_pose - np.array(block2_pose[:2].tolist() + [block2_pose[2] + 0.05])) < eps)
            and np.all(abs(block4_pose - np.array(block3_pose[:2].tolist() + [block3_pose[2] + 0.05])) < eps)
            and self.is_left_gripper_open() and self.is_right_gripper_open())

    def get_failure_info(self):
        block1_pose = self.block1.get_pose().p
        block2_pose = self.block2.get_pose().p
        block3_pose = self.block3.get_pose().p
        block4_pose = self.block4.get_pose().p
        poses = [block1_pose, block2_pose, block3_pose, block4_pose]
        eps = [0.025, 0.025, 0.012]

        for i in range(1, len(poses)):
            for j in range(1, len(poses)):
                if i != j and j != i-1:
                    if np.all(abs(poses[i] - np.array(poses[j][:2].tolist() + [poses[j][2] + 0.05])) < eps):
                        return self.failure_types[0]
        return self.failure_types[1]