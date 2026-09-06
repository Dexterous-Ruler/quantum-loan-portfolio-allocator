<#
    start_demo.ps1 - one command to bring up everything for the presentation.

    Starts the 3D dashboard (http://localhost:4173) and the Streamlit demo
    (http://localhost:8899), builds the web app first if it has never been built,
    waits until both answer, and opens them in the browser.

    Safe to run twice: anything already listening is left alone.

    Usage:
        powershell -ExecutionPolicy Bypass -File start_demo.ps1
        powershell -ExecutionPolicy Bypass -File start_demo.ps1 -NoBrowser
        powershell -ExecutionPolicy Bypass -File start_demo.ps1 -Share     # + public Cloudflare link
        powershell -ExecutionPolicy Bypass -File start_demo.ps1 -Stop
#>
[CmdletBinding()]
param(
    [switch]$NoBrowser,   # start the servers but do not open browser tabs
    [switch]$Share,       # also open a public Cloudflare quick tunnel to the dashboard
    [switch]$Stop         # shut both servers down instead of starting them
)

$ErrorActionPreference = 'Stop'
$root    = $PSScriptRoot
$WEB_PORT = 4173
$APP_PORT = 8899
$logDir  = Join-Path $root 'artifacts'

function Write-Step($msg) { Write-Host "  $msg" -ForegroundColor DarkGray }
function Write-Good($msg) { Write-Host "  OK  $msg" -ForegroundColor Green }
function Write-Warn($msg) { Write-Host "  !!  $msg" -ForegroundColor Yellow }

function Test-Port([int]$port) {
    try { return [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction Stop) }
    catch { return $false }
}

function Wait-Port([int]$port, [int]$timeoutSec = 90) {
    $deadline = (Get-Date).AddSeconds($timeoutSec)
    while ((Get-Date) -lt $deadline) {
        if (Test-Port $port) { return $true }
        Start-Sleep -Milliseconds 700
    }
    return $false
}

function Stop-Port([int]$port, [string]$label) {
    if (-not (Test-Port $port)) { Write-Step "$label was not running"; return }
    $pids = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $pids) {
        try { Stop-Process -Id $procId -Force -ErrorAction Stop; Write-Good "stopped $label (pid $procId)" }
        catch { Write-Warn "could not stop pid $procId : $_" }
    }
}

Write-Host ''
Write-Host '  QUANTUM LOAN BOOK - demo launcher' -ForegroundColor White
Write-Host '  Team ASTITWA' -ForegroundColor DarkGray
Write-Host ''

# ---------------------------------------------------------------- stop mode
if ($Stop) {
    Stop-Port $WEB_PORT '3D dashboard'
    Stop-Port $APP_PORT 'Streamlit demo'
    Get-Process cloudflared -ErrorAction SilentlyContinue | ForEach-Object {
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        Write-Good "stopped Cloudflare tunnel (pid $($_.Id))"
    }
    Write-Host ''
    exit 0
}

if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir | Out-Null }

# ---------------------------------------------------------------- preflight
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) {
    Write-Warn "no virtualenv at .venv - run:  py -3.14 -m venv .venv; .venv\Scripts\python.exe -m pip install -r requirements.txt"
    exit 1
}

# ---------------------------------------------------------------- 3D dashboard
Write-Host '  [1/2] 3D dashboard' -ForegroundColor White
if (Test-Port $WEB_PORT) {
    Write-Good "already running on port $WEB_PORT"
} else {
    $webDir = Join-Path $root 'web'
    if (-not (Test-Path (Join-Path $webDir 'node_modules'))) {
        Write-Step 'installing npm packages (first run, ~1 min)'
        Push-Location $webDir; & npm install --silent; Pop-Location
    }
    if (-not (Test-Path (Join-Path $webDir 'dist\index.html'))) {
        Write-Step 'building the web app (~15 s)'
        Push-Location $webDir; & npm run build; Pop-Location
    }
    Write-Step "starting vite preview on port $WEB_PORT"
    Start-Process -FilePath 'cmd.exe' `
        -ArgumentList '/c', "npm run preview -- --port $WEB_PORT > `"$logDir\web_preview.log`" 2>&1" `
        -WorkingDirectory $webDir -WindowStyle Hidden
    if (Wait-Port $WEB_PORT 90) { Write-Good "up on port $WEB_PORT" }
    else { Write-Warn "did not come up - check $logDir\web_preview.log" }
}

# ---------------------------------------------------------------- Streamlit
Write-Host ''
Write-Host '  [2/2] Streamlit demo' -ForegroundColor White
if (Test-Port $APP_PORT) {
    Write-Good "already running on port $APP_PORT"
} else {
    Write-Step "starting streamlit on port $APP_PORT (first solve is pre-warmed, ~20 s)"
    Start-Process -FilePath 'cmd.exe' `
        -ArgumentList '/c', "`"$python`" -m streamlit run app.py --server.port $APP_PORT --server.headless true > `"$logDir\app_log.txt`" 2>&1" `
        -WorkingDirectory $root -WindowStyle Hidden
    if (Wait-Port $APP_PORT 120) { Write-Good "up on port $APP_PORT" }
    else { Write-Warn "did not come up - check $logDir\app_log.txt" }
}

# ---------------------------------------------------------------- public link
$publicUrl = $null
if ($Share) {
    Write-Host ''
    Write-Host '  [+] public Cloudflare link' -ForegroundColor White
    $cf = @(
        'C:\Program Files (x86)\cloudflared\cloudflared.exe',
        'C:\Program Files\cloudflared\cloudflared.exe',
        "$env:LOCALAPPDATA\cloudflared\cloudflared.exe"
    ) | Where-Object { Test-Path $_ } | Select-Object -First 1

    if (-not $cf) {
        Write-Warn 'cloudflared not found - install it, or deploy to Vercel for a permanent link'
    } else {
        Get-Process cloudflared -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        $tunLog = Join-Path $logDir 'tunnel_log.txt'
        Remove-Item $tunLog -ErrorAction SilentlyContinue
        # --protocol http2: this network blocks the QUIC port (7844) cloudflared prefers.
        Start-Process -FilePath 'cmd.exe' `
            -ArgumentList '/c', "`"$cf`" tunnel --url http://localhost:$WEB_PORT --protocol http2 --no-autoupdate > `"$tunLog`" 2>&1" `
            -WorkingDirectory $root -WindowStyle Hidden
        Write-Step 'waiting for Cloudflare to hand out a hostname'
        $deadline = (Get-Date).AddSeconds(60)
        while ((Get-Date) -lt $deadline -and -not $publicUrl) {
            Start-Sleep -Milliseconds 1200
            if (Test-Path $tunLog) {
                $m = Select-String -Path $tunLog -Pattern 'https://[a-z0-9-]+\.trycloudflare\.com' -ErrorAction SilentlyContinue |
                     Select-Object -First 1
                if ($m) { $publicUrl = $m.Matches[0].Value }
            }
        }
        if ($publicUrl) { Write-Good $publicUrl }
        else { Write-Warn "no hostname yet - check $tunLog" }
    }
}

# ---------------------------------------------------------------- open + summary
$webUrl = "http://localhost:$WEB_PORT/"
$appUrl = "http://localhost:$APP_PORT/"

if (-not $NoBrowser) {
    Write-Host ''
    Write-Step 'opening browser tabs'
    if (Test-Port $WEB_PORT) { Start-Process $webUrl; Start-Sleep -Milliseconds 900 }
    if (Test-Port $APP_PORT) { Start-Process $appUrl }
}

Write-Host ''
Write-Host '  ---------------------------------------------------------' -ForegroundColor DarkGray
Write-Host "  3D dashboard   $webUrl   <- present from this one" -ForegroundColor White
Write-Host "  Streamlit      $appUrl" -ForegroundColor White
if ($publicUrl) {
    Write-Host "  Public link    $publicUrl" -ForegroundColor Cyan
    Write-Host "                 (dies when this laptop sleeps or the script is stopped)" -ForegroundColor DarkGray
}
Write-Host "  Report         REPORT.pdf" -ForegroundColor DarkGray
Write-Host "  Run of show    PRESENT.md" -ForegroundColor DarkGray
Write-Host '  ---------------------------------------------------------' -ForegroundColor DarkGray
Write-Host '  Shut down with:  powershell -ExecutionPolicy Bypass -File start_demo.ps1 -Stop' -ForegroundColor DarkGray
Write-Host ''
