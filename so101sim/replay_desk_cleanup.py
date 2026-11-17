"""Replay the recorded actions from Project-IRA Desk Cleanup episode 230."""

import argparse
from contextlib import nullcontext
from pathlib import Path
import time

import numpy as np

import desk_cleanup
from joint_targets import FPS, JointTargets


START_FRAME = 100
EPISODE_FILE = Path(__file__).resolve().parents[1] / "data" / "raw" / "desk_cleanup_episode_230.npz"


def replay(sim, actions, viewer):
    stream = JointTargets(sim, desk_cleanup.ZERO_RAD, desk_cleanup.RAD_PER_UNIT)
    targets, limited = stream.prepare(actions)
    ball = sim.data.body("blue_ball")
    ball_geom = sim.model.geom("blue_ball_geom").id
    bowl_floor = sim.model.geom("bowl_floor").id
    pads = {sim.model.geom(name).id for name in ("fixed_finger_pad", "moving_finger_pad")}
    force = np.zeros(6)
    start_height = ball.xpos[2]
    peak_lift = 0.0
    hold = longest_hold = 0.0
    last_held_frame = None
    touching = set()

    for frame, target in enumerate(targets, start=START_FRAME):
        if viewer is not None and not viewer.is_running():
            break
        start_frame_time = time.monotonic()
        before = sim.data.time
        stream.apply(target)
        lift = ball.xpos[2] - start_height
        peak_lift = max(peak_lift, lift)
        touching.clear()
        for index, contact in enumerate(sim.data.contact[:sim.data.ncon]):
            if ball_geom in contact.geom:
                sim.mj.mj_contactForce(sim.model, sim.data, index, force)
                if force[0] > 0:
                    touching.update(contact.geom)
        if lift > 0.01 and pads <= touching:
            hold += sim.data.time - before
            if hold > longest_hold:
                longest_hold = hold
                last_held_frame = frame
        else:
            hold = 0.0
        if viewer is not None:
            viewer.sync()
            time.sleep(max(0, 1 / FPS - (time.monotonic() - start_frame_time)))

    if not np.isfinite(sim.data.qpos).all():
        raise RuntimeError("MuJoCo returned a non-finite position")
    count = stream.executed
    print(f"Replayed {count}/{len(actions)} targets ({limited[:count].sum()} limited) "
          f"in {sim.data.time - stream.start_time:.3f} simulated seconds.")
    print(f"Peak lift: {100 * peak_lift:.2f} cm. Longest lifted hold on both pads: {longest_hold:.2f} s.")
    if last_held_frame is not None:
        gripper = actions[last_held_frame - START_FRAME, -1]
        print(f"Last frame of longest hold: {last_held_frame} (recorded gripper: {gripper:.2f}%).")
    in_bowl = bowl_floor in touching and np.linalg.norm(
        ball.xpos[:2] - sim.data.geom("bowl_floor").xpos[:2]
    ) < sim.model.geom("bowl_floor").size[0]
    print(f"Ball resting inside bowl at end: {in_bowl}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    # Ignored: the dataset-matched scene is always used (decision 0009).
    parser.add_argument("--match-dataset", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--viewer", action="store_true", help="Show the replay in the MuJoCo window")
    args = parser.parse_args()
    if not EPISODE_FILE.is_file():
        parser.error(f"Missing the local action extract at {EPISODE_FILE}")
    with np.load(EPISODE_FILE) as episode:
        actions = episode["action"]
        if episode["fps"].item() != FPS or actions.shape != (949, 6) or not np.isfinite(actions).all():
            parser.error("Expected episode 230 with 949 finite six-joint actions at 30 Hz")

    print(f"Replaying episode 230 from frame {START_FRAME} at {FPS} Hz.", flush=True)
    sim = desk_cleanup.create_simulation(match_dataset=True)
    viewer_context = nullcontext()
    if args.viewer:
        from mujoco.viewer import launch_passive

        viewer_context = launch_passive(sim.model, sim.data)
    with viewer_context as viewer:
        replay(sim, actions[START_FRAME:], viewer)
        while viewer is not None and viewer.is_running():
            time.sleep(0.1)


if __name__ == "__main__":
    main()
