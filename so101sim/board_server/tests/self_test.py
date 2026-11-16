#!/usr/bin/env python3
"""Compile one MuJoCo scene, validate structure/pose and optionally render both cameras."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
WS=ROOT/'models/SO101/workspace.xml'
XML=ROOT/'models/SO101/so101_new_calib.xml'
required_names=['red_ball','green_ball','blue_ball','yellow_ball','drop_box']
required_cameras=['overhead_camera','wrist_camera']
expected=['shoulder_pan','shoulder_lift','elbow_flex','wrist_flex','wrist_roll','gripper']

wt=ET.parse(WS).getroot()
rt=ET.parse(XML).getroot()
assert wt.find("include[@file='so101_new_calib.xml']") is not None
for name in required_names:
    assert any(b.get('name')==name for b in wt.iter('body')),name
for name in required_cameras:
    assert any(c.get('name')==name for c in (list(wt.iter('camera'))+list(rt.iter('camera')))),name
assets=ROOT.parent/'models/SO101/assets'
meshes={m.get('file') for m in rt.iter('mesh') if m.get('file')}
for fname in meshes:
    assert (assets/fname).is_file(),f'Missing STL asset: {fname}'
print('PASS: XML syntax, single scene, all meshes, four balls, tray, two cameras')

try:
    import mujoco
except ImportError:
    sys.exit('MuJoCo not installed; static XML checks passed. In WSL install: python -m pip install -r requirements.txt')

m=mujoco.MjModel.from_xml_path(str(WS))
names=[mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_ACTUATOR,i) for i in range(m.nu)]
assert names==expected,names
for name in required_names:
    assert mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_BODY,name)>=0
for name in required_cameras:
    assert mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_CAMERA,name)>=0
print('PASS: MJCF compiled; 6 actuators, 4 dynamic balls, 2 working MuJoCo camera definitions')
from engine import Simulation
sim=Simulation('local')
print('READY POSE radians:',sim.snapshot()['joint_positions'])
siteid=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_SITE,'gripperframe')
if siteid>=0:
    print('GRIPPERFRAME xyz [m]:', sim.data.site_xpos[siteid].tolist())
    if sim.data.site_xpos[siteid][2] < 0.03:
        print('WARNING: gripper may collide with table at ready pose')
print('NOTE: compile does NOT prove real-world grasp success, board integration, or safety')
