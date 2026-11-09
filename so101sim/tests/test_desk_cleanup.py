import json
from pathlib import Path
import unittest
from unittest.mock import patch

from desk_cleanup import DATASET, DATASET_REVISION, TASK, create_simulation, matches_checkpoint_task


class DeskCleanupTest(unittest.TestCase):
    def test_calibration_selection_requires_matching_task_and_dataset_revision(self):
        checkpoint = Path("checkpoint")
        with patch.object(Path, "read_text", side_effect=FileNotFoundError):
            self.assertFalse(matches_checkpoint_task(checkpoint, TASK))

        dataset = {"repo_id": DATASET, "revision": DATASET_REVISION}
        with patch.object(Path, "read_text", return_value=json.dumps({"dataset": dataset})):
            self.assertTrue(matches_checkpoint_task(checkpoint, TASK + "."))
            self.assertFalse(matches_checkpoint_task(checkpoint, "Roll the dice"))

        dataset["revision"] = "another-revision"
        with patch.object(Path, "read_text", return_value=json.dumps({"dataset": dataset})):
            self.assertFalse(matches_checkpoint_task(checkpoint, TASK))

    def test_dataset_matched_start_has_clearance_and_objects_in_frame(self):
        sim = create_simulation(match_dataset=True)
        self.assertEqual(sim.data.ncon, 0)
        self.assertGreater(sim.data.site("gripperframe").xpos[2], 0.05)
        jaw_tips = []
        for name in ("fixed_finger_pad", "moving_finger_pad"):
            pad = sim.data.geom(name)
            half_length = sim.model.geom(name).size[2]
            jaw_tips.append(pad.xpos - half_length * pad.xmat.reshape(3, 3)[:, 2])
        for camera_name, points in (
            ("overhead_camera", (sim.data.body("blue_ball").xpos, sim.data.body("drop_box").xpos)),
            ("wrist_camera", jaw_tips),
        ):
            camera = sim.data.camera(camera_name)
            camera_id = sim.model.camera(camera_name).id
            width, height = sim.model.cam_sensorsize[camera_id]
            fx, fy, cx, cy = sim.model.cam_intrinsic[camera_id]
            for point in points:
                x, y, depth = (point - camera.xpos) @ camera.xmat.reshape(3, 3)
                self.assertLess(depth, 0, camera_name)
                self.assertLess(abs(fx * x / -depth - cx), width / 2, camera_name)
                self.assertLess(abs(-fy * y / -depth - cy), height / 2, camera_name)
