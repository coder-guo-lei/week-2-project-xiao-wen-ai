# Open Android Studio with the android/ project (workaround for Capacitor path issues)
$ErrorActionPreference = 'Stop'
$androidDir = (Resolve-Path (Join-Path $PSScriptRoot '..\android')).Path

$candidates = @(
  $env:CAPACITOR_ANDROID_STUDIO_PATH,
  "$env:ProgramFiles\Android\Android Studio\bin\studio64.exe",
  "${env:ProgramFiles(x86)}\Android\Android Studio\bin\studio64.exe",
  "$env:LOCALAPPDATA\Programs\Android Studio\bin\studio64.exe"
) | Where-Object { $_ -and (Test-Path $_) }

if (-not $candidates -or $candidates.Count -eq 0) {
  $found = Get-ChildItem -Path 'D:\', 'C:\Program Files' -Recurse -Filter 'studio64.exe' -ErrorAction SilentlyContinue -Depth 5 |
    Select-Object -First 1
  if ($found) { $candidates = @($found.FullName) }
}

if (-not $candidates -or $candidates.Count -eq 0) {
  Write-Host 'Android Studio not found. Set CAPACITOR_ANDROID_STUDIO_PATH to studio64.exe'
  Write-Host "Or open Android Studio manually: Open -> $androidDir"
  exit 1
}

$studio = $candidates[0]
Write-Host "Studio: $studio"
Write-Host "Project: $androidDir"
Start-Process -FilePath $studio -ArgumentList "`"$androidDir`""
Write-Host 'Launch requested.'
