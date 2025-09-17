# GitHub Actions Automated Docker Builds

This document explains the automated Docker container builds setup for the New Metal Albums project with multi-architecture support.

## Overview

The project uses GitHub Actions to automatically build and publish Docker images to GitHub Container Registry (GHCR) with support for both AMD64 and ARM64 architectures.

## Workflow Features

### 🔄 **Automated Triggers**
- **Push to main/master/develop**: Builds and pushes images
- **Tagged releases** (v*): Creates versioned releases
- **Pull requests**: Builds images for testing (no push)
- **Manual dispatch**: Trigger builds manually

### 🏗️ **Multi-Architecture Support**
- **AMD64**: Intel/AMD processors (standard servers, desktops)
- **ARM64**: Apple Silicon, Raspberry Pi, AWS Graviton

### 🐳 **Container Registry**
- **Registry**: GitHub Container Registry (ghcr.io)
- **Images**: 
  - `ghcr.io/[username]/newmetalbums-backend:latest`
  - `ghcr.io/[username]/newmetalbums-frontend:latest`

### 🔒 **Security Features**
- Vulnerability scanning with Trivy
- Results uploaded to GitHub Security tab
- Automatic security advisories

## Setup Instructions

### 1. Enable GitHub Container Registry

1. Go to your GitHub repository
2. Navigate to **Settings** → **Actions** → **General**
3. Under "Workflow permissions", select **Read and write permissions**
4. Check **Allow GitHub Actions to create and approve pull requests**

### 2. Repository Settings

Ensure your repository has the following:
- **Public repository** OR **GitHub Pro/Team** for private registries
- **Actions enabled** in repository settings

### 3. First Build

Push to main branch or create a tag to trigger the first build:

```bash
git add .
git commit -m "Add automated Docker builds"
git push origin main

# Or create a release
git tag v1.0.0
git push origin v1.0.0
```

## Usage

### Production Deployment

Use the pre-built images from GitHub Container Registry:

```bash
# Download the production compose file
curl -O https://raw.githubusercontent.com/[username]/newmetalbums/main/docker-compose.production.yml

# Start the application
docker-compose -f docker-compose.production.yml up -d
```

### Custom Images

To use your own registry, update the workflow file:

```yaml
env:
  REGISTRY: your-registry.com
  IMAGE_NAME_BACKEND: your-org/newmetalbums-backend
  IMAGE_NAME_FRONTEND: your-org/newmetalbums-frontend
```

## Image Tags

The workflow creates multiple tags for flexibility:

- **`latest`**: Latest build from main branch
- **`main`**: Latest build from main branch
- **`v1.0.0`**: Specific version tags
- **`v1.0`**: Major.minor version
- **`pr-123`**: Pull request builds

## Architecture Detection

Images are automatically built for multiple architectures:

```bash
# Docker will automatically pull the correct architecture
docker run ghcr.io/[username]/newmetalbums-backend:latest

# Check available architectures
docker manifest inspect ghcr.io/[username]/newmetalbums-backend:latest
```

## Monitoring Builds

### GitHub Actions Tab
1. Go to your repository
2. Click **Actions** tab
3. View build status and logs

### Container Registry
1. Go to your repository
2. Click **Packages** tab (right sidebar)
3. View published images and download stats

## Troubleshooting

### Build Failures

**Common issues:**
- **Permission denied**: Check workflow permissions in repository settings
- **Registry authentication**: Ensure GITHUB_TOKEN has package write permissions
- **Multi-arch build fails**: Some dependencies may not support ARM64

### ARM64 Compatibility

**Playwright on ARM64:**
- The workflow installs Chromium for both architectures
- ARM64 builds may take longer due to emulation

**Node.js on ARM64:**
- Uses official Node.js Alpine images with native ARM64 support
- All dependencies should work correctly

### Manual Testing

Test multi-arch builds locally:

```bash
# Enable buildx
docker buildx create --use

# Build for multiple architectures
docker buildx build --platform linux/amd64,linux/arm64 -t test-image .

# Test ARM64 on AMD64 (emulated)
docker run --platform linux/arm64 test-image
```

## Security

### Vulnerability Scanning
- **Trivy scanner** runs on every build
- Results appear in **Security** tab
- Critical vulnerabilities block deployments

### Registry Security
- Images are signed and verified
- Private repositories require authentication
- Public images are available to everyone

## Cost Optimization

### Build Caching
- **GitHub Actions cache** reduces build times
- **Layer caching** minimizes data transfer
- **Incremental builds** only rebuild changed layers

### Resource Usage
- **2000 minutes/month** free for public repositories
- **500 MB storage** free for packages
- **Unlimited bandwidth** for public packages

## Advanced Configuration

### Custom Build Arguments

Add build arguments to the workflow:

```yaml
- name: Build and push backend Docker image
  uses: docker/build-push-action@v5
  with:
    build-args: |
      BUILD_VERSION=${{ github.sha }}
      BUILD_DATE=${{ github.event.head_commit.timestamp }}
```

### Matrix Builds

Build multiple variants:

```yaml
strategy:
  matrix:
    variant: [slim, full]
    platform: [linux/amd64, linux/arm64]
```

### Conditional Builds

Skip builds for documentation changes:

```yaml
on:
  push:
    paths-ignore:
      - '**.md'
      - 'docs/**'
```

## Files Created

- **`.github/workflows/docker-build.yml`**: Main workflow
- **`docker-compose.production.yml`**: Production deployment
- **`Dockerfile.backend`**: Updated with multi-arch support
- **`frontend/Dockerfile`**: Updated with multi-arch support

## Next Steps

1. **Push to GitHub** to trigger first build
2. **Monitor build progress** in Actions tab
3. **Test deployment** with production compose file
4. **Set up monitoring** for production deployments
5. **Configure alerts** for build failures
