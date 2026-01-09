# Portable Windows Build Instructions for Radiant Core

> **Recommended**: For the smoothest development experience on Windows, we recommend using **WSL2** (Windows Subsystem for Linux). See [Option 0: WSL2](#option-0-wsl2-recommended) below.

## Prerequisites
- Windows 10/11
- Visual Studio 2019/2022 with C++ development tools OR MinGW-w64
- CMake 3.22+
- Python 3.6+
- Git

## Option 0: WSL2 (Recommended)

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
- Access daemon from Windows via `localhost`
- Easier dependency management via apt

## Option 1: Using Visual Studio (Native Windows)

### Step 1: Install Dependencies
1. Install Visual Studio 2019/2022 with C++ development tools
2. Install vcpkg: `git clone https://github.com/Microsoft/vcpkg.git`
3. Install vcpkg packages:
   ```
   cd vcpkg
   .\bootstrap-vcpkg.bat
   .\vcpkg install openssl:x64-windows
   .\vcpkg install boost:x64-windows
   .\vcpkg install libevent:x64-windows
   ```

### Step 2: Build
```cmd
mkdir build
cd build
cmake .. -G "Visual Studio 16 2019" -A x64 -DCMAKE_TOOLCHAIN_FILE=C:\path\to\vcpkg\scripts\buildsystems\vcpkg.cmake -DBUILD_RADIANT_WALLET=OFF -DBUILD_RADIANT_ZMQ=OFF -DENABLE_UPNP=OFF
cmake --build . --config Release
```

## Option 2: Using MinGW-w64 via MSYS2

> **Important**: You must install libevent via MSYS2 pacman. Do not use the bundled libevent-stubs as they do not provide full functionality (RPC will not work).

### Step 1: Install Dependencies
1. Install MSYS2: https://www.msys2.org/
2. Open **MSYS2 MinGW64** shell (not MSYS2 MSYS)
3. Install dependencies:
   ```bash
   pacman -Syu
   pacman -S mingw-w64-x86_64-gcc
   pacman -S mingw-w64-x86_64-cmake
   pacman -S mingw-w64-x86_64-openssl
   pacman -S mingw-w64-x86_64-boost
   pacman -S mingw-w64-x86_64-libevent  # Critical for RPC functionality
   pacman -S mingw-w64-x86_64-python
   ```

### Step 2: Build (Portable)
```cmd
# Make sure to use the MSYS2 MinGW shell
mkdir build
cd build
cmake .. -G "MinGW Makefiles" -DBUILD_RADIANT_WALLET=OFF -DBUILD_RADIANT_ZMQ=OFF -DENABLE_UPNP=OFF
mingw32-make -j$(nproc)
```

## Creating a Portable Distribution

### Step 1: Copy Required DLLs
After building, copy these DLLs to the output directory:
- libssl-3-x64.dll
- libcrypto-3-x64.dll
- libevent-2-1.dll
- libgcc_s_seh-1.dll
- libstdc++-6.dll
- libwinpthread-1.dll

### Step 2: Create Installer
Use NSIS or WiX to create an installer that includes:
- All executables (radiantd.exe, radiant-cli.exe, radiant-tx.exe)
- Required DLLs
- Configuration files
- Documentation

## Automated Build Script

For automated building, use the provided scripts:
- `build-portable-windows.bat` - Automated Windows build
- `create-installer.nsi` - NSIS installer script

## Known Issues

### libevent-stubs and RPC Functionality

The repository contains a `libevent-stubs.c` file that provides stub implementations of libevent functions. **These stubs do not provide full functionality:**

- The HTTP event loop exits immediately, breaking RPC server functionality
- `radiant-cli` will fail with assertion errors when trying to connect
- Mining via RPC (`generatetoaddress`) will not work

**Solution**: Always use real libevent from vcpkg or MSYS2 packages. The stubs were a temporary workaround and should not be used for production builds.

### Static Initialization Issues

When mixing different MinGW toolchains or library versions, you may encounter crashes during startup (e.g., in `GetRand()`). This is typically caused by:

- ABI incompatibilities between different GCC versions
- Static initialization order problems
- Mixing libraries built with different compilers

**Solution**: Use a consistent toolchain. Either:
1. Build everything in MSYS2 MinGW64 environment
2. Use vcpkg with Visual Studio
3. Use WSL2 (recommended)
