[CmdletBinding()]
param([string]$Python = 'python')

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

try {
    $projectPath = [System.IO.Path]::GetFullPath($PSScriptRoot)
    $sourcePath = Join-Path $projectPath 'tools\log_window.py'
    $distPath = Join-Path $projectPath 'dist'
    $workPath = Join-Path $projectPath 'build\log-window'
    $specPath = Join-Path $projectPath 'build'
    # PyInstaller replaces its generated output on rebuild. Keep it in this project.
    foreach ($path in @($distPath, $workPath, $specPath)) {
        if (-not [System.IO.Path]::GetFullPath($path).StartsWith($projectPath + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Build path is outside the project: $path"
        }
    }
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) { throw "Missing window source: $sourcePath" }
    & $Python -c "import sys, struct, tkinter, PyInstaller; assert sys.platform == 'win32' and struct.calcsize('P') == 8, 'Use 64-bit Windows Python'; assert int(PyInstaller.__version__.split('.')[0]) >= 6, 'PyInstaller 6 or newer is required'"
    if ($LASTEXITCODE -ne 0) {
        throw 'Install 64-bit Python with Tcl/Tk, then run: python -m pip install -r requirements-build.txt'
    }
    & $Python -m PyInstaller --noconfirm --clean --onedir --windowed --noupx `
        --debug noarchive --contents-directory dependencies --name StellarBladeExportLog `
        --distpath $distPath --workpath $workPath --specpath $specPath $sourcePath
    if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed with exit code $LASTEXITCODE." }
    $bundlePath = Join-Path $distPath 'StellarBladeExportLog'
    if (-not (Test-Path -LiteralPath (Join-Path $bundlePath 'StellarBladeExportLog.exe') -PathType Leaf) -or
        -not (Test-Path -LiteralPath (Join-Path $bundlePath 'dependencies') -PathType Container)) {
        throw 'Build did not produce the EXE and dependencies folder.'
    }
    Write-Host "Built $bundlePath"
}
catch {
    Write-Error -Message "Log window build failed: $($_.Exception.Message)" -ErrorAction Continue
    exit 1
}
