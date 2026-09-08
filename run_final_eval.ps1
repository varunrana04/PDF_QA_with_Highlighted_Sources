Write-Host "Checking if Ollama is installed..." -ForegroundColor Cyan

$ollamaPath = "C:\Users\Varun\AppData\Local\Programs\Ollama\ollama.exe"

if (-not (Test-Path $ollamaPath) -and -not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "Ollama not found. Downloading Ollama installer..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri "https://ollama.com/download/OllamaSetup.exe" -OutFile "OllamaSetup.exe"
    
    Write-Host "Installing Ollama silently (this may take a minute)..." -ForegroundColor Yellow
    Start-Process -FilePath ".\OllamaSetup.exe" -ArgumentList "/SILENT" -Wait
    
    Write-Host "Ollama installed successfully!" -ForegroundColor Green
} else {
    Write-Host "Ollama is already installed." -ForegroundColor Green
}

# Add Ollama to path for this session if it's not there
if (Test-Path $ollamaPath) {
    $env:Path += ";C:\Users\Varun\AppData\Local\Programs\Ollama"
}

Write-Host "Starting Ollama server in the background..." -ForegroundColor Cyan
Start-Process -NoNewWindow -FilePath "ollama" -ArgumentList "serve"

Write-Host "Pulling LLaMA 3.1 model (this may take a few minutes if not already downloaded)..." -ForegroundColor Yellow
ollama pull llama3.1

Write-Host "Ollama is ready! Running the final evaluation on Attention Is All You Need..." -ForegroundColor Green
python backend\run_eval.py --real-pdf "attention_is_all_you_need.pdf"
