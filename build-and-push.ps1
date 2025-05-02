#
# PowerShell script to build and push a multi-platform Docker image
# for the Car Insurance Claims AI Agent
#

param (
    [string]$Registry = "",
    [string]$Name = "car-insurance-claims-ai-agent",
    [string]$Tag = "latest",
    [string]$Platforms = "linux/amd64,linux/arm64",
    [switch]$BuildOnly = $false,
    [switch]$Help = $false
)

# Show help if requested
if ($Help) {
    Write-Host "Usage: .\build-and-push.ps1 [OPTIONS]"
    Write-Host ""
    Write-Host "Build and push a multi-platform Docker image for the Car Insurance Claims AI Agent"
    Write-Host ""
    Write-Host "Options:"
    Write-Host "  -Registry     Container registry URL (e.g., myacr.azurecr.io)"
    Write-Host "  -Name         Image name (default: car-insurance-claims-ai-agent)"
    Write-Host "  -Tag          Image tag (default: latest)"
    Write-Host "  -Platforms    Platforms to build for (default: linux/amd64,linux/arm64)"
    Write-Host "  -BuildOnly    Build image only, don't push"
    Write-Host "  -Help         Show this help message"
    Write-Host ""
    Write-Host "Example:"
    Write-Host "  .\build-and-push.ps1 -Registry myacr.azurecr.io -Tag v1.0.0"
    exit 0
}

# Check if Docker is installed
try {
    $null = docker --version
}
catch {
    Write-Host "Error: Docker is not installed or not in your PATH" -ForegroundColor Red
    exit 1
}

# Enable Docker BuildKit for multi-platform builds
$env:DOCKER_BUILDKIT = 1

# Set up image name with registry if provided
if ($Registry) {
    $FullImageName = "$Registry/$Name`:$Tag"
}
else {
    $FullImageName = "$Name`:$Tag"
}

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Building multi-platform Docker image" -ForegroundColor Cyan
Write-Host "Image: $FullImageName" -ForegroundColor Cyan
Write-Host "Platforms: $Platforms" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Check if Docker BuildX is available
try {
    $null = docker buildx version
}
catch {
    Write-Host "Creating Docker BuildX instance..." -ForegroundColor Yellow
    docker buildx create --name multiarch --use
}

# Build and push image
if ($BuildOnly) {
    Write-Host "Building image without pushing..." -ForegroundColor Yellow
    docker buildx build --platform $Platforms `
        -t $FullImageName `
        --load `
        .
}
else {
    # Check if registry is provided for push
    if (-not $Registry) {
        Write-Host "Error: Registry must be specified when pushing an image" -ForegroundColor Red
        Write-Host "Use -Registry option or -BuildOnly if you just want to build" -ForegroundColor Red
        exit 1
    }
    
    Write-Host "Building and pushing image..." -ForegroundColor Yellow
    docker buildx build --platform $Platforms `
        -t $FullImageName `
        --push `
        .
}

Write-Host "========================================" -ForegroundColor Green
Write-Host "Process completed successfully!" -ForegroundColor Green
if ($BuildOnly) {
    Write-Host "Image built: $FullImageName" -ForegroundColor Green
}
else {
    Write-Host "Image built and pushed: $FullImageName" -ForegroundColor Green
}
Write-Host "========================================" -ForegroundColor Green 