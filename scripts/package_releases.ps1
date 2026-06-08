$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$releaseDir = Join-Path $root "release"

New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

$windowsZip = Join-Path $releaseDir "keyboard_immulation_windows.zip"
$macosZip = Join-Path $releaseDir "keyboard_immulation_macos.zip"
$linuxZip = Join-Path $releaseDir "keyboard_immulation_linux.zip"
$androidZip = Join-Path $releaseDir "keyboard_immulation_android.zip"
$stagingDir = Join-Path $releaseDir "staging"
$windowsStaging = Join-Path $stagingDir "windows"
$desktopStaging = Join-Path $stagingDir "desktop"
$androidStaging = Join-Path $stagingDir "android"

Remove-Item $windowsZip, $macosZip, $linuxZip, $androidZip -Force -ErrorAction SilentlyContinue
Remove-Item $stagingDir -Recurse -Force -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Force -Path $windowsStaging, $desktopStaging, $androidStaging | Out-Null

$windowsExe = Get-ChildItem (Join-Path $root "dist") -Filter "*.exe" | Select-Object -First 1
if (-not $windowsExe) {
  throw "Windows executable was not found under dist"
}

Copy-Item $windowsExe.FullName (Join-Path $windowsStaging "keyboard_immulation_windows.exe")
Copy-Item (Join-Path $root "README.md") $windowsStaging

Compress-Archive -Path (Join-Path $windowsStaging "*") -DestinationPath $windowsZip

Copy-Item (Join-Path $root "keyboard_relay.py") $desktopStaging
Copy-Item (Join-Path $root "keyboard_relay_gui.pyw") $desktopStaging
Copy-Item (Join-Path $root "run.sh") $desktopStaging
Copy-Item (Join-Path $root "requirements.txt") $desktopStaging
Copy-Item (Join-Path $root "README.md") $desktopStaging

Compress-Archive -Path (Join-Path $desktopStaging "*") -DestinationPath $macosZip

Compress-Archive -Path (Join-Path $desktopStaging "*") -DestinationPath $linuxZip

Copy-Item (Join-Path $root "android") $androidStaging -Recurse
Copy-Item (Join-Path $root "README.md") $androidStaging

Compress-Archive -Path (Join-Path $androidStaging "*") -DestinationPath $androidZip

Get-ChildItem $releaseDir -Filter "keyboard_immulation_*" | Select-Object Name, Length
