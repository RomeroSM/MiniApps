# Simple script to push Docker image to Docker Hub
# Requires: Docker Hub username and credentials

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "Push Docker image to Docker Hub" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Request Docker Hub username
$DockerHubUsername = Read-Host "Enter your Docker Hub username"

if ([string]::IsNullOrWhiteSpace($DockerHubUsername)) {
    Write-Host "ERROR: Username cannot be empty" -ForegroundColor Red
    exit 1
}

$ImageName = "telegram_miniapp"
$Tag = "latest"
$DockerHubImage = "${DockerHubUsername}/${ImageName}:${Tag}"

Write-Host ""
Write-Host "Push parameters:" -ForegroundColor Yellow
Write-Host "  Username: $DockerHubUsername" -ForegroundColor White
Write-Host "  Image: ${ImageName}:${Tag}" -ForegroundColor White
Write-Host "  Full name: $DockerHubImage" -ForegroundColor White
Write-Host ""

# Check local image
Write-Host "Checking local image..." -ForegroundColor Yellow
$localImage = docker images "${ImageName}:${Tag}" -q
if (-not $localImage) {
    Write-Host "ERROR: Local image not found. Build it first:" -ForegroundColor Red
    Write-Host "  docker build -t ${ImageName}:${Tag} ." -ForegroundColor Yellow
    exit 1
}
Write-Host "SUCCESS: Local image found" -ForegroundColor Green
Write-Host ""

# Tag image
Write-Host "Tagging image for Docker Hub..." -ForegroundColor Yellow
docker tag "${ImageName}:${Tag}" $DockerHubImage
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to tag image" -ForegroundColor Red
    exit 1
}
Write-Host "SUCCESS: Image tagged" -ForegroundColor Green
Write-Host ""

# Login to Docker Hub
Write-Host "Logging in to Docker Hub..." -ForegroundColor Yellow
Write-Host "Enter your credentials (username and password/token):" -ForegroundColor White
docker login
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Failed to login to Docker Hub" -ForegroundColor Red
    exit 1
}
Write-Host "SUCCESS: Logged in" -ForegroundColor Green
Write-Host ""

# Push image
Write-Host "Pushing image to Docker Hub..." -ForegroundColor Yellow
Write-Host "This may take a few minutes..." -ForegroundColor Gray
docker push $DockerHubImage
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host "SUCCESS! Image pushed to Docker Hub" -ForegroundColor Green
    Write-Host "=========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Image is available at:" -ForegroundColor Cyan
    $repoUrl = "https://hub.docker.com/r/${DockerHubUsername}/${ImageName}"
    Write-Host "  $repoUrl" -ForegroundColor White
    Write-Host ""
    $pullCmd = "docker pull $DockerHubImage"
    Write-Host "To pull the image use:" -ForegroundColor Cyan
    Write-Host "  $pullCmd" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "ERROR: Failed to push image" -ForegroundColor Red
    exit 1
}
