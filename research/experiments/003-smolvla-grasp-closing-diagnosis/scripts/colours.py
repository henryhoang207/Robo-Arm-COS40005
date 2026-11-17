"""Median real colours of desk and bowl (frame 100 desk view) vs the sim's rendered colours, using sim masks."""
import sys
sys.path.insert(0, r"C:\RobotArm\so101sim")
import numpy as np
from PIL import Image
import desk_cleanup

real = np.load(r"C:\RobotArm\data\raw\camera_check\frame100_real.npz")["desk"]
real = np.asarray(Image.fromarray(real).resize((640, 480), Image.LANCZOS)).astype(int)
sim = desk_cleanup.create_simulation(match_dataset=True)
r = sim.mj.Renderer(sim.model, height=480, width=640)
r.update_scene(sim.data, camera="overhead_camera")
rgb = r.render().astype(int)
r.enable_segmentation_rendering()
r.update_scene(sim.data, camera="overhead_camera")
ids = r.render()[..., 0]
m = sim.model
table = ids == m.geom("table_top").id
bowl_ids = [i for i in range(m.ngeom) if m.geom(i).name.startswith(("bowl_side", "bowl_surface", "bowl_floor"))]
bowl = np.isin(ids, bowl_ids)
# Erode masks so edges and misalignment do not mix colours.
from scipy import ndimage
table = ndimage.binary_erosion(table, iterations=6)
bowl = ndimage.binary_erosion(bowl, iterations=6)
sat = (real.max(-1) - real.min(-1)) / np.maximum(real.max(-1), 1)
for name, mask, extra in (("desk", table, (real.mean(-1) > 120) & (sat < 0.25)), ("bowl", bowl, sat > 0.15)):
    rm = mask & extra
    print(f"{name}: real median RGB {np.median(real[rm], 0).astype(int).tolist()} (n={rm.sum()}), "
          f"sim median RGB {np.median(rgb[mask], 0).astype(int).tolist()} (n={mask.sum()})")
