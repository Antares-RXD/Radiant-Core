# Building Radiant Core on Windows

> **Important**: Native Windows builds are not supported. We recommend using **WSL2** (Windows Subsystem for Linux) for the best experience on Windows.

## Prerequisites
- Windows 10/11 (Build 19041 or higher)
- WSL2 enabled

## WSL2 Build Instructions (Recommended)

WSL2 provides a native Linux environment on Windows, avoiding Windows-specific dependency issues. This is the recommended approach for development and testing.

### Step 1: Install WSL2
```powershell
# Run in PowerShell as Administrator
wsl --install -d Ubuntu-22.04
```

Restart your computer after installation.

### Step 2: Install Dependencies in WSL2
```bash
# In WSL2 Ubuntu terminal
sudo apt update
sudo apt install -y build-essential cmake pkg-config git python3
sudo apt install -y libssl-dev libboost-all-dev libevent-dev
```

### Step 3: Clone and Build
```bash
cd ~
git clone https://github.com/aspect-build/radiant-core.git
cd radiant-core
mkdir build && cd build
cmake .. -DBUILD_RADIANT_WALLET=OFF -DBUILD_RADIANT_ZMQ=OFF -DENABLE_UPNP=OFF
make -j$(nproc)
```

### Step 4: Run
```bash
# The daemon is accessible from Windows via localhost
./src/radiantd -regtest -printtoconsole

# In another terminal
./src/radiant-cli -regtest getblockchaininfo
```

**Advantages of WSL2:**
- Native Linux build process (no Windows-specific issues)
- Full libevent support (RPC works correctly)
- Full wallet support (BerkeleyDB works correctly)
- Access daemon from Windows via `localhost`
- Easier dependency management via apt
- Consistent behavior with Linux production environments

## Accessing the Node from Windows

Once the node is running in WSL2, you can access it from Windows:

```powershell
# From Windows PowerShell, connect to the node running in WSL2
wsl ./src/radiant-cli -regtest getblockchaininfo

# Or access via localhost (RPC port 7332)
curl --user user:password --data-binary '{"jsonrpc":"1.0","method":"getblockchaininfo","params":[]}' http://127.0.0.1:7332/
```

## Why Not Native Windows Builds?

Native Windows builds have been deprecated due to persistent issues:

- **libevent compatibility**: The RPC server requires full libevent functionality that is difficult to achieve on native Windows
- **BerkeleyDB 4.8.30**: Incompatible with VS2022's modern C++ headers (macro conflicts)
- **Toolchain complexity**: Mixing MinGW/MSVC toolchains causes ABI and static initialization issues
- **CI reliability**: GitHub Actions Windows builds consistently fail

WSL2 provides a fully supported Linux environment that avoids all these issues while still allowing Windows users to run and develop Radiant Core.

## Docker Alternative

If you prefer not to use WSL2, you can also use Docker Desktop for Windows:

```powershell
# Build and run via Docker
docker build -t radiant-core .
docker run -d --name radiant-node -p 7332:7332 -p 7333:7333 radiant-core
```

See the main [README.md](README.md) for Docker instructions.
