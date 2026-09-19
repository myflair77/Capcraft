$ErrorActionPreference = 'Stop'
$projectRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$archiveRoot = Join-Path $projectRoot 'archive\legacy'
$keep = @('main.py', 'capture_engine.py', 'storage.py', 'ocr_engine.py', 'ocr_bridge.py', 'requirements.txt', 'requirements-build.txt', 'requirements-ocr.txt', 'index.html', 'guide.html', 'popout-quality.js', 'presentation-refresh.js', 'ocr-ui.js')
$candidates = Get-ChildItem -LiteralPath $projectRoot -File | Where-Object {
    $_.Extension -in @('.py', '.txt', '.js', '.html') -and $_.Name -notin ($keep + @('ocr_mixed.py', 'ocr_text.py', 'ocr_languages.py', 'ocr_window.py', 'natural-pens.js', 'line-anchors.js', 'shape-pens.js', 'stroke-effects.js'))
}
foreach ($item in $candidates) {
    $source = [IO.Path]::GetFullPath($item.FullName)
    $destination = [IO.Path]::GetFullPath((Join-Path $archiveRoot $item.Name))
    if ([IO.Path]::GetDirectoryName($source) -ne $projectRoot -or
        -not $destination.StartsWith($archiveRoot + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw "Unexpected archive target: $source"
    }
    if (Test-Path -LiteralPath $destination) { throw "Already exists: $destination" }
}
New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null
foreach ($item in $candidates) {
    Move-Item -LiteralPath $item.FullName -Destination (Join-Path $archiveRoot $item.Name)
}
Write-Output "Archived $($candidates.Count) historical helper files without deleting their contents."
