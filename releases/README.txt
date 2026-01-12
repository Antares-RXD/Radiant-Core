Radiant Core v2.0.0 Release
===========================

Release artifacts for Radiant Core v2.0.0.

Available Releases:
------------------
- Linux/        - Linux x86_64 binaries
- Mac - Apple Silicon/  - macOS ARM64 (Apple Silicon) binaries
- Docker/       - Docker image tarball

Linux x86_64:
-------------
  cd Linux
  tar -xzf radiant-core-linux-x86_64.tar.gz
  cd radiant-core-linux-x86_64
  ./radiantd --version
  ./radiantd -server -txindex=1

macOS (Apple Silicon):
----------------------
  cd "Mac - Apple Silicon"
  tar -xzf radiant-core-macos-arm64.tar.gz
  cd radiant-core-macos-arm64
  ./radiantd --version
  ./radiantd -server -txindex=1

Docker:
-------
  # Load the image
  docker load < Docker/radiant-core-docker-v2.0.0.tar.gz
  
  # Or use the pre-built image
  docker run -d --name radiant-node \
    -p 7332:7332 -p 7333:7333 \
    -v radiant-data:/home/radiant/.radiant \
    radiant-core:v2.0.0
  
  # Check status
  docker exec radiant-node radiant-cli getblockchaininfo

Windows (via WSL2):
-------------------
  1. Install WSL2: wsl --install -d Ubuntu-24.04
  2. Use the Linux release inside WSL2

Verify Checksums:
-----------------
Each release includes a .sha256 file. Verify with:
  shasum -a 256 -c <release>.tar.gz.sha256

Ports:
------
- Mainnet: 7332 (RPC), 7333 (P2P)
- Testnet: 27332 (RPC), 27333 (P2P)

For more information: https://radiantblockchain.org
Source: https://github.com/Radiant-Core/Radiant-Core
