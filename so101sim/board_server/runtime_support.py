"""Runtime paths, WSL graphics selection, model identity and nonblocking run logs."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import queue
import threading
import time

ROOT = Path(__file__).resolve().parent          # so101sim/board_server
SIM_ROOT = ROOT.parent                          # so101sim
RUNTIME = SIM_ROOT / 'runtime'                  # logs, session token, board-runs/, runs/
ASSETS = SIM_ROOT / 'models/SO101/assets'       # the 13 STL are shared with the local-mode scene


def configure_graphics():
    # Apply to noninteractive USB launches too; respect explicit user overrides.
    if Path('/dev/dxg').exists():
        os.environ.setdefault('GALLIUM_DRIVER', 'd3d12')
        os.environ.setdefault('MESA_D3D12_DEFAULT_ADAPTER_NAME', 'NVIDIA')
    os.environ.setdefault('MUJOCO_GL', 'egl')


def model_identity():
    files = [ROOT / 'models/SO101/workspace.xml', ROOT / 'models/SO101/so101_new_calib.xml',
             ROOT / 'ready_pose.json', ROOT / 'settings.json']
    files += sorted(ASSETS.glob('*.stl'))
    digest = hashlib.sha256()
    hashes = {}
    for path in files:
        value = hashlib.sha256(path.read_bytes()).hexdigest()
        # Same names as before the 11/11 move, so model_sha256 stays comparable with the 09/11 runs.
        name = ('models/SO101/assets/' + path.name) if path.parent == ASSETS else path.relative_to(ROOT).as_posix()
        hashes[name] = value
        digest.update(f'{name}:{value}\n'.encode())
    return {'model_sha256': digest.hexdigest(), 'files': hashes,
            'contact_model': 'SO101 finger collision approximation v1; simulated contact, not hardware calibration'}


class Recorder:
    """One writer thread; filesystem work never runs in the physics loop."""
    def __init__(self, directory):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.pending = queue.Queue(maxsize=4096)
        self.dropped = 0
        self.error = None
        self.worker = threading.Thread(target=self._write, name='run-log', daemon=True)
        self.worker.start()

    def emit(self, run_id, kind, **fields):
        item = {'event': kind, 'run_id': run_id, 'wall_time_unix_ns': time.time_ns(),
                'server_monotonic_ns': time.monotonic_ns(), **fields}
        try:
            self.pending.put_nowait((run_id, item))
        except queue.Full:
            self.dropped += 1

    def _write(self):
        stream = None
        current = None
        try:
            while True:
                entry = self.pending.get()
                if entry is None:
                    break
                run_id, event = entry
                try:
                    if current != run_id or stream is None:
                        if stream:
                            stream.close()
                        stream = None
                        stream = (self.directory / f'{run_id}.jsonl').open('a', encoding='utf8')
                        current = run_id
                    stream.write(json.dumps(event, ensure_ascii=False, allow_nan=False) + '\n')
                    stream.flush()
                except (OSError, ValueError, TypeError) as exc:
                    self.error = str(exc)
        finally:
            if stream:
                stream.close()

    def close(self):
        self.pending.put(None)
        self.worker.join(timeout=10)
