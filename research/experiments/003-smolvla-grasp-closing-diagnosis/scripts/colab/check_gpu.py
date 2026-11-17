import subprocess, sys
print(subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv"], capture_output=True, text=True).stdout)
print(sys.version)
print(subprocess.run(["df", "-h", "/content"], capture_output=True, text=True).stdout)
