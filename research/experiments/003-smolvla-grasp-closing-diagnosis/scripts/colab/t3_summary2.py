import glob, json, subprocess
import numpy as np
rs = [json.load(open(f)) for f in sorted(glob.glob("/content/runs/t3-big-noisecpu-*/summary.json"))]
rs.sort(key=lambda r: r["seed"])
near = [r for r in rs if r["closest_cm"] < 5]
print(f"runs {len(rs)} | reached<5cm {len(near)} | any pad {sum(r['max_pads']>0 for r in rs)} | both pads "
      f"{sum(r['steps_both_pads']>0 for r in rs)} | lift>5 {sum(r['peak_lift_cm']>5 for r in rs)} | in bowl "
      f"{sum(r['in_bowl_end'] for r in rs)} | limited {sum(r['limited_targets'] for r in rs)}")
print("closest per seed:", [r["closest_cm"] for r in rs])
print("dz at closest (reached):", [r["closest_offset_cm_xyz"][2] for r in near])
print("min grip within 5cm (reached):", [r["min_grip_cmd_within_5cm"] for r in near])
print("closest step (reached):", [r["closest_step"] for r in near])
print(subprocess.run("tail -2 /content/t3_cpunoise.log | grep -v -i egl", shell=True, capture_output=True, text=True).stdout)
subprocess.run("cd /content && tar czf t3_runs.tgz runs/*/summary.json runs/*/steps.jsonl", shell=True)
