# WINDOWS BUILD NOTES

## For End Users: Native Windows GUI (Recommended)

We provide a native Windows GUI application that bundles pre-built binaries:

1. Download from `gui/dist/`:
   - `RadiantCore.exe` - The GUI application
   - `radiant-core-windows-x64.zip` - Node binaries and DLLs

2. Keep both files in the same folder and double-click `RadiantCore.exe`

See [gui/README.md](../gui/README.md) for detailed instructions.

---

## For Developers: Building from Source

> **Note**: Native Windows builds from source are complex. We recommend using **WSL2** (Windows Subsystem for Linux) for development.

## Recommended: WSL2 with Native Linux Build

WSL2 provides a full Linux environment on Windows, avoiding all Windows-specific build issues.

### Step 1: Install WSL2

```powershell
# Run in PowerShell as Administrator
wsl --install -d Ubuntu-22.04
```

Restart your computer after installation.

### Step 2: Build in WSL2

Once WSL2 is installed, follow the [Unix build guide](build-unix.md) for complete instructions.

Quick start:
```bash
# In WSL2 Ubuntu terminal
sudo apt update
sudo apt install -y build-essential cmake ninja-build pkg-config git python3
sudo apt install -y libssl-dev libboost-all-dev libevent-dev libdb++-dev

cd ~
git clone https://github.com/radiantblockchain/radiant-node.git
cd radiant-node
mkdir build && cd build
cmake -GNinja .. -DBUILD_RADIANT_WALLET=ON
ninja
```

### Step 3: Run

```bash
# The daemon is accessible from Windows via localhost
./src/radiantd -printtoconsole

# In another terminal
./src/radiant-cli getblockchaininfo
```

## Why Not Native Windows Builds?

Native Windows builds have been deprecated due to:

- **libevent compatibility issues**: RPC server functionality is unreliable
- **BerkeleyDB 4.8.30 conflicts**: Incompatible with modern MSVC headers
- **Toolchain complexity**: MinGW/MSVC mixing causes ABI issues
- **CI reliability**: Windows builds consistently fail in GitHub Actions

WSL2 provides a fully supported Linux environment that avoids these issues.

## Docker Alternative

You can also use Docker Desktop for Windows:

```powershell
docker build -t radiant-core .
docker run -d --name radiant-node -p 7332:7332 -p 7333:7333 radiant-core
```

See the main [README.md](../README.md) for Docker instructions.
