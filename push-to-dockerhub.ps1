# Скрипт для публикации образа в Docker Hub
# Использование: .\push-to-dockerhub.ps1 -DockerHubUsername "your-username"

param(
    [Parameter(Mandatory=$true)]
    [string]$DockerHubUsername,
    
    [string]$ImageName = "telegram_miniapp",
    [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"

$DockerHubImage = "${DockerHubUsername}/${ImageName}:${Tag}"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Публикация образа в Docker Hub" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Пользователь Docker Hub: $DockerHubUsername" -ForegroundColor White
Write-Host "Имя образа: $ImageName" -ForegroundColor White
Write-Host "Тег: $Tag" -ForegroundColor White
Write-Host "Полное имя: $DockerHubImage" -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Шаг 1: Проверка существования локального образа
Write-Host "Шаг 1: Проверка локального образа..." -ForegroundColor Yellow
$localImage = docker images "${ImageName}:${Tag}" -q
if (-not $localImage) {
    Write-Host "✗ Локальный образ ${ImageName}:${Tag} не найден" -ForegroundColor Red
    Write-Host "Сначала соберите образ: docker build -t ${ImageName}:${Tag} ." -ForegroundColor Yellow
    exit 1
}
Write-Host "✓ Локальный образ найден" -ForegroundColor Green
Write-Host ""

# Шаг 2: Тегирование образа для Docker Hub
Write-Host "Шаг 2: Тегирование образа для Docker Hub..." -ForegroundColor Yellow
docker tag "${ImageName}:${Tag}" $DockerHubImage
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Ошибка тегирования образа" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Образ помечен: $DockerHubImage" -ForegroundColor Green
Write-Host ""

# Шаг 3: Вход в Docker Hub
Write-Host "Шаг 3: Вход в Docker Hub..." -ForegroundColor Yellow
Write-Host "Введите ваши учетные данные Docker Hub:" -ForegroundColor White
docker login
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Ошибка входа в Docker Hub" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Успешный вход в Docker Hub" -ForegroundColor Green
Write-Host ""

# Шаг 4: Публикация образа
Write-Host "Шаг 4: Публикация образа в Docker Hub..." -ForegroundColor Yellow
Write-Host "Это может занять некоторое время..." -ForegroundColor Gray
docker push $DockerHubImage
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host "✓ Образ успешно опубликован!" -ForegroundColor Green
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Образ доступен по адресу:" -ForegroundColor Cyan
    Write-Host "https://hub.docker.com/r/${DockerHubUsername}/${ImageName}" -ForegroundColor White
    Write-Host ""
    Write-Host "Команда для скачивания:" -ForegroundColor Cyan
    Write-Host "docker pull $DockerHubImage" -ForegroundColor Yellow
} else {
    Write-Host "✗ Ошибка публикации образа" -ForegroundColor Red
    exit 1
}

