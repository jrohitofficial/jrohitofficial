<#
.SYNOPSIS
    Fill in the placeholders and generate every local asset for the profile README.

.EXAMPLE
    .\setup.ps1 -Username tanishka -Name "Tanishka" -Image .\me.jpg

.EXAMPLE
    # regenerate art only, with different dot settings
    .\setup.ps1 -Image .\me.jpg -Cols 110 -Circle -Animate
#>
[CmdletBinding()]
param(
    [string]$Username,
    [string]$Name,
    [string]$Image,
    [ValidateSet('dots', 'binary', 'ascii', 'braille')]
    [string]$Mode = 'dots',
    [int]$Cols = 88,
    [switch]$Circle,
    [switch]$Color,
    [switch]$Animate,
    [switch]$Invert,
    [switch]$Square,
    [string]$Focus = '0.5,0.5'
)

$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

function Set-Placeholder($token, $value) {
    if (-not $value) { return }
    $targets = @(
        (Join-Path $root 'README.md')
        (Get-ChildItem (Join-Path $root '.github\workflows') -Filter *.yml).FullName
    ) | Where-Object { $_ -and (Test-Path $_) }

    # Read/write UTF-8 explicitly. Windows PowerShell 5.1 reads as ANSI by
    # default, which mangles every non-ASCII character in the file, and its
    # -Encoding utf8 writes a BOM. Go through .NET to get plain UTF-8 both ways.
    $utf8 = New-Object System.Text.UTF8Encoding $false

    foreach ($f in $targets) {
        $text = [System.IO.File]::ReadAllText($f, $utf8)
        if ($text.Contains($token)) {
            [System.IO.File]::WriteAllText($f, $text.Replace($token, $value), $utf8)
            Write-Host "  $token -> $value  in $(Split-Path $f -Leaf)"
        }
    }
}

if ($Username) {
    Write-Host "`n[1/3] filling placeholders" -ForegroundColor Cyan
    Set-Placeholder 'YOUR_USERNAME' $Username
}
if ($Name) {
    Set-Placeholder 'YOUR+NAME' ($Name -replace ' ', '+')   # typing-SVG query string
    Set-Placeholder 'YOUR NAME' $Name
}

Write-Host "`n[2/3] drawing the skill radar" -ForegroundColor Cyan
python (Join-Path $root 'scripts\radar.py') --data (Join-Path $root 'assets\skills.json') -o (Join-Path $root 'assets\radar')

if ($Username) {
    Write-Host "      drawing the language radar from the GitHub API" -ForegroundColor Cyan
    try {
        python (Join-Path $root 'scripts\radar.py') --github $Username -o (Join-Path $root 'assets\radar-langs') --values
    } catch {
        Write-Warning "language radar skipped: $_"
    }
}

if ($Image) {
    Write-Host "`n[3/3] dot-matrixing $Image" -ForegroundColor Cyan
    # NB: not $args — that is a reserved PowerShell automatic variable
    $dotArgs = @(
        (Join-Path $root 'scripts\dotify.py'), $Image,
        '-o', (Join-Path $root 'assets\portrait'),
        '--mode', $Mode, '--cols', $Cols
    )
    if ($Square)  { $dotArgs += @('--square', '--focus', $Focus) }
    if ($Circle)  { $dotArgs += '--circle' }
    if ($Color)   { $dotArgs += '--color' }
    if ($Animate) { $dotArgs += '--animate' }
    if ($Invert)  { $dotArgs += '--invert' }
    python @dotArgs
} else {
    Write-Host "`n[3/3] no -Image given, skipping the portrait" -ForegroundColor DarkGray
}

Write-Host "`ndone. open preview.html to check it, then read SETUP.md for the GitHub side.`n" -ForegroundColor Green
