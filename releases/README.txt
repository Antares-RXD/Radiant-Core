Radiant Core v2.0.0 Release
===========================

Release artifacts for Radiant Core v2.0.0.

Available Releases:
------------------
- Linux/                - Linux x86_64 binaries
- Mac - Apple Silicon/  - macOS ARM64 (Apple Silicon) binaries
- Windows/              - Windows x86_64 binaries + GUI
- Docker/               - Docker image tarball
- Radiant-Core-GUI-2.0.0.dmg - macOS GUI Application (node + wallet)

All releases include:
- radiantd      - Node daemon
- radiant-cli   - Command-line interface
- radiant-tx    - Transaction utility
- Wallet support enabled

Build Configuration:
--------------------
All releases are built with the following recommended options:

  cmake \
    -DCMAKE_BUILD_TYPE=Release \
    -DBUILD_RADIANT_WALLET=ON \
    -DBUILD_RADIANT_DAEMON=ON \
    -DBUILD_RADIANT_CLI=ON \
    -DBUILD_RADIANT_TX=ON \
    -DBUILD_RADIANT_ZMQ=ON \
    -DENABLE_HARDENING=ON \
    -DENABLE_UPNP=ON \
    ..

| Option               | Value | Description                    |
|----------------------|-------|--------------------------------|
| BUILD_RADIANT_WALLET | ON    | Wallet functionality (GUI)     |
| BUILD_RADIANT_DAEMON | ON    | Main node binary               |
| BUILD_RADIANT_CLI    | ON    | Command-line interface         |
| BUILD_RADIANT_TX     | ON    | Transaction utility            |
| BUILD_RADIANT_ZMQ    | ON    | Real-time notifications        |
| ENABLE_HARDENING     | ON    | Security hardening             |
| ENABLE_UPNP          | ON    | Automatic port forwarding      |

Build Scripts:
--------------
To rebuild releases with the same configuration:

  ./build-mac-arm64.sh   # macOS Apple Silicon
  ./build-linux-x64.sh   # Linux x86_64 (run on Linux)
  ./build-docker.sh      # Docker image

Linux x86_64:
-------------
  # Install runtime dependencies (Ubuntu 22.04)
  sudo apt-get install libboost-chrono1.74.0 libboost-filesystem1.74.0 \
    libboost-thread1.74.0 libevent-2.1-7 libevent-pthreads-2.1-7 \
    libssl3 libdb5.3++ libminiupnpc17 libzmq5

  # Extract and run
  cd Linux
  tar -xzf radiant-core-linux-x64.tar.gz
  cd radiant-core-linux-x64
  ./radiantd --version
  ./radiantd -server -txindex=1

macOS (Apple Silicon):
----------------------

  OPTION 1: GUI Application (Recommended for most users)
  -------------------------------------------------------
  Download Radiant-Core-GUI-2.0.0.dmg, open it, and drag to Applications.
  Double-click to launch - includes node and wallet in one app.
  
  If blocked by Gatekeeper:
    xattr -rd com.apple.quarantine /Applications/Radiant\ Core.app

  OPTION 2: Command-Line Binaries
  --------------------------------
  cd "Mac - Apple Silicon"
  unzip radiant-core-macos-arm64.zip
  cd radiant-core-macos-arm64
  
  # Remove quarantine (required for downloaded files)
  xattr -rd com.apple.quarantine .
  
  ./radiantd --version
  ./radiantd -server -txindex=1

Docker:
-------
  # Load the image (x86_64/amd64 architecture)
  docker load < Docker/radiant-core-docker-v2.0.0.tar.gz
  
  # Run with wallet support
  docker run -d --name radiant-node \
    -p 7332:7332 -p 7333:7333 \
    -v radiant-data:/home/radiant/.radiant \
    radiant-core:v2.0.0-amd64
  
  # Check status
  docker exec radiant-node radiant-cli getblockchaininfo
  
  # View wallet commands
  docker exec radiant-node radiant-cli help | grep -A50 "== Wallet =="

Windows (x86_64):
-----------------
  cd Windows
  .\radiantd.exe --version
  .\radiantd.exe -server -txindex=1

  Files included:
  - radiantd.exe          - Node daemon
  - radiant-cli.exe       - Command-line interface
  - RadiantCore.exe       - GUI application (optional)
  - Required DLLs:
    - libcrypto-3-x64.dll, libssl-3-x64.dll (OpenSSL)
    - libdb_cxx-6.2.dll (BerkeleyDB)
    - libevent-7.dll, libevent_core-7.dll, libevent_extra-7.dll, libevent_openssl-7.dll
    - libzmq.dll, libsodium-26.dll (ZeroMQ)
    - libgcc_s_seh-1.dll, libstdc++-6.dll, libwinpthread-1.dll (MinGW runtime)
    - libqrencode.dll, zlib1.dll

Windows (Native GUI):
---------------------
  For end users, we provide a native Windows GUI application in the Windows/ folder:
  
  1. Double-click RadiantCore.exe (in the Windows/ folder)
  
  2. The GUI will automatically launch in your browser at http://127.0.0.1:8765
  
  3. All required DLLs and node binaries are included in the same folder

Windows (via WSL2 - for developers):
------------------------------------
  1. Install WSL2: wsl --install -d Ubuntu-24.04
  2. Use the Linux release inside WSL2

Verify Checksums:
-----------------
Each release includes a .sha256 file. Verify with:
  shasum -a 256 -c <release>.sha256

Ports:
------
- Mainnet: 7332 (RPC), 7333 (P2P)
- Testnet: 27332 (RPC), 27333 (P2P)

For more information: https://radiantblockchain.org
Source: https://github.com/Radiant-Core/Radiant-Core
