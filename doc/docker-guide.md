# Docker Build Guide

This document explains the different Dockerfiles available for Radiant Core and their intended use cases.

## Quick Start with Pre-built Release

The fastest way to run Radiant Core via Docker:

```bash
# Load the pre-built image from releases/Docker/
docker load < releases/Docker/radiant-core-docker-v2.0.0.tar.gz

# Run the node
docker run -d --name radiant-node \
  -p 7332:7332 -p 7333:7333 \
  -v radiant-data:/home/radiant/.radiant \
  radiant-core:v2.0.0

# Check status
docker exec radiant-node radiant-cli getblockchaininfo
```

## Dockerfiles Overview

### Production Dockerfiles

#### `docker/Dockerfile.release` (Recommended for Production)
**Multi-stage build optimized for production deployments**

- **Base**: Ubuntu 24.04 (multi-stage: builder + runtime)
- **Size**: Optimized minimal runtime image
- **Features**: 
  - Multi-stage build (smaller final image)
  - Non-root user execution
  - Health checks included
  - Production-ready configuration
- **Use Case**: Production deployments, Docker Hub releases
- **Build**: `docker build -f docker/Dockerfile.release -t radiant-core:latest .`

#### `docker/Dockerfile.base` (Legacy Production)
**Full production image with Node.js and mining support**

- **Base**: Ubuntu 24.04
- **Features**: 
  - Includes Node.js 20 (for ElectrumX/RXinDexer)
  - GPU mining support (OpenCL)
  - Builds from GitHub source
- **Use Case**: Legacy production, mining operations
- **Note**: Consider using `docker/Dockerfile.release` for standard deployments

### Development Dockerfiles

#### `docker/Dockerfile.core` (Local Development)
**Build from local source tree**

- **Base**: Ubuntu 24.04
- **Features**:
  - Builds from current directory source
  - Development-friendly configuration
  - Debug logging enabled
- **Use Case**: Local development and testing
- **Build**: `docker build -f docker/Dockerfile.core -t radiant-core-local .`

#### `docker/Dockerfile.ci` (Continuous Integration)
**Complete CI/CD build environment**

- **Base**: Ubuntu 24.04
- **Features**:
  - Full build tools and dependencies
  - Cross-compilation support (Windows, ARM, AArch64)
  - Documentation tools (Doxygen)
  - Python testing dependencies
- **Use Case**: CI/CD pipelines, automated testing
- **Build**: `docker build -f docker/Dockerfile.ci -t radiant-core-ci .`

### Specialized Dockerfiles

#### `docker/Dockerfile.testnet` (Testnet Node)
**Pre-configured for Radiant testnet**

- **Base**: Ubuntu 24.04
- **Features**:
  - Testnet configuration pre-loaded
  - Testnet ports exposed (27332, 27333)
  - Runtime-only (no build tools)
- **Use Case**: Testnet deployments
- **Build**: `docker build -f docker/Dockerfile.testnet -t radiant-core-testnet .`

#### `docker/Dockerfile.seeder` (DNS Seeder)
**DNS seed node for network discovery**

- **Base**: Ubuntu 24.04
- **Features**:
  - Builds only the seeder component
  - Exposes DNS port (53/udp)
  - Minimal footprint
- **Use Case**: Network infrastructure, DNS seeding
- **Build**: `docker build -f docker/Dockerfile.seeder -t radiant-seeder .`

#### `docker/Dockerfile.orbstack` (macOS Development)
**OrbStack-specific configuration for macOS users**

- **Base**: Ubuntu 24.04
- **Features**:
  - Mining support (GPU/OpenCL)
  - Testnet configuration
  - Optimized for OrbStack on macOS
- **Use Case**: macOS development with OrbStack
- **Build**: `docker build -f docker/Dockerfile.orbstack -t radiant-orbstack .`

## Usage Examples

### Production Deployment
```bash
# Build and run production image
docker build -f docker/Dockerfile.release -t radiant-core:latest .
docker run -d --name radiant-node \
  -p 7332:7332 -p 7333:7333 \
  -v radiant-data:/home/radiant/.radiant \
  radiant-core:latest
```

### Local Development
```bash
# Build from local source
docker build -f docker/Dockerfile.core -t radiant-core-local .
docker run --rm -it -p 7332:7332 -p 7333:7333 radiant-core-local
```

### Testnet Deployment
```bash
# Build and run testnet node
docker build -f docker/Dockerfile.testnet -t radiant-testnet .
docker run -d --name radiant-testnet \
  -p 27332:27332 -p 27333:27333 \
  -v testnet-data:/home/radiant/.radiant \
  radiant-testnet
```

### CI/CD Build
```bash
# Build CI environment
docker build -f docker/Dockerfile.ci -t radiant-core-ci .
docker run --rm -v $PWD:/source radiant-core-ci \
  bash -c "cd /source && mkdir build && cd build && cmake .. && ninja"
```

## Configuration

### Environment Variables
- `DEBIAN_FRONTEND=noninteractive`: Prevents interactive prompts during build
- `CCACHE_DIR`: CCache directory for faster builds (CI Dockerfile)
- `GIT_TAG`: Git tag to build (Release Dockerfile)
- `BUILD_TYPE`: CMake build type (Release Dockerfile)

### Ports
- **Mainnet**: 7332 (RPC), 7333 (P2P)
- **Testnet**: 27332 (RPC), 27333 (P2P)
- **Seeder**: 53/udp (DNS)

### Volumes
- `/home/radiant/.radiant`: Default data directory
- `/ccache`: Build cache (CI Dockerfile)

## Security Considerations

1. **Non-root User**: All production Dockerfiles run as non-root `radiant` user
2. **Minimal Runtime**: `docker/Dockerfile.release` uses multi-stage build for minimal attack surface
3. **RPC Security**: Avoid exposing RPC ports publicly without authentication
4. **Health Checks**: Production images include health checks for monitoring

## Migration Guide

### From Legacy Dockerfile to Release Dockerfile
If you're currently using the main `docker/Dockerfile.base`, consider migrating to `docker/Dockerfile.release`:

```bash
# Old way
docker build -t radiant-core .
docker run radiant-core radiantd -server

# New way
docker build -f docker/Dockerfile.release -t radiant-core:latest .
docker run radiant-core:latest
```

Benefits:
- Smaller image size
- Better security (non-root user)
- Health checks included
- Production-ready defaults

## Troubleshooting

### Build Issues
- Ensure Docker has sufficient memory (4GB+ recommended)
- Use `docker/Dockerfile.core` for local development if network issues occur
- Check for sufficient disk space (multi-stage builds require more space)

### Runtime Issues
- Verify port mappings (mainnet vs testnet)
- Check volume permissions for data persistence
- Use `docker logs` to debug startup issues

### Performance Optimization
- Use `docker/Dockerfile.release` for production (smaller size, faster startup)
- Enable build cache with `CCACHE_DIR` volume in CI
- Consider resource limits for mining operations

## Windows Support

Windows users should use WSL2 or Docker Desktop with WSL2 backend. Native Windows builds are deprecated. See [build-windows-portable.md](build-windows-portable.md) for detailed WSL2 setup instructions.
