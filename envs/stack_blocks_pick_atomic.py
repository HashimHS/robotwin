from ._base_task import Base_Task
from .utils import *
import sapien
import math
import random


class pick_blocks_rgb(Base_Task):

    def setup_demo(self, **kwags):
        super()._init_task_env_(**kwags)

    def load_actors(self):
        block_half_size = 0.025
        block_pose_lst = []
        for i in range(3):
            block_pose = rand_pose(
                xlim=[-0.28, 0.28],
                ylim=[-0.08, 0.05],
                zlim=[0.741 + block_half_size],
                qpos=[1, 0, 0, 0],
                ylim_prop=True,
                rotate_rand=True,
                rotate_lim=[0, 0, 0.75],
            )

            def check_block_pose(block_pose):
                for j in range(len(block_pose_lst)):
                    if (np.sum(pow(block_pose.p[:2] - block_pose_lst[j].p[:2], 2)) < 0.01):
                        return False
                return True

            while (abs(block_pose.p[0]) < 0.05 or np.sum(pow(block_pose.p[:2] - np.array([0, -0.1]), 2)) < 0.0225
                   or not check_block_pose(block_pose)):
                block_pose = rand_pose(
                    xlim=[-0.28, 0.28],
                    ylim=[-0.08, 0.05],
                    zlim=[0.741 + block_half_size],
                    qpos=[1, 0, 0, 0],
                    ylim_prop=True,
                    rotate_rand=True,
                    rotate_lim=[0, 0, 0.75],
                )
            block_pose_lst.append(deepcopy(block_pose))

        def create_block(block_pose, color):
            return create_box(
                scene=self,
                pose=block_pose,
                half_size=(block_half_size, block_half_size, block_half_size),
                color=color,
                name="box",
            )

        self.block1 = create_block(block_pose_lst[0], (1, 0, 0))
        self.block1.name = "red block"
        self.block2 = create_block(block_pose_lst[1], (0, 1, 0))
        self.block2.name = "green block"
        self.block3 = create_block(block_pose_lst[2], (0, 0, 1))
        self.block3.name = "blue block"
        self.add_prohibit_area(self.block1, padding=0.05)
        self.add_prohibit_area(self.block2, padding=0.05)
        self.add_prohibit_area(self.block3, padding=0.05)
        target_pose = [-0.04, 0, 0.04, -0.05]
        self.prohibited_area.append(target_pose)
        self.block1_target_pose = [0, 0, 0.75 + self.table_z_bias, 0, 1, 0, 0]

        # We shuffle the order of blocks to increase the diversity of demonstrations.
        blocks = [self.block1, self.block2, self.block3]
        random.shuffle(blocks)

        self.block1 = blocks[0]
        self.block2 = blocks[1]
        self.block3 = blocks[2]

        # We pick a random record list to determine which block's pick-and-place process will be recorded.
        self.record_list = [True, False, False]
        random.shuffle(self.record_list)
        

    def play_once(self):
        self.stop_recording()
        self.last_gripper = None
        self.last_actor = None

        arm_tag1 = self.pick_and_place_block_atomic(self.block1, record=self.record_list[0])
        arm_tag2 = self.pick_and_place_block_atomic(self.block2, record=self.record_list[1])
        arm_tag3 = self.pick_and_place_block_atomic(self.block3, record=self.record_list[2])
        self.start_recording()

        # self.info["info"] = {
        #     "{A}": self.block1.name,
        #     "{B}": self.block2.name,
        #     "{C}": self.block3.name,
        #     "{a}": str(arm_tag1),
        #     "{b}": str(arm_tag2),
        #     "{c}": str(arm_tag3),
        # }
        return self.info

    def pick_and_place_block_atomic(self, block, record=False):

        block_pose = block.get_pose().p
        arm_tag = ArmTag("left" if block_pose[0] < 0 else "right")

        if record:
            self.start_recording()
            self.info["info"] = {
                "{A}": block.name,
                "{a}": str(arm_tag),
            }

        if self.last_gripper is not None and (self.last_gripper != arm_tag):
            self.move(
                self.grasp_actor(block, arm_tag=arm_tag, pre_grasp_dis=0.09),
                self.back_to_origin(arm_tag=arm_tag.opposite),
            )
        else:
            self.move(self.grasp_actor(block, arm_tag=arm_tag, pre_grasp_dis=0.09))

        self.move(self.move_by_displacement(arm_tag=arm_tag, z=0.07))

        if self.last_actor is None:
            target_pose = [0, 0, 0.75 + self.table_z_bias, 0, 1, 0, 0]
        else:
            target_pose = self.last_actor.get_functional_point(1)

        self.stop_recording()
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
        self.move(self.move_by_displacement(arm_tag=arm_tag, z=0.07))

        self.last_gripper = arm_tag
        self.last_actor = block
        return str(arm_tag)

    def check_success(self):
        block1_pose = self.block1.get_pose().p
        block2_pose = self.block2.get_pose().p
        block3_pose = self.block3.get_pose().p
        eps = [0.025, 0.025, 0.012]

        return (np.all(abs(block2_pose - np.array(block1_pose[:2].tolist() + [block1_pose[2] + 0.05])) < eps)
                and np.all(abs(block3_pose - np.array(block2_pose[:2].tolist() + [block2_pose[2] + 0.05])) < eps)
                and self.is_left_gripper_open() and self.is_right_gripper_open())