#Requires -Version 5.1
# AudioPipeline Pro — Full build + installer
# Usage: powershell -ExecutionPolicy Bypass -File build_installer.ps1

param([switch]$SkipPublish)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent

function Step($msg) { Write-Host "`n==> $msg" -ForegroundColor Cyan }
function OK($msg)   { Write-Host "    OK: $msg" -ForegroundColor Green }
function Fail($msg) { Write-Host "    FAIL: $msg" -ForegroundColor Red; exit 1 }

# 1. Publish .NET app
if (-not $SkipPublish) {
    Step "Publishing .NET app..."
    $pubDir = Join-Path $root "publish\dotnet"
    Set-Location (Join-Path $root "AudioPipeline.UI")
    dotnet publish AudioPipeline.UI.csproj -c Release -p:PublishDir="$pubDir\" --nologo
    if ($LASTEXITCODE -ne 0) { Fail "dotnet publish failed" }
    OK "$((Get-ChildItem $pubDir -Recurse -File).Count) files published"
}

# 2. Generate WiX components
Step "Generating WiX components..."
Set-Location $PSScriptRoot
powershell -ExecutionPolicy Bypass -File generate_components.ps1
OK "Components generated"

# 3. Build MSI
Step "Building MSI..."
$msi = Join-Path $root "publish\AudioPipelinePro.msi"
wix build Product.wxs AppFiles.wxs SvcFiles.wxs `
    -ext WixToolset.UI.wixext/4.0.5 `
    -o $msi
if ($LASTEXITCODE -ne 0) { Fail "wix build failed" }

$size = [math]::Round((Get-Item $msi).Length / 1MB, 1)
OK "MSI created: $msi ($size MB)"

Step "Done! Installer is at: publish\AudioPipelinePro.msi"
