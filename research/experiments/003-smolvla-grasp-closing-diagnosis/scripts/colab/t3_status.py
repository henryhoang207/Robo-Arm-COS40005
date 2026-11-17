import subprocess
print(subprocess.run("ps aux | grep -c '[t]3_rollout'; ls /content/runs 2>/dev/null; "
                     "for f in /content/runs/*/summary.json; do cat $f; echo; done 2>/dev/null; "
                     "tail -3 /content/t3.log 2>/dev/null",
                     shell=True, capture_output=True, text=True).stdout)
