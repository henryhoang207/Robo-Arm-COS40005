import unittest

from engine import Simulation
from protocol import Action


class GraspTest(unittest.TestCase):
    def test_jaw_pads_lift_red_ball(self):
        sim = Simulation("local")
        timestep = sim.model.opt.timestep
        ball = sim.data.body("red_ball")
        for _ in range(round(0.4 / timestep)):
            sim.step()
        table_height = ball.xpos[2]

        # Reach the scene's red ball with the fingers on opposite sides.
        above = (-0.866595, -0.866446, 0.694366, 1.188074, -1.522110)
        pinch = (-0.866595, -0.685270, 1.290078, 0.411159, -1.522116)
        waypoints = (
            (above, 0.60, 1.50),
            (pinch, 0.60, 1.00),
            (pinch, 0.10, 0.65),
            (above, 0.10, 1.20),
        )
        for sequence, (arm, gripper, duration) in enumerate(waypoints):
            sim.enqueue(Action(sequence, (*arm, gripper), duration, duration + 0.5), from_board=False)
            for _ in range(round((duration + 0.2) / timestep)):
                sim.step()
            self.assertEqual(sim.snapshot()["status"], "DONE")

        self.assertGreater(ball.xpos[2] - table_height, 0.07)
        ball_geom = sim.model.geom("red_ball_geom").id
        touching = {
            int(other)
            for contact in sim.data.contact[:sim.data.ncon]
            if ball_geom in contact.geom
            for other in contact.geom
            if other != ball_geom
        }
        self.assertIn(sim.model.geom("fixed_finger_pad").id, touching)
        self.assertIn(sim.model.geom("moving_finger_pad").id, touching)


if __name__ == "__main__":
    unittest.main()
