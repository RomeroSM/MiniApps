# Скрипт для отправки образа в локальный Docker registry
# Использование: .\push-to-local.ps1 -ImageName "telegram-miniapp" -Tag "latest"

param(
    [Parameter(Mandatory=$true)]
    [string]$ImageName,
    
    [Parameter(Mandatory=$false)]
    [string]$Tag = "latest",
    
    [Parameter(Mandatory=$false)]
    [string]$Registry = "localhost:5000"
)

$FullImageName = "$ImageName`:$Tag"
$RegistryImageName = "$Registry/$FullImageName"

Write-Host "Тегирование образа: $FullImageName -> $RegistryImageName" -ForegroundColor Cyan

# Проверка существования образа
$imageExists = docker images $FullImageName -q
if (-not $imageExists) {
    Write-Host "Ошибка: Образ $FullImageName не найден!" -ForegroundColor Red
    Write-Host "Доступные образы:" -ForegroundColor Yellow
    docker images
    exit 1
}

# Тегирование
Write-Host "Выполняется тегирование..." -ForegroundColor Yellow
docker tag $FullImageName $RegistryImageName

if ($LASTEXITCODE -ne 0) {
    Write-Host "Ошибка при тегировании образа!" -ForegroundColor Red
    exit 1
}

# Отправка в registry
Write-Host "Отправка образа в локальный registry: $RegistryImageName" -ForegroundColor Yellow
docker push $RegistryImageName

if ($LASTEXITCODE -ne 0) {
    Write-Host "Ошибка при отправке образа!" -ForegroundColor Red
    Write-Host "Убедитесь, что:" -ForegroundColor Yellow
    Write-Host "  1. Registry запущен (docker-compose up -d)" -ForegroundColor Yellow
    Write-Host "  2. Настроен insecure-registries в Docker Desktop" -ForegroundColor Yellow
    exit 1
}

Write-Host "Образ успешно отправлен в локальный registry!" -ForegroundColor Green
Write-Host "Используйте: docker pull $RegistryImageName" -ForegroundColor Cyan




