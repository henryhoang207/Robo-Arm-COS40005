import subprocess
print(subprocess.run("grep -i -n -B2 -A2 'error\\|warn' /content/t3.log | grep -v -i egl | head -40; "
                     "python -c \"import json;c=json.load(open('/content/ckpt/pretrained_model/config.json'));"
                     "print({k:c.get(k) for k in ('device','use_amp','num_steps','chunk_size','n_action_steps')})\"",
                     shell=True, capture_output=True, text=True).stdout)
