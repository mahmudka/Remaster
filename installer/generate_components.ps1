#Requires -Version 5.1
# Generates AppFiles.wxs and SvcFiles.wxs for WiX 4 installer.
param(
    [string]$PublishDir = "..\publish\dotnet",
    [string]$StemsDir   = "..\services\python_stems",
    [string]$MixDir     = "..\services\python_mix",
    [string]$VstStub    = "..\services\cpp_vst\stub_server.py"
)

$script:IdCounter = 0
function SafeId([string]$prefix) {
    $script:IdCounter++
    return "${prefix}_{0:D4}" -f $script:IdCounter
}

# ─── Recursive function: emit directories + components ───────────────────────
function Write-DirTree {
    param(
        [System.IO.DirectoryInfo]$Dir,
        [string]$RelPath,          # relative path from root source dir
        [string]$WixParentId,      # WiX Directory Id of parent
        [string]$Prefix,           # prefix for Ids
        [System.Text.StringBuilder]$Sb,
        [System.Collections.Generic.List[string]]$Refs,
        [string]$Indent = "    "
    )

    # Emit files in this directory
    foreach ($file in (Get-ChildItem $Dir.FullName -File)) {
        if ($file.Name -match '\.pyc$') { continue }
        $fileId = SafeId "F_$Prefix"
        $cmpId  = SafeId "C_$Prefix"
        $guid   = [guid]::NewGuid().ToString().ToUpper()
        $relSrc = $file.FullName  # absolute path — simplest for generated files

        [void]$Sb.AppendLine("$Indent<Component Id=""$cmpId"" Guid=""{$guid}"" Directory=""$WixParentId"">")
        [void]$Sb.AppendLine("$Indent  <File Id=""$fileId"" Source=""$relSrc"" KeyPath=""yes"" />")
        [void]$Sb.AppendLine("$Indent</Component>")
        $Refs.Add($cmpId)
    }

    # Recurse into subdirectories
    foreach ($sub in (Get-ChildItem $Dir.FullName -Directory)) {
        if ($sub.Name -match '^__pycache__$|^venv$|^\.venv$|^\.git$') { continue }
        $subRelPath = if ($RelPath) {"$RelPath`_$($sub.Name)"} else {$sub.Name}
        $subDirId   = SafeId "Dir_$Prefix"
        [void]$Sb.AppendLine("$Indent<Directory Id=""$subDirId"" Name=""$($sub.Name)"">")
        Write-DirTree -Dir $sub -RelPath $subRelPath -WixParentId $subDirId `
                      -Prefix $Prefix -Sb $Sb -Refs $Refs -Indent ($Indent + "  ")
        [void]$Sb.AppendLine("$Indent</Directory>")
    }
}

# ─── Generate AppFiles.wxs ───────────────────────────────────────────────────
Write-Host "Generating AppFiles.wxs from $PublishDir ..."
$sb   = [System.Text.StringBuilder]::new()
$refs = [System.Collections.Generic.List[string]]::new()

[void]$sb.AppendLine('<?xml version="1.0" encoding="utf-8"?>')
[void]$sb.AppendLine('<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">')
[void]$sb.AppendLine('  <Fragment>')
[void]$sb.AppendLine('    <DirectoryRef Id="APPLICATIONFOLDER">')

$pubDir = Get-Item $PublishDir
Write-DirTree -Dir $pubDir -RelPath "" -WixParentId "APPLICATIONFOLDER" `
              -Prefix "App" -Sb $sb -Refs $refs -Indent "      "

[void]$sb.AppendLine('    </DirectoryRef>')
[void]$sb.AppendLine('    <ComponentGroup Id="AppFiles">')
foreach ($r in $refs) { [void]$sb.AppendLine("      <ComponentRef Id=""$r"" />") }
[void]$sb.AppendLine('    </ComponentGroup>')
[void]$sb.AppendLine('  </Fragment>')
[void]$sb.AppendLine('</Wix>')
Set-Content -Path "AppFiles.wxs" -Value $sb.ToString() -Encoding UTF8
Write-Host "  -> $($refs.Count) components"

# ─── Generate SvcFiles.wxs ───────────────────────────────────────────────────
Write-Host "Generating SvcFiles.wxs ..."
$sb2   = [System.Text.StringBuilder]::new()
$refs2 = [System.Collections.Generic.List[string]]::new()

[void]$sb2.AppendLine('<?xml version="1.0" encoding="utf-8"?>')
[void]$sb2.AppendLine('<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">')
[void]$sb2.AppendLine('  <Fragment>')

# Stems service
[void]$sb2.AppendLine('    <DirectoryRef Id="StemsSvcDir">')
Write-DirTree -Dir (Get-Item $StemsDir) -RelPath "" -WixParentId "StemsSvcDir" `
              -Prefix "Stems" -Sb $sb2 -Refs $refs2 -Indent "      "
[void]$sb2.AppendLine('    </DirectoryRef>')

# Mix service
[void]$sb2.AppendLine('    <DirectoryRef Id="MixSvcDir">')
Write-DirTree -Dir (Get-Item $MixDir) -RelPath "" -WixParentId "MixSvcDir" `
              -Prefix "Mix" -Sb $sb2 -Refs $refs2 -Indent "      "
[void]$sb2.AppendLine('    </DirectoryRef>')

# VST stub single file
$vstFile = Get-Item $VstStub
$vstGuid = [guid]::NewGuid().ToString().ToUpper()
[void]$sb2.AppendLine('    <DirectoryRef Id="VstSvcDir">')
[void]$sb2.AppendLine("      <Component Id=""C_VstStub"" Guid=""{$vstGuid}"" Directory=""VstSvcDir"">")
[void]$sb2.AppendLine("        <File Id=""F_VstStub"" Source=""$($vstFile.FullName)"" KeyPath=""yes"" />")
[void]$sb2.AppendLine("      </Component>")
[void]$sb2.AppendLine('    </DirectoryRef>')
$refs2.Add("C_VstStub")

[void]$sb2.AppendLine('    <ComponentGroup Id="SvcFiles">')
foreach ($r in $refs2) { [void]$sb2.AppendLine("      <ComponentRef Id=""$r"" />") }
[void]$sb2.AppendLine('    </ComponentGroup>')
[void]$sb2.AppendLine('  </Fragment>')
[void]$sb2.AppendLine('</Wix>')
Set-Content -Path "SvcFiles.wxs" -Value $sb2.ToString() -Encoding UTF8
Write-Host "  -> $($refs2.Count) service components"
Write-Host "Done. Now run:"
Write-Host "  wix build Product.wxs AppFiles.wxs SvcFiles.wxs -ext WixToolset.UI.wixext/4.0.5 -o ..\publish\AudioPipelinePro.msi"
