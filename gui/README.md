# Radiant Node GUI

A simple browser-based GUI for running a Radiant node. Designed for non-technical users to easily start and manage their node.

## Download

Get the **All-in-One Package** for your platform (includes GUI + node binaries):

| Platform | Download | Size |
|----------|----------|------|
| **Windows (x64)** | [releases/Windows/](../releases/Windows/) | ~46 MB |
| **macOS (Apple Silicon)** | [radiant-node-gui-macos-v2.0.0.tar.gz](https://github.com/Radiant-Core/Radiant-Core/releases/download/v2.0.0/radiant-node-gui-macos-v2.0.0.tar.gz) | ~15 MB |
| **Linux (x86_64)** | [radiant-node-gui-linux-x64-v2.0.0.tar.gz](https://github.com/Radiant-Core/Radiant-Core/releases/download/v2.0.0/radiant-node-gui-linux-x64-v2.0.0.tar.gz) | ~20 MB |

### Quick Install

**Windows (Recommended for most users):**

1. Go to `releases/Windows/` folder (all binaries and DLLs are pre-extracted)

2. Double-click `RadiantCore.exe`

3. The GUI will launch in your default web browser at `http://127.0.0.1:8765`

**macOS:**
```bash
# Download and extract
curl -LO https://github.com/Radiant-Core/Radiant-Core/releases/download/v2.0.0/radiant-node-gui-macos-v2.0.0.tar.gz
tar xzf radiant-node-gui-macos-v2.0.0.tar.gz
cd radiant-node-gui-macos-v2.0.0

# Remove quarantine (required for downloaded apps)
xattr -rd com.apple.quarantine .

# Launch - double-click start-gui.command or run:
./start-gui.command
```

**Linux:**
```bash
curl -LO https://github.com/Radiant-Core/Radiant-Core/releases/download/v2.0.0/radiant-node-gui-linux-x64-v2.0.0.tar.gz
tar xzf radiant-node-gui-linux-x64-v2.0.0.tar.gz
cd radiant-node-gui-linux-x64-v2.0.0
./start-gui.sh
```

The GUI opens automatically in your browser at **http://127.0.0.1:8765**

## Features

- **One-click start/stop** - Start and stop your node with a single button click
- **Real-time status** - See sync progress, block count, and peer count in real-time
- **Network selection** - Easily switch between mainnet, testnet, and regtest
- **Pruning support** - Enable pruning to save disk space
- **Log output** - View node activity in the built-in log panel
- **Node info** - View detailed node information with one click
- **No dependencies** - Uses only Python standard library, works everywhere
- **Modern UI** - Clean interface with light/dark mode toggle
- **Wallet Integration** - Send/receive RXD, view balances and transactions (requires wallet-enabled build)
- **Auto-start** - Optionally start the node automatically when GUI launches
- **Auto-download binaries** - Automatically detect your platform and download pre-built binaries
- **Wallet Backup & Restore** - Export/import private keys and seed phrases for wallet recovery

## Architecture

### How the GUI Interfaces with the Node

The GUI communicates with the Radiant node through **RPC (Remote Procedure Call)**:

```
┌─────────────┐     HTTP      ┌─────────────────┐    RPC     ┌───────────┐
│   Browser   │ ◄──────────► │  Python Backend  │ ◄────────► │  radiantd │
│   (GUI)     │   Port 8765   │ (radiant_node_   │  via CLI   │   (node)  │
└─────────────┘               │    web.py)       │            └───────────┘
                              └─────────────────┘
```

**Data Flow:**
1. Browser sends requests to Python backend on `http://127.0.0.1:8765`
2. Python backend executes `radiant-cli` commands to communicate with the node
3. Node responds via RPC, Python parses and returns JSON to browser

**Key RPC Commands Used:**
| Command | Purpose |
|---------|----------|
| `getblockchaininfo` | Block height, sync progress, chain name |
| `getnetworkinfo` | Peer count, version info |
| `getwalletinfo` | Wallet balance, status |
| `getnewaddress` | Generate new receiving address |
| `sendtoaddress` | Send RXD transactions |
| `listtransactions` | Transaction history |

**Requirements for RPC:**
- Node must have `server=1` in config (the GUI sets this automatically)
- RPC is local-only by default for security

### Wallet Support

The Wallet tab requires the node to be compiled with wallet support. If you see "Wallet not available" in the GUI:

**Option 1: Build from source with wallet enabled**
```bash
cd radiant-core
mkdir -p build && cd build
cmake -DBUILD_RADIANT_WALLET=ON ..
make -j$(nproc)
```

**Option 2: Use pre-built binaries with wallet support**

Download wallet-enabled binaries from the [GitHub Releases page](https://github.com/Radiant-Core/Radiant-Core/releases/tag/v2.0.0):

| Platform | Download |
|----------|----------|
| macOS (Apple Silicon) | [radiant-core-macos-arm64.tar.gz](https://github.com/Radiant-Core/Radiant-Core/releases/download/v2.0.0/radiant-core-macos-arm64.tar.gz) |
| Linux (x86_64) | [radiant-core-linux-x64.tar.gz](https://github.com/Radiant-Core/Radiant-Core/releases/download/v2.0.0/radiant-core-linux-x64.tar.gz) |
| Docker (x86_64) | [radiant-core-docker-v2.0.0.tar.gz](https://github.com/Radiant-Core/Radiant-Core/releases/download/v2.0.0/radiant-core-docker-v2.0.0.tar.gz) |

**Quick setup (macOS):**
```bash
# Download and extract
curl -LO https://github.com/Radiant-Core/Radiant-Core/releases/download/v2.0.0/radiant-core-macos-arm64.tar.gz
tar xzf radiant-core-macos-arm64.tar.gz

# Remove quarantine (required for downloaded binaries)
xattr -rd com.apple.quarantine radiant-core-macos-arm64

# Run the GUI
cd radiant-core-macos-arm64
python3 ../gui/radiant_node_web.py
```

**Quick setup (Linux):**
```bash
curl -LO https://github.com/Radiant-Core/Radiant-Core/releases/download/v2.0.0/radiant-core-linux-x64.tar.gz
tar xzf radiant-core-linux-x64.tar.gz
cd radiant-core-linux-x64
./radiantd -server -txindex=1
```

**Note:** When the GUI starts a node, it automatically enables wallet functionality with the `-disablewallet=0` flag.

### Wallet Backup & Restore

The GUI provides several ways to backup and restore your wallet:

#### Backup Options

| Method | Description | Use Case |
|--------|-------------|----------|
| **Backup Wallet File** | Creates a copy of `wallet.dat` | Full backup of all keys and transactions |
| **Export Private Key** | Exports WIF key for a specific address | Backup individual addresses |
| **Export Seed Phrase** | 12/24-word mnemonic phrase | Human-readable backup, easy to write down |

#### Restore Options

| Method | Description |
|--------|-------------|
| **Import Private Key** | Import a WIF-format private key |
| **Import Seed Phrase** | Restore wallet from 12/24-word mnemonic |

#### Using Seed Phrases (Recommended)

Seed phrases are the safest way to backup your wallet:

1. Go to **Wallet** tab → **Backup & Restore** section
2. Click **Generate Seed Phrase** to create a new 12-word phrase
3. **Write it down on paper** - never store digitally!
4. To restore: Enter your seed phrase and click **Import Seed Phrase**

⚠️ **Security Warning:**
- Never share your seed phrase or private keys
- Anyone with access can steal your funds
- Store backups in a secure, offline location

### Interfacing with an Existing Node

If you have a node already running (started outside the GUI), the GUI can interface with it as long as:
- The node was started with RPC enabled (`server=1`)
- The `radiant-cli` binary is accessible
- The node is running on the expected network (mainnet/testnet/regtest)

The GUI will detect the running node and display its status.

## Requirements

- **Python 3.6+** - Usually pre-installed on macOS and Linux
- **Radiant Node binaries** - Either build from source or download pre-built binaries
- **Web browser** - Any modern browser (Chrome, Firefox, Safari, Edge)

### Installing Python

#### macOS
Python 3 is usually pre-installed. If not:
```bash
brew install python3
```

#### Linux (Ubuntu/Debian)
```bash
sudo apt install python3
```

#### Windows
Download from [python.org/downloads](https://www.python.org/downloads/)

## Quick Start

### Windows (Native GUI - Recommended)
1. Go to `releases/Windows/` folder
2. Double-click `RadiantCore.exe`
3. The GUI opens automatically in your browser at `http://127.0.0.1:8765`

**Files included in releases/Windows/:**
- `RadiantCore.exe` - GUI application
- `radiantd.exe` - The Radiant node daemon
- `radiant-cli.exe` - Command-line interface
- Required DLLs (OpenSSL, libevent, BerkeleyDB, ZeroMQ, etc.)

### macOS
1. Double-click `run_node_gui.command`
2. If prompted, right-click → Open to bypass Gatekeeper

### Linux
```bash
chmod +x run_node_gui.sh
./run_node_gui.sh
```

### Command Line (All Platforms)
```bash
python3 radiant_node_web.py
```

## Usage

### Starting the Node

1. Launch the GUI application
2. (Optional) Adjust settings:
   - **Network**: Choose mainnet, testnet, or regtest
   - **Data Dir**: Where blockchain data is stored
   - **Pruning**: Enable to save disk space (minimum 550 MB)
3. Click **▶ Start Node**
4. Watch the log output for progress

### Stopping the Node

1. Click **■ Stop Node**
2. Wait for graceful shutdown
3. The status indicator will turn gray when stopped

### Viewing Node Info

Click **ℹ Node Info** to see:
- Blockchain sync status
- Network information
- Connected peers

## Settings

Settings are automatically saved to `node_settings.json` in the gui folder.

### Network Options

| Network | Description |
|---------|-------------|
| mainnet | Main Radiant network (real RXD) |
| testnet | Test network (test RXD, no value) |
| regtest | Local regression testing network |

### Pruning

Pruning reduces disk usage by deleting old block data. The blockchain will still be fully validated but you won't be able to serve old blocks to other nodes.

- **Minimum**: 550 MB
- **Recommended**: 1000+ MB for better performance

## Troubleshooting

### "Could not find radiantd binary"

The GUI looks for the node binary in these locations:
1. `build/src/radiantd` (after building)
2. `src/radiantd`
3. `/usr/local/bin/radiantd`
4. `/usr/bin/radiantd`

**Solutions:**
- Build the node from source: See [INSTALL.md](../INSTALL.md)
- Or download pre-built binaries from [GitHub Releases](https://github.com/Radiant-Core/Radiant-Core/releases/tag/v2.0.0)
- Or use the GUI's built-in **Download Binaries** feature (auto-detects your platform)

### Node won't start

1. Check the log output for error messages
2. Ensure the data directory exists and is writable
3. Check if another node is already running
4. Verify you have enough disk space

### GUI looks different on my system

The GUI uses your system's native theme. Appearance may vary between:
- macOS (Aqua theme)
- Windows (Windows theme)
- Linux (depends on desktop environment)

## Getting Binaries

### Option 1: Download Pre-built (Recommended)

The GUI can automatically download the correct binaries for your platform. Just click **Download Binaries** when prompted.

Or download manually from [GitHub Releases](https://github.com/Radiant-Core/Radiant-Core/releases/tag/v2.0.0).

### Option 2: Build from Source

```bash
# Install dependencies (macOS)
brew install cmake boost openssl libevent berkeley-db@4

# Build with wallet support
mkdir build && cd build
cmake -DBUILD_RADIANT_WALLET=ON ..
make -j$(sysctl -n hw.ncpu)
```

See [INSTALL.md](../INSTALL.md) for detailed build instructions.

## Support

- Website: [radiantblockchain.org](https://radiantblockchain.org)
- Documentation: [doc/](../doc/)

## License

This software is released under the MIT License. See [COPYING](../COPYING) for details.
