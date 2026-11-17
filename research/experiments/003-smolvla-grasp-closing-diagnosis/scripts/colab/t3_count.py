import subprocess
print("RUNNING=" + subprocess.run("ps aux | grep -c '[t]3_rollout'", shell=True, capture_output=True, text=True).stdout.strip())
print("DONE=" + subprocess.run("ls /content/runs/t3fix-*/summary.json 2>/dev/null | wc -l", shell=True, capture_output=True, text=True).stdout.strip())
print("NOISEERR=" + subprocess.run("grep -c 'looks like noise' /content/t3_fix.log", shell=True, capture_output=True, text=True).stdout.strip())
