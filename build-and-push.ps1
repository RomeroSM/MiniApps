# Скрипт для сборки и публикации Docker образа в приватный реестр (PowerShell)
# Использование: .\build-and-push.ps1 [registry-url] [image-name] [tag]

param(
    [string]$Registry = "your-registry.com",
    [string]$ImageName = "telegram_miniapp",
    [string]$Tag = "latest"
)

$ErrorActionPreference = "Stop"

# Полное имя образа с реестром
$FullImageName = "${Registry}/${ImageName}:${Tag}"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Сборка и публикация Docker образа" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Реестр: $Registry"
Write-Host "Имя образа: $ImageName"
Write-Host "Тег: $Tag"
Write-Host "Полное имя: $FullImageName"
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Шаг 1: Сборка образа
Write-Host "Шаг 1: Сборка Docker образа..." -ForegroundColor Yellow
docker build -t "${ImageName}:${Tag}" -t "$FullImageName" .
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Ошибка сборки образа" -ForegroundColor Red
    exit 1
}
Write-Host "✓ Образ собран успешно" -ForegroundColor Green
Write-Host ""

# Шаг 2: Вход в реестр (опционально)
Write-Host "Шаг 2: Вход в Docker Registry..." -ForegroundColor Yellow
Write-Host "Если требуется аутентификация, выполните: docker login $Registry"
$LoginRequired = Read-Host "Выполнить вход сейчас? (y/n)"

if ($LoginRequired -eq "y" -or $LoginRequired -eq "Y") {
    docker login $Registry
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Успешный вход в реестр" -ForegroundColor Green
    } else {
        Write-Host "✗ Ошибка входа в реестр" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "→ Вход пропущен" -ForegroundColor Gray
}
Write-Host ""

# Шаг 3: Публикация образа
Write-Host "Шаг 3: Публикация образа в реестр..." -ForegroundColor Yellow
docker push "$FullImageName"
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Образ успешно опубликован: $FullImageName" -ForegroundColor Green
} else {
    Write-Host "✗ Ошибка публикации образа" -ForegroundColor Red
    exit 1
}
Write-Host ""

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Готово! Образ доступен по адресу:" -ForegroundColor Green
Write-Host "$FullImageName" -ForegroundColor White
Write-Host "=========================================" -ForegroundColor Cyan

