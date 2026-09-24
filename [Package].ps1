# Run from any directory. Builds the Windows log viewer before packaging.
# The manifest is the source of truth for the release version.
# Requires Windows PowerShell 5.1 or later.
[CmdletBinding()]
param([string]$Python = 'python')

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$temporaryPath = $null

try {
    $addonPath = Join-Path $PSScriptRoot 'addon'
    $manifestPath = Join-Path $addonPath 'blender_manifest.toml'
    $manifest = Get-Content -LiteralPath $manifestPath -Raw
    # Only look at top-level fields, before the first TOML table.
    $metadata = ($manifest -split '(?m)^\s*\[', 2)[0]
    $versionMatch = [regex]::Match($metadata, '(?m)^version\s*=\s*"(?<version>\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)"\s*(?:#.*)?$')
    if (-not $versionMatch.Success) {
        throw 'No valid version was found in addon/blender_manifest.toml.'
    }
    if (-not (Test-Path -LiteralPath (Join-Path $addonPath '__init__.py') -PathType Leaf)) {
        throw 'The addon folder must contain __init__.py.'
    }

    $version = $versionMatch.Groups['version'].Value
    & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot '[Build Log Window].ps1') -Python $Python
    if ($LASTEXITCODE -ne 0) { throw 'Log window build failed; release ZIP was not replaced.' }
    $bundlePath = Join-Path $PSScriptRoot 'dist\StellarBladeExportLog'
    $releasePath = Join-Path $PSScriptRoot 'releases'
    [System.IO.Directory]::CreateDirectory($releasePath) | Out-Null
    $archivePath = Join-Path $releasePath "stellar-blade-fbx-exporter-v$version.zip"
    $temporaryPath = Join-Path $releasePath ('.package-' + [guid]::NewGuid().ToString('N') + '.tmp')

    Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
    $archive = [System.IO.Compression.ZipFile]::Open($temporaryPath, [System.IO.Compression.ZipArchiveMode]::Create)
    $fileCount = 0
    try {
        foreach ($file in (Get-ChildItem -LiteralPath $addonPath -File -Recurse -Force | Sort-Object FullName)) {
            $relativePath = $file.FullName.Substring($addonPath.Length + 1).Replace('\', '/')
            if ($relativePath -eq 'stellar_blade_log_window.ps1' -or $relativePath.StartsWith('log_window/')) {
                continue
            }
            # Match the manifest's current build exclusions, plus compiled Python files.
            if ($relativePath -match '(^|/)(\.[^/]*|__pycache__)(/|$)' -or
                $relativePath -match '\.(zip|pyc|pyo)$' -or
                ($file.Attributes -band [System.IO.FileAttributes]::Hidden)) {
                continue
            }
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive, $file.FullName, $relativePath, [System.IO.Compression.CompressionLevel]::Optimal
            ) | Out-Null
            $fileCount++
        }
        # Include the complete runtime bundle, including dependency ZIPs and bytecode.
        # Applying add-on source exclusions here would break the standalone viewer.
        foreach ($file in (Get-ChildItem -LiteralPath $bundlePath -File -Recurse -Force | Sort-Object FullName)) {
            $relativePath = 'log_window/' + $file.FullName.Substring($bundlePath.Length + 1).Replace('\', '/')
            [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
                $archive, $file.FullName, $relativePath, [System.IO.Compression.CompressionLevel]::Optimal
            ) | Out-Null
            $fileCount++
        }
    }
    finally {
        $archive.Dispose()
    }

    # Finish the ZIP before replacing a previous build of the same version.
    if ([System.IO.File]::Exists($archivePath)) {
        [System.IO.File]::Replace($temporaryPath, $archivePath, [NullString]::Value)
    }
    else {
        [System.IO.File]::Move($temporaryPath, $archivePath)
    }
    Write-Host "Created $archivePath ($fileCount files)."
}
catch {
    Write-Error -Message "Packaging failed: $($_.Exception.Message)" -ErrorAction Continue
    exit 1
}
finally {
    if ($temporaryPath -and (Test-Path -LiteralPath $temporaryPath)) {
        Remove-Item -LiteralPath $temporaryPath -Force
    }
}
