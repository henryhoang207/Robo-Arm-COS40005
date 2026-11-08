#!/usr/bin/env python3
"""Collect E3 (scene), E4 (web/camera), E5 (integration smoke test)
from SO101 Unified Simulation. Read-only with respect to app.py, MJCF, robot
control and VENTUNO Q. It never sends POST /api/action.

Copy this script to: so101sim/evidence/capture_E3_E5.py
With `python app.py --mode local` running in another WSL terminal:
    python evidence/capture_E3_E5.py
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

PROJECT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT / 'evidence'
E3 = OUTPUT / 'E3'
E4 = OUTPUT / 'E4'
E5 = OUTPUT / 'E5'
BASE = 'http://127.0.0.1:8000'
JOINTS = ('shoulder_pan','shoulder_lift','elbow_flex','wrist_flex','wrist_roll','gripper')
OBJECTS = ('red_ball','green_ball','blue_ball','yellow_ball','drop_box')
CAMERAS = ('overhead_camera','wrist_camera')


def save_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def http_get(path: str) -> tuple[int, bytes, str]:
    request = Request(BASE + path, headers={'Cache-Control':'no-store'})
    try:
        with urlopen(request, timeout=8) as response:
            return response.status, response.read(), response.headers.get('Content-Type','')
    except HTTPError as exc:
        return exc.code, exc.read(), exc.headers.get('Content-Type','')


def run_test(args: list[str], destination: Path) -> bool:
    proc = subprocess.run([sys.executable,*args], cwd=PROJECT, capture_output=True, text=True)
    text = '$ ' + ' '.join([sys.executable,*args]) + '\n' + proc.stdout + proc.stderr + '\nexit_code=' + str(proc.returncode) + '\n'
    destination.write_text(text,encoding='utf-8')
    return proc.returncode == 0


def main() -> int:
    for dest in (E3,E4,E5): dest.mkdir(parents=True,exist_ok=True)
    now = datetime.now().astimezone().isoformat(timespec='seconds')
    report = {'captured_at':now, 'project_path':str(PROJECT),
              'scope':'LOCAL WSL2 MuJoCo simulation, NOT validated physical VENTUNO Q or STM32 firmware',
              'checks':{}, 'notes':[]}
    chk = report['checks']
    scene=PROJECT/'models'/'SO101'/'workspace.xml'
    robot=PROJECT/'models'/'SO101'/'so101_new_calib.xml'
    pose_path=PROJECT/'ready_pose.json'
    for path in (scene,robot,pose_path):
        if not path.is_file():
            print('ERROR: missing',path)
            return 2
    # E3: XML, model component inventory, pose and reproducibility hashes.
    w=ET.parse(scene).getroot()
    r=ET.parse(robot).getroot()
    joint_in_model={j.get('name') for j in r.iter('joint')}
    ws_bodies={b.get('name') for b in w.iter('body')}
    all_cameras={c.get('name') for tree in (w,r) for c in tree.iter('camera')}
    pose=json.loads(pose_path.read_text(encoding='utf-8'))['joints']
    scene_includes=w.find("include[@file='so101_new_calib.xml']") is not None
    geometry_files={m.get('file') for m in r.iter('mesh') if m.get('file')}
    asset_dir=PROJECT/'models'/'SO101'/'assets'
    missing_meshes=sorted(x for x in geometry_files if not (asset_dir/x).is_file())
    inventory={'scene_name':w.get('model'), 'scene_path':str(scene.relative_to(PROJECT)),
               'includes_robot_model':scene_includes,
               'workspace_bodies':sorted(x for x in ws_bodies if x),
               'required_objects':list(OBJECTS),
               'objects_present':{x:x in ws_bodies for x in OBJECTS},
               'required_cameras':list(CAMERAS),
               'camera_elements_present':{x:x in all_cameras for x in CAMERAS},
               'robot_joints_present':{x:x in joint_in_model for x in JOINTS},
               'ready_pose_rad':pose,
               'required_stl_count':len(geometry_files),
               'missing_mesh_files':missing_meshes,
               'mesh_import_marker_present':(asset_dir/'OFFICIAL_ASSETS_INSTALLED.txt').exists(),
               'caution':'Presence of STL and camera definitions alone does not establish physical grasp accuracy.'}
    chk['E3_scene_includes_so101_model']=scene_includes
    chk['E3_four_balls_and_tray']=all(inventory['objects_present'].values())
    chk['E3_two_cameras_declared']=all(inventory['camera_elements_present'].values())
    chk['E3_six_joints_declared']=all(inventory['robot_joints_present'].values())
    chk['E3_all_mesh_paths_resolve']=not missing_meshes
    try:
        import mujoco
        m=mujoco.MjModel.from_xml_path(str(scene))
        actuators=tuple(mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_ACTUATOR,i) for i in range(m.nu))
        chk['E3_six_correct_actuators_compiled']=actuators==JOINTS
        camera_parent={}
        for name in CAMERAS:
            cid=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_CAMERA,name)
            camera_parent[name]=(mujoco.mj_id2name(m,mujoco.mjtObj.mjOBJ_BODY,int(m.cam_bodyid[cid])) if cid>=0 else None)
        inventory['compiled_actuators']=list(actuators)
        inventory['camera_parent_body']=camera_parent
        chk['E3_wrist_camera_attached_to_gripper']=camera_parent.get('wrist_camera')=='gripper'
        in_range={}
        for name in JOINTS:
            jid=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_JOINT,name)
            aid=mujoco.mj_name2id(m,mujoco.mjtObj.mjOBJ_ACTUATOR,name)
            val=float(pose[name]);lo=max(m.jnt_range[jid,0],m.actuator_ctrlrange[aid,0]);hi=min(m.jnt_range[jid,1],m.actuator_ctrlrange[aid,1])
            in_range[name]=bool(lo<=val<=hi)
        inventory['ready_pose_in_limits']=in_range
        chk['E3_ready_pose_within_joint_and_actuator_limits']=all(in_range.values())
    except (ImportError,RuntimeError,ValueError,KeyError) as exc:
        chk['E3_six_correct_actuators_compiled']=False
        chk['E3_wrist_camera_attached_to_gripper']=False
        chk['E3_ready_pose_within_joint_and_actuator_limits']=False
        report['notes'].append('Model compile or pose check failed: '+repr(exc))
    save_json(E3/'E3_scene_inventory.json',inventory)
    with (E3/'E3_file_hashes.sha256').open('w',encoding='utf-8') as f:
        for p in (scene,robot,pose_path):
            f.write(sha256(p.read_bytes()).hexdigest()+'  '+str(p.relative_to(PROJECT))+'\n')
    # E4: capture HTTP state and live JPEGs; do not send robot motion commands.
    try:
        status, raw, content_type=http_get('/api/state')
        state=json.loads(raw.decode('utf-8'))
        save_json(E4/'E4_api_state.json',state)
        chk['E4_http_state_ok']=status==200 and len(state.get('joint_positions',[]))==6
        chk['E4_app_in_local_mode']=state.get('mode')=='local'
        cam_result={}
        from PIL import Image
        for camera in ('overhead','wrist'):
            saved=False
            for attempt in range(8):
                code, bytes_, mime=http_get('/api/camera/'+camera)
                if code==200 and bytes_[:3]==b'\xff\xd8\xff':
                    img=Image.open(BytesIO(bytes_));size=img.size;img.verify()
                    out=E4/('E4_'+camera+'.jpg');out.write_bytes(bytes_)
                    cam_result[camera]={'http_status':code,'content_type':mime,'pixel_size':list(size), 'bytes':len(bytes_), 'filename':out.name}
                    saved=True
                    break
                time.sleep(0.5)
            if not saved:
                cam_result[camera]={'http_status':code,'content_type':mime,'error':bytes_[:300].decode('utf8',errors='replace')}
            chk['E4_'+camera+'_valid_JPEG']=saved
        save_json(E4/'E4_camera_validation.json',cam_result)
        if state.get('camera_error'):
            report['notes'].append('MuJoCo camera_error: '+str(state['camera_error']))
    except (URLError,TimeoutError,ValueError,KeyError,ImportError) as exc:
        chk['E4_http_state_ok']=False
        chk['E4_app_in_local_mode']=False
        for camera in ('overhead','wrist'):chk['E4_'+camera+'_valid_JPEG']=False
        report['notes'].append('HTTP/camera check failed: '+repr(exc))
    # E5: independent, repeatable acceptance checks. No extra robot motion.
    chk['E5_self_test_passed']=run_test(['self_test.py'],E5/'E5_self_test.log')
    chk['E5_six_unit_tests_passed']=run_test(['-m','unittest','discover','-s','tests','-v'],E5/'E5_unit_tests.log')
    e2=OUTPUT/'E2'/'E2_report.json'
    if e2.exists():
        try:
            e2_result=json.loads(e2.read_text(encoding='utf8'))
            report['separate_E2_local_motion_evidence']=e2_result.get('result')
        except (ValueError,OSError) as exc:report['notes'].append('E2_report.json unreadable: '+repr(exc))
    else:
        report['notes'].append('E2_report.json not found; E2 local motion evidence must be collected separately.')
    ok=all(chk.values())
    report['overall']='PASS' if ok else 'NEEDS_REVIEW'
    save_json(E5/'E5_acceptance_summary.json',report)
    with (E5/'E5_acceptance.log').open('w',encoding='utf8') as f:
        f.write('SO101 unified local acceptance smoke checks\nDate: '+now+'\n')
        for name,val in chk.items(): f.write(('PASS' if val else 'FAIL')+'  '+name+'\n')
        f.write('OVERALL: '+report['overall']+'\n')
        f.write('Scope: local simulator only, no physical IQ8/STM32/servo-grasp confirmation.\n')
    print('Evidence folders:',E3,E4,E5,sep='\n  ')
    for name,val in chk.items():print(('PASS' if val else 'FAIL'),name)
    print('OVERALL:', report['overall'])
    print('No action commands were sent; no project source/MJCF files were modified.')
    return 0 if ok else 1

if __name__=='__main__':
    try:sys.exit(main())
    except Exception as exc:
        print('E3-E5 CAPTURE FAILED:',type(exc).__name__,str(exc),file=sys.stderr)
        sys.exit(2)
