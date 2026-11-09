"""Local MuJoCo calibration for Project-IRA's Desk Cleanup episode 230."""

import json
import math

import mujoco
import numpy as np

from engine import MODEL_FILE, Simulation
from protocol import JOINT_NAMES


TASK = "Place the ball into the bowl to clear the desk"
DATASET = "Project-IRA/TPSoSe2026_Dataset_Full_Merged_Final_LeRobot_SO101_V1"
DATASET_REVISION = "bf6f568e9ec218fff838fb266e161724ec4f7e2c"

# Affine mapping from LeRobot degrees and gripper percent to MuJoCo radians.
# The positive wrist-roll sign matches both rotation directions in episodes 267 and 338.
ZERO_RAD = np.r_[np.deg2rad([0, 5, -2, 0, 6.037]), -0.17]
RAD_PER_UNIT = np.r_[np.full(5, np.pi / 180), 0.0095]
# The folded home pose intersects the MuJoCo shoulder meshes. Start at frame 100,
# with the gripper already clear and the ball still in its recorded position.
RECORDED_START = np.array([-3.69231, -103.47253, 79.86813, 81.89011, -90.32967, 1.81087])
TABLE_MARKERS = (
    (-0.574, 0.019), (-0.496, 0.086), (-0.409, 0.139), (-0.234, 0.351),
    (-0.542, -0.080), (-0.460, -0.020), (-0.184, 0.240), (-0.511, -0.169),
    (-0.434, -0.126), (-0.140, 0.116), (-0.476, -0.274), (-0.407, -0.245),
    (-0.311, -0.217), (-0.182, -0.162), (-0.064, -0.124), (-0.377, -0.334),
    (-0.283, -0.324), (-0.107, 0.007),
)


def matches_checkpoint_task(checkpoint, task):
    if task.strip().removesuffix(".").casefold() != TASK.casefold():
        return False
    try:
        dataset = json.loads((checkpoint / "train_config.json").read_text(encoding="utf-8"))["dataset"]
        return dataset["repo_id"] == DATASET and dataset["revision"] == DATASET_REVISION
    except (OSError, ValueError, KeyError, TypeError):
        return False


def _set_camera(camera, position, xyaxes, focal, principal):
    camera.pos[:] = position
    camera.alt.type = mujoco.mjtOrientation.mjORIENTATION_XYAXES
    camera.alt.xyaxes[:] = xyaxes
    camera.resolution[:] = [640, 480]
    camera.sensor_size[:] = [0.0064, 0.0048]
    camera.focal_pixel[:] = [focal, focal]
    camera.principal_pixel[:] = principal


def _set_ball_appearance(spec, ball):
    # A cube map gives the sphere the recorded ball's navy, yellow and red panels.
    edge = 32
    u, v = np.meshgrid(np.linspace(-1, 1, edge), np.linspace(-1, 1, edge))
    one = np.ones_like(u)
    faces = [(one, -v, -u), (-one, -v, u), (u, one, v), (u, -one, -v),
             (u, -v, one), (-u, -v, -one)]
    directions = np.stack([np.stack(face, axis=-1) for face in faces])
    directions /= np.linalg.norm(directions, axis=-1, keepdims=True)
    pixels = np.empty((6, edge, edge, 3), dtype=np.uint8)
    pixels[:] = [39, 50, 105]
    lower_panel = directions @ np.array([0.58, 0.58, 0.58]) < 0.10
    pixels[lower_panel] = [225, 181, 98]
    pixels[(directions[..., 1] > 0.72) & ~lower_panel] = [181, 58, 58]
    spec.add_texture(name="desk_ball_panels", type=mujoco.mjtTexture.mjTEXTURE_CUBE,
                     width=edge, height=6 * edge, nchannel=3, data=pixels.ravel())
    material = spec.add_material(name="desk_ball_fabric", rgba=[1, 1, 1, 1], specular=0.15, shininess=0.25)
    material.textures[mujoco.mjtTextureRole.mjTEXROLE_RGB] = "desk_ball_panels"
    ball.rgba[:] = [1, 1, 1, 1]
    ball.material = material.name


def _add_bowl_appearance(spec, bowl, color):
    # Keep the tested contact geometry and render a smooth bowl wall in its place.
    segments = 48
    profile = [(0.075, 0.006), (0.079, 0.044), (0.083, 0.050),
               (0.089, 0.047), (0.085, 0.007)]
    angles = np.linspace(0, math.tau, segments, endpoint=False)
    vertices = [(radius * math.cos(angle), radius * math.sin(angle), height)
                for radius, height in profile for angle in angles]
    faces = []
    for ring in range(len(profile)):
        next_ring = (ring + 1) % len(profile)
        for i in range(segments):
            j = (i + 1) % segments
            a, b = ring * segments + i, ring * segments + j
            c, d = next_ring * segments + i, next_ring * segments + j
            faces.extend(((a, c, b), (b, c, d)))
    spec.add_mesh(name="desk_bowl_surface", smoothnormal=True,
                  uservert=np.asarray(vertices).ravel(), userface=np.asarray(faces).ravel())
    bowl.add_geom(name="bowl_surface", type=mujoco.mjtGeom.mjGEOM_MESH,
                  meshname="desk_bowl_surface", rgba=color, contype=0, conaffinity=0, mass=0)

    # The reference bowl has clutter. Place visual proxies away from the measured drop point.
    box = mujoco.mjtGeom.mjGEOM_BOX
    props = (
        ((-0.033, 0.027, 0.017), (0.017, 0.009, 0.008), (0.06, 0.19, 0.57, 1), 0.22),
        ((-0.034, -0.003, 0.018), (0.010, 0.009, 0.009), (0.69, 0.10, 0.12, 1), -0.45),
        ((-0.051, 0.008, 0.018), (0.009, 0.012, 0.010), (0.11, 0.49, 0.19, 1), 0.32),
        ((-0.012, 0.026, 0.016), (0.025, 0.004, 0.004), (0.89, 0.86, 0.78, 1), 1.05),
        ((-0.038, -0.024, 0.014), (0.006, 0.006, 0.006), (0.84, 0.83, 0.75, 1), 0.36),
        ((-0.010, 0.041, 0.015), (0.010, 0.005, 0.005), (0.53, 0.35, 0.21, 1), -0.40),
        ((0.006, -0.039, 0.015), (0.007, 0.007, 0.007), (0.88, 0.86, 0.77, 1), 0.42),
        ((-0.021, -0.048, 0.016), (0.014, 0.006, 0.007), (0.49, 0.31, 0.19, 1), 0.75),
    )
    for i, (pos, size, rgba, angle) in enumerate(props):
        bowl.add_geom(name=f"bowl_prop_{i}", type=box, pos=pos, size=size, rgba=rgba,
                      euler=[0, 0, angle], contype=0, conaffinity=0, mass=0)


def _add_table_appearance(spec):
    table = spec.geom("table_top")
    table.pos[:2] = [-0.17, -0.04]
    table.size[:2] = [0.62, 0.53]
    spec.visual.headlight.ambient[:] = [0.43, 0.42, 0.38]
    spec.visual.headlight.diffuse[:] = [0.45, 0.44, 0.42]
    spec.light("key_light").diffuse[:] = [0.14, 0.14, 0.13]
    for i, (x, y) in enumerate(TABLE_MARKERS):
        spec.worldbody.add_geom(name=f"desk_marker_{i}", type=mujoco.mjtGeom.mjGEOM_BOX,
                                pos=[x, y, 0.0003], size=[0.006, 0.005, 0.0002],
                                euler=[0, 0, (i % 5 - 2) * 0.21], rgba=[0.026, 0.024, 0.021, 1],
                                contype=0, conaffinity=0)


def create_simulation(*, match_dataset=False):
    spec = mujoco.MjSpec.from_file(str(MODEL_FILE))
    spec.body("base").pos[2] = 0.02137
    spec.geom("table_top").size[:2] = [0.62, 0.50]
    if match_dataset:
        _add_table_appearance(spec)
    for name in ("red_ball", "green_ball", "yellow_ball"):
        spec.delete(spec.body(name))
    spec.body("blue_ball").pos[:] = [-0.311163, 0.222834, 0.0165]
    ball = spec.geom("blue_ball_geom")
    ball.rgba[:] = [0.06, 0.10, 0.34, 1]
    if match_dataset:
        _set_ball_appearance(spec, ball)
    ball.condim = 6
    ball.friction[:] = [1.6, 0.04, 0.01]
    ball.solref[:] = [0.009, 1]
    for pad in ("fixed_finger_pad", "moving_finger_pad"):
        spec.geom(pad).solref[:] = [0.009, 1]

    # Fit a round, shallow bowl to the release area of the reference motion.
    bowl = spec.body("drop_box")
    bowl.pos[:] = [-0.269, -0.046, 0]
    for geom in list(bowl.geoms):
        spec.delete(geom)
    bowl_color = [0.10, 0.23, 0.23, 1] if match_dataset else [0.12, 0.27, 0.28, 1]
    rim_radius = 0.085 if match_dataset else 0.073
    side_width = 0.0175 if match_dataset else 0.015
    bowl.add_geom(type=mujoco.mjtGeom.mjGEOM_CYLINDER, name="bowl_floor",
                  pos=[0, 0, 0.004], size=[rim_radius - 0.004, 0.004, 0], rgba=bowl_color)
    for i in range(16):
        angle = math.tau * i / 16
        bowl.add_geom(type=mujoco.mjtGeom.mjGEOM_BOX, name=f"bowl_side_{i}",
                      pos=[rim_radius * math.cos(angle), rim_radius * math.sin(angle), 0.027],
                      euler=[0, 0, angle], size=[0.006, side_width, 0.022],
                      rgba=bowl_color, group=3 if match_dataset else 0)

    desk = spec.camera("overhead_camera")
    wrist = spec.camera("wrist_camera")
    if match_dataset:
        _add_bowl_appearance(spec, bowl, bowl_color)
        # Fit both projections to table, object and jaw landmarks across episode 230.
        spec.body("overhead_camera_rig").pos[:] = [-0.217864, -0.394406, 0.385554]
        _set_camera(desk, [0, 0, 0], [0.880458, 0.412748, 0.233309, -0.471029, 0.705333, 0.529752],
                    505.378, [-60.0, -1.461])
        _set_camera(wrist, [0.001269, 0.042, -0.041743],
                    [0.984909, 0.073984, -0.156461, -0.118025, 0.948324, -0.294536], 483.107, [46.0, 46.0])
    else:
        spec.body("overhead_camera_rig").pos[:] = [-0.2324, -0.4906, 0.5890]
        desk.alt.type = mujoco.mjtOrientation.mjORIENTATION_XYAXES
        desk.alt.xyaxes[:] = [0.854378, 0.494643, 0.159267, -0.508741, 0.733711, 0.450389]
        desk.fovy = 46.25
        wrist.pos[:] = [0.009, 0.050, -0.037]
        wrist.alt.xyaxes[:] = [1, 0, 0, 0, 0.939693, -0.342020]
        wrist.fovy = 76
    for name in ("overhead_camera_housing", "overhead_camera_lens", "wrist_camera_housing", "wrist_camera_lens"):
        spec.delete(spec.geom(name))
    for material in spec.materials:
        if material.rgba[0] > 0.9:
            material.rgba[:] = [0.13, 0.13, 0.15, 1]

    pose = dict(zip(JOINT_NAMES, ZERO_RAD + RAD_PER_UNIT * RECORDED_START))
    return Simulation("local", model=spec.compile(), ready_pose=pose)
