import glob, json, subprocess
import numpy as np
rows = [json.load(open(f)) for f in glob.glob("/content/runs/t3fix-*/summary.json")]
for look in ("small", "big"):
    rs = sorted([r for r in rows if r["look"] == look], key=lambda r: r["seed"])
    near = [r for r in rs if r["closest_cm"] < 5]
    dz = [r["closest_offset_cm_xyz"][2] for r in near]
    grip = [r["min_grip_cmd_within_5cm"] for r in near if r["min_grip_cmd_within_5cm"] is not None]
    print(f"{look:5s}: runs {len(rs)} | reached<5cm {len(near)} | any pad {sum(r['max_pads']>0 for r in rs)} | "
          f"both pads {sum(r['steps_both_pads']>0 for r in rs)} | lift>5cm {sum(r['peak_lift_cm']>5 for r in rs)} | "
          f"in bowl {sum(r['in_bowl_end'] for r in rs)} | closest median {np.median([r['closest_cm'] for r in rs]):.1f} | "
          f"dz median (reached) {np.median(dz) if dz else float('nan'):.1f} | min grip median (reached) "
          f"{np.median(grip) if grip else float('nan'):.1f} | peak lift max {max(r['peak_lift_cm'] for r in rs):.1f}")
    print("   closest:", [r["closest_cm"] for r in rs])
    print("   dz     :", [r["closest_offset_cm_xyz"][2] for r in rs])
print(subprocess.run("grep -c 'looks like noise' /content/t3_fix.log; grep -c Traceback /content/t3_fix.log",
                     shell=True, capture_output=True, text=True).stdout)
subprocess.run("cd /content && tar czf t3fix.tgz runs/t3fix-*/summary.json runs/t3fix-*/steps.jsonl", shell=True)
