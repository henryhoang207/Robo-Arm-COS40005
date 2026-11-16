"""Paired camera snapshots: one immutable physics sample, rendered on a worker."""
from __future__ import annotations
import io
import threading
import time
from PIL import Image
from protocol import JOINT_NAMES, SCHEMA_VERSION


def capture_pair(sim, renderer, copied_data):
    started = time.monotonic()
    with sim.lock:
        sim.mj.mj_copyData(copied_data, sim.model, sim.data)
        run_id = sim.run_id
        metadata = {'schema_version': SCHEMA_VERSION, 'run_id': run_id, 'session_id': sim.session_id,
                    'captured_monotonic_ns': time.monotonic_ns(), 'captured_unix_ns': time.time_ns(),
                    'sim_time': float(sim.data.time), 'joint_names': list(JOINT_NAMES),
                    'joint_positions': sim.data.qpos[sim.qids].tolist(),
                    'joint_velocities': sim.data.qvel[sim.vids].tolist(),
                    'target_positions': sim.data.ctrl[sim.aids].tolist(),
                    'applied_sequence': sim.last_applied_sequence,
                    'completed_sequence': sim.last_completed_sequence,
                    'width': sim.settings['camera_width'], 'height': sim.settings['camera_height']}
    sim.mj.mj_forward(sim.model, copied_data)
    frames = {}
    for label, camera in (('overhead', 'overhead_camera'), ('wrist', 'wrist_camera')):
        renderer.update_scene(copied_data, camera=camera)
        pixels = renderer.render()
        output = io.BytesIO()
        Image.fromarray(pixels).save(output, format='JPEG', quality=85)
        frames[label] = output.getvalue()
    with sim.lock:
        if run_id != sim.run_id:
            return  # A reset happened during rendering; never publish old-run images.
        sim.frame_id += 1
        metadata['frame_id'] = sim.frame_id
        sim.images = frames
        sim.frame_bundle = metadata
        sim.camera_error = None
        sim.render_info['pair_render_ms'] = (time.monotonic() - started) * 1000


class CameraWorker:
    def __init__(self, sim):
        self.sim = sim
        self.stopping = threading.Event()
        self.thread = threading.Thread(target=self.run, name='cameras', daemon=True)

    def start(self):
        self.thread.start()

    def run(self):
        sim = self.sim
        renderer = None
        try:
            renderer = sim.mj.Renderer(sim.model, height=sim.settings['camera_height'],
                                       width=sim.settings['camera_width'])
            data = sim.mj.MjData(sim.model)
            from OpenGL import GL
            device = GL.glGetString(GL.GL_RENDERER)
            with sim.lock:
                sim.render_info.update(renderer=device.decode() if device else 'unknown',
                                       requested_fps=1 / sim.camera_interval)
            last = time.monotonic()
            while not self.stopping.is_set():
                started = time.monotonic()
                capture_pair(sim, renderer, data)
                now = time.monotonic()
                with sim.lock:
                    sim.render_info['actual_pair_fps'] = 1 / max(now - last, 1e-6)
                last = now
                self.stopping.wait(max(0, sim.camera_interval - (now - started)))
        except Exception as exc:
            with sim.lock:
                sim.camera_error = f'{type(exc).__name__}: {exc}'
        finally:
            if renderer is not None:
                renderer.close()

    def stop(self):
        self.stopping.set()
        self.thread.join(timeout=10)
