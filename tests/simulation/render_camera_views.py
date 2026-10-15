from pathlib import Path

import mujoco
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATH = (
    REPO_ROOT
    / "SO-ARM100-main"
    / "Simulation"
    / "SO101"
    / "scene.xml"
)

OUTPUT_DIR = (
    REPO_ROOT
    / "research"
    / "results"
    / "SO101-49"
)

CAMERA_NAMES = [
    "top_camera",
    "wrist_cam_view",
]

IMAGE_WIDTH = 640
IMAGE_HEIGHT = 480


def main():
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(
            f"MuJoCo scene not found: {MODEL_PATH}"
        )

    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)

    mujoco.mj_resetData(model, data)
    mujoco.mj_forward(model, data)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    renderer = mujoco.Renderer(
        model,
        height=IMAGE_HEIGHT,
        width=IMAGE_WIDTH,
    )

    try:
        for camera_name in CAMERA_NAMES:
            camera_id = mujoco.mj_name2id(
                model,
                mujoco.mjtObj.mjOBJ_CAMERA,
                camera_name,
            )

            if camera_id < 0:
                raise RuntimeError(
                    f"Camera not found: {camera_name}"
                )

            renderer.update_scene(
                data,
                camera=camera_name,
            )
            pixels = renderer.render()

            output_filename = {
                "top_camera": "so101_top_camera.png",
                "wrist_cam_view": "so101_wrist_camera.png",
            }

            output_path = OUTPUT_DIR / output_filename[camera_name]

            Image.fromarray(pixels).save(output_path)

            print(f"CAMERA RENDER: PASS - {camera_name}")
            print(f"IMAGE SAVED: {output_path}")

    finally:
        renderer.close()

    print("CAMERA RENDER TEST: PASS")


if __name__ == "__main__":
    main()
