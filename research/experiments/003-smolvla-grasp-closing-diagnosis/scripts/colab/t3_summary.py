import glob, json, subprocess
import numpy as np
rows = [json.load(open(f)) for f in sorted(glob.glob("/content/runs/t3-*-replan50/summary.json"))]
for look in ("small", "big"):
    rs = [r for r in rows if r["look"] == look]
    near = [r for r in rs if r["closest_cm"] < 5]
    dz = [r["closest_offset_cm_xyz"][2] for r in near]
    grip = [r["min_grip_cmd_within_5cm"] for r in near if r["min_grip_cmd_within_5cm"] is not None]
    print(f"{look:5s}: runs {len(rs)} | reached <5cm {len(near)} | any pad {sum(r['max_pads'] > 0 for r in rs)} | "
          f"both pads {sum(r['steps_both_pads'] > 0 for r in rs)} | lift>5cm {sum(r['peak_lift_cm'] > 5 for r in rs)} | "
          f"in bowl {sum(r['in_bowl_end'] for r in rs)} | closest median {np.median([r['closest_cm'] for r in rs]):.1f}cm | "
          f"dz at closest (reached runs) median {np.median(dz) if dz else float('nan'):.1f}cm | "
          f"min grip within 5cm median {np.median(grip) if grip else float('nan'):.1f}% | limited {sum(r['limited_targets'] for r in rs)}")
    print("   per seed closest_cm:", [r["closest_cm"] for r in sorted(rs, key=lambda r: r["seed"])])
subprocess.run("cd /content && tar czf t3_runs.tgz runs/*/summary.json runs/*/steps.jsonl", shell=True)
print(subprocess.run("ls -la /content/t3_runs.tgz; grep -ci error /content/t3.log", shell=True, capture_output=True, text=True).stdout)
