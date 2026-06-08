$ErrorActionPreference = "Stop"

$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$releaseDir = Join-Path $root "release"

New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

$windowsExeAsset = Join-Path $releaseDir "keyboard_simulation_windows.exe"
$macosReadme = Join-Path $releaseDir "keyboard_simulation_macos.requires-macos-build.txt"
$linuxReadme = Join-Path $releaseDir "keyboard_simulation_linux.requires-linux-build.txt"
$androidReadme = Join-Path $releaseDir "keyboard_simulation_android.requires-android-build.txt"

Remove-Item (Join-Path $releaseDir "keyboard_simulation_*") -Force -ErrorAction SilentlyContinue

$windowsExe = Get-ChildItem (Join-Path $root "dist") -Filter "*.exe" | Select-Object -First 1
if (-not $windowsExe) {
  throw "Windows executable was not found under dist"
}

Copy-Item $windowsExe.FullName $windowsExeAsset

Set-Content -Path $macosReadme -Encoding UTF8 -Value "Build keyboard_simulation_macos.dmg on macOS with GitHub Actions or PyInstaller."
Set-Content -Path $linuxReadme -Encoding UTF8 -Value "Build keyboard_simulation_linux on Linux with GitHub Actions or PyInstaller."
Set-Content -Path $androidReadme -Encoding UTF8 -Value "Build keyboard_simulation_android.apk with Android SDK/Gradle or GitHub Actions."

Get-ChildItem $releaseDir -Filter "keyboard_simulation_*" | Select-Object Name, Length
