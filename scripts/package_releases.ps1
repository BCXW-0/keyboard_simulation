$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$releaseDir = Join-Path $root "release"
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
Remove-Item (Join-Path $releaseDir "keyboard_simulation_*") -Force -ErrorAction SilentlyContinue
$windowsExe = Get-ChildItem (Join-Path $root "dist") -Filter "*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
if ($windowsExe) {
  Copy-Item $windowsExe.FullName (Join-Path $releaseDir "keyboard_simulation_windows.exe") -Force
  Write-Host "Windows asset ready"
} else {
  Set-Content -Path (Join-Path $releaseDir "keyboard_simulation_windows.requires-local-build.txt") -Encoding UTF8 -Value "Build with PyInstaller on Windows first."
}
Set-Content -Path (Join-Path $releaseDir "keyboard_simulation_macos.requires-macos-build.txt") -Encoding UTF8 -Value "Build keyboard_simulation_macos.dmg on macOS."
Set-Content -Path (Join-Path $releaseDir "keyboard_simulation_linux.requires-linux-build.txt") -Encoding UTF8 -Value "Build keyboard_simulation_linux on Linux."
Set-Content -Path (Join-Path $releaseDir "keyboard_simulation_android.requires-android-build.txt") -Encoding UTF8 -Value "Build keyboard_simulation_android.apk with Android SDK/Gradle."
Get-ChildItem $releaseDir -Filter "keyboard_simulation_*" | Select-Object Name, Length
