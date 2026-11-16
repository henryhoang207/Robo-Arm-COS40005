param([string]$AppLabRoot = "$env:LOCALAPPDATA\AppLab")
# Compile-only check of the final STM32 firmware in C:\RobotArm\robo-arm\sketch.
# Never uploads anything; the board compiles and flashes it itself when you press Run in App Lab.
$ErrorActionPreference = 'Stop'
$sketch = Join-Path $PSScriptRoot '..\..\robo-arm\sketch' | Resolve-Path
$cli = Join-Path $AppLabRoot 'resources\arduino\arduino-cli\arduino-cli.exe'
$config = Join-Path $AppLabRoot 'a15\arduino-cli.yaml'
$runtime = Join-Path $PSScriptRoot '..\runtime'
New-Item -ItemType Directory -Path $runtime -Force | Out-Null
$output = Join-Path $runtime 'firmware-build'
& $cli --config-file $config compile --fqbn arduino:zephyr:ventunoq --build-path $output $sketch 2>&1 |
    Tee-Object -FilePath (Join-Path $runtime 'firmware-compile.txt')
if ($LASTEXITCODE -ne 0) { throw 'Firmware compilation failed. See SO101\runtime\firmware-compile.txt.' }
