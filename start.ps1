param(
    [switch]$Install = $false
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
cd $ScriptDir

Write-Host "Starting PDF Q&A..." -ForegroundColor Cyan

# Kill stale processes on ports 5173 (Frontend) and 8000 (Backend)
function Kill-Port {
    param([int]$Port)
    $Connections = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if ($Connections) {
        Write-Host "Port $Port is in use. Killing stale processes..." -ForegroundColor Yellow
        foreach ($Conn in $Connections) {
            $Process = Get-Process -Id $Conn.OwningProcess -ErrorAction SilentlyContinue
            if ($Process) {
                Write-Host "Killing Process ID: $($Process.Id) ($($Process.ProcessName))" -ForegroundColor Yellow
                Stop-Process -Id $Process.Id -Force
            }
        }
        Start-Sleep -Seconds 2
    }
}

Kill-Port 8001
Kill-Port 5174

if ($Install) {
    Write-Host "Installing Backend Dependencies..." -ForegroundColor Cyan
    cd backend
    pip install -r requirements.txt
    cd ..

    Write-Host "Installing Frontend Dependencies..." -ForegroundColor Cyan
    cd frontend
    npm install
    cd ..
}

# Start Backend
Write-Host "Starting Backend..." -ForegroundColor Cyan
cd backend
$BackendProc = Start-Process python -ArgumentList "main.py" -NoNewWindow -PassThru
cd ..

Start-Sleep -Seconds 2

# Start Frontend
Write-Host "Starting Frontend..." -ForegroundColor Cyan
cd frontend
$FrontendProc = Start-Process npm.cmd -ArgumentList "run dev" -NoNewWindow -PassThru
cd ..

Write-Host "PDF Q&A is running!" -ForegroundColor Green
Write-Host "Frontend: http://localhost:5174"
Write-Host "Backend: http://localhost:8001"
Write-Host "Press Ctrl+C to exit."

try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host "`nStopping processes..." -ForegroundColor Yellow
    if ($BackendProc) { Stop-Process -Id $BackendProc.Id -Force -ErrorAction SilentlyContinue }
    if ($FrontendProc) { Stop-Process -Id $FrontendProc.Id -Force -ErrorAction SilentlyContinue }
}
