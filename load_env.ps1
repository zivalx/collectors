# PowerShell script to load environment variables from .env file
# Usage: .\load_env.ps1

Write-Host "Loading environment variables from .env file..." -ForegroundColor Green

$envFile = Join-Path $PSScriptRoot ".env"

if (-not (Test-Path $envFile)) {
    Write-Host "ERROR: .env file not found at: $envFile" -ForegroundColor Red
    Write-Host "Please create a .env file from .env.example" -ForegroundColor Yellow
    exit 1
}

$lineCount = 0
$varCount = 0

Get-Content $envFile | ForEach-Object {
    $lineCount++
    if ($_ -match '^\s*([^#][^=]*?)\s*=\s*(.*)$') {
        $key = $matches[1]
        $value = $matches[2]
        [Environment]::SetEnvironmentVariable($key, $value, 'Process')
        $varCount++
        Write-Host "  OK Loaded: $key" -ForegroundColor Cyan
    }
}

Write-Host "`nSuccessfully loaded $varCount environment variables from $lineCount lines" -ForegroundColor Green
Write-Host "`nYou can now run your Python scripts in this session." -ForegroundColor Yellow
Write-Host "Example: python examples\my_crypto_collector.py" -ForegroundColor Yellow
