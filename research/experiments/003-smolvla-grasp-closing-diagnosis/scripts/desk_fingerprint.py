"""Fingerprint the episode-230 desk-cleanup scene of one checkout: model, cameras, objects, start state, short rollout."""
import hashlib, sys
import numpy as np
sys.path.insert(0, sys.argv[1])
import mujoco, desk_cleanup

out = {}
for match in (False, True):
    sim = desk_cleanup.create_simulation(match_dataset=match)
    m, d = sim.model, sim.data
    h = hashlib.sha256()
    for arr in (m.body_pos, m.body_quat, m.geom_size, m.geom_pos, m.geom_friction, m.geom_rgba,
                m.cam_pos, m.cam_quat, m.cam_fovy, m.actuator_gainprm, m.actuator_forcerange,
                m.jnt_range, m.opt.timestep * np.ones(1), d.qpos):
        h.update(np.ascontiguousarray(arr, dtype=np.float64).tobytes())
    bodies = [m.body(i).name for i in range(m.nbody)]
    cams = [m.camera(i).name for i in range(m.ncam)]
    for _ in range(500):
        sim.step()
    out[match] = (h.hexdigest()[:16], hashlib.sha256(np.round(d.qpos, 9).tobytes()).hexdigest()[:16])
    print(f"match_dataset={match}: model+start={out[match][0]} after500steps={out[match][1]} "
          f"nbody={m.nbody} cams={cams}")
    print("   objects:", [b for b in bodies if any(k in b for k in ('ball', 'bowl', 'box'))])
