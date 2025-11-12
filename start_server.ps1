# Script para iniciar o servidor de forma mais robusta
cd "C:\PROJETOS_PYTHON\Game Roleplay"
.\venv\Scripts\Activate.ps1

Write-Host "Iniciando servidor..." -ForegroundColor Green
Write-Host "Pressione Ctrl+C para parar o servidor" -ForegroundColor Yellow
Write-Host ""

# Configurar logging para ver todos os erros
$env:PYTHONUNBUFFERED = "1"

python -m app.main




