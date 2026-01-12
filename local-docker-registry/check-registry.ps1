# Скрипт для проверки статуса локального Docker registry

$RegistryUrl = "http://localhost:5000"

Write-Host "Проверка локального Docker registry..." -ForegroundColor Cyan
Write-Host "URL: $RegistryUrl" -ForegroundColor Gray
Write-Host ""

# Проверка доступности registry
Write-Host "1. Проверка доступности registry..." -ForegroundColor Yellow
try {
    $response = Invoke-WebRequest -Uri "$RegistryUrl/v2/" -Method Get -TimeoutSec 5 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "   ✓ Registry доступен" -ForegroundColor Green
    } else {
        Write-Host "   ✗ Registry вернул код: $($response.StatusCode)" -ForegroundColor Red
    }
} catch {
    Write-Host "   ✗ Registry недоступен: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "Попробуйте запустить registry:" -ForegroundColor Yellow
    Write-Host "   docker-compose up -d" -ForegroundColor Cyan
    exit 1
}

# Проверка статуса контейнера
Write-Host ""
Write-Host "2. Проверка статуса контейнера..." -ForegroundColor Yellow
$container = docker ps -a --filter "name=local-docker-registry" --format "{{.Names}} {{.Status}}"
if ($container) {
    Write-Host "   $container" -ForegroundColor Green
} else {
    Write-Host "   ✗ Контейнер не найден" -ForegroundColor Red
}

# Список репозиториев
Write-Host ""
Write-Host "3. Список репозиториев в registry..." -ForegroundColor Yellow
try {
    $catalog = Invoke-RestMethod -Uri "$RegistryUrl/v2/_catalog" -Method Get -TimeoutSec 5
    if ($catalog.repositories.Count -gt 0) {
        Write-Host "   Найдено репозиториев: $($catalog.repositories.Count)" -ForegroundColor Green
        foreach ($repo in $catalog.repositories) {
            Write-Host "   - $repo" -ForegroundColor Gray
        }
    } else {
        Write-Host "   Registry пуст (нет репозиториев)" -ForegroundColor Gray
    }
} catch {
    Write-Host "   ✗ Не удалось получить список репозиториев: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Проверка завершена!" -ForegroundColor Green




