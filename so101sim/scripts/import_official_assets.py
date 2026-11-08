#!/usr/bin/env python3
"""Replace generated simplified proxy STLs with original SO-101 STL meshes."""
import argparse
import shutil
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
ROBOT=ROOT/'models/SO101/so101_new_calib.xml'
TARGET=ROOT/'models/SO101/assets'
needed=sorted({x.get('file') for x in ET.parse(ROBOT).getroot().iter('mesh') if x.get('file')})
ap=argparse.ArgumentParser(description='Replace all stand-in STL assets with authentic SO-101 model meshes')
ap.add_argument('--source',required=True,help='Original Simulation/SO101/assets folder')
a=ap.parse_args()
src=Path(a.source).expanduser().resolve()
if not src.is_dir():ap.error('Not a folder: '+str(src))
missing=[x for x in needed if not (src/x).is_file()]
if missing:ap.error('Official source is missing: '+', '.join(missing))
backup=TARGET/'proxy_meshes_backup'
backup.mkdir(exist_ok=True)
for name in needed:
    target=TARGET/name
    if target.is_file() and not (backup/name).exists(): shutil.copy2(target,backup/name)
    shutil.copy2(src/name,target)
(TARGET/'OFFICIAL_ASSETS_INSTALLED.txt').write_text('Copied mesh files from '+str(src)+'\n',encoding='utf8')
print('COPIED',len(needed),'official meshes into',TARGET)
print('Proxy meshes backed up at:', backup)
print('Next: python self_test.py && python app.py --mode local')
