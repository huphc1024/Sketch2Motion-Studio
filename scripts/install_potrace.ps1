$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$targetDirectory = Join-Path $projectRoot "tools\potrace"
$downloadUrl = "https://potrace.sourceforge.net/download/1.16/potrace-1.16.win64.zip"
$temporaryRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("sketch2motion-potrace-" + [Guid]::NewGuid().ToString("N"))
$archivePath = Join-Path $temporaryRoot "potrace.zip"
$extractPath = Join-Path $temporaryRoot "extracted"

New-Item -ItemType Directory -Path $temporaryRoot -Force | Out-Null
New-Item -ItemType Directory -Path $targetDirectory -Force | Out-Null

try {
    Write-Host "Downloading Potrace 1.16 for Windows x64..."
    Invoke-WebRequest -Uri $downloadUrl -OutFile $archivePath
    Expand-Archive -LiteralPath $archivePath -DestinationPath $extractPath -Force

    $binary = Get-ChildItem -LiteralPath $extractPath -Filter "potrace.exe" -File -Recurse |
        Select-Object -First 1
    if (-not $binary) {
        throw "The official archive does not contain potrace.exe."
    }

    Copy-Item -LiteralPath $binary.FullName -Destination (Join-Path $targetDirectory "potrace.exe") -Force
    $mkbitmap = Get-ChildItem -LiteralPath $extractPath -Filter "mkbitmap.exe" -File -Recurse |
        Select-Object -First 1
    if ($mkbitmap) {
        Copy-Item -LiteralPath $mkbitmap.FullName -Destination (Join-Path $targetDirectory "mkbitmap.exe") -Force
    }

    $installed = Join-Path $targetDirectory "potrace.exe"
    Write-Host "Installed: $installed"
    & $installed --version
}
finally {
    $resolvedTemp = [System.IO.Path]::GetFullPath($temporaryRoot)
    $systemTemp = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath())
    if ($resolvedTemp.StartsWith($systemTemp, [System.StringComparison]::OrdinalIgnoreCase) -and
        (Test-Path -LiteralPath $resolvedTemp)) {
        Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
    }
}
