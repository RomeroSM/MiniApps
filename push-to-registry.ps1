# Быстрая команда для публикации образа в реестр
# Использование: .\push-to-registry.ps1 -Registry "your-registry.com"

param(
    [Parameter(Mandatory=$true)]
    [string]$Registry,
    
    [string]$ImageName = "telegram_miniapp",
    [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"

$FullImageName = "${Registry}/${ImageName}:${Tag}"

Write-Host "Публикация образа в реестр: $Registry" -ForegroundColor Cyan
Write-Host "Полное имя образа: $FullImageName" -ForegroundColor Yellow
Write-Host ""

# Тегирование
Write-Host "Тегирование образа..." -ForegroundColor Yellow
docker tag "${ImageName}:${Tag}" $FullImageName
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Ошибка тегирования" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Образ помечен" -ForegroundColor Green
Write-Host ""

# Вход в реестр
Write-Host "Вход в реестр..." -ForegroundColor Yellow
docker login $Registry
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Ошибка входа в реестр" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Успешный вход" -ForegroundColor Green
Write-Host ""

# Публикация
Write-Host "Публикация образа..." -ForegroundColor Yellow
docker push $FullImageName
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Образ успешно опубликован: $FullImageName" -ForegroundColor Green
} else {
    Write-Host "✗ Ошибка публикации" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Готово! Образ доступен по адресу: $FullImageName" -ForegroundColor Cyan

