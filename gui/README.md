# Radiant Node GUI

A simple browser-based GUI for running a Radiant node. Designed for non-technical users to easily start and manage their node.

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

Download wallet-enabled binaries from the releases page.

**Note:** When the GUI starts a node, it automatically enables wallet functionality with the `-disablewallet=0` flag.

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

### macOS
1. Double-click `run_node_gui.command`
2. If prompted, right-click → Open to bypass Gatekeeper

### Linux
```bash
chmod +x run_node_gui.sh
./run_node_gui.sh
```

### Windows
Double-click `run_node_gui.bat`

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
- Or download pre-built binaries and place in one of the above locations

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

## Building Radiant Node

If you haven't built the node binaries yet:

```bash
# Install dependencies (macOS)
brew install cmake boost openssl libevent

# Build
mkdir build && cd build
cmake ..
make -j$(nproc)
```

See [INSTALL.md](../INSTALL.md) for detailed build instructions.

## Support

- Website: [radiantblockchain.org](https://radiantblockchain.org)
- Documentation: [doc/](../doc/)

## License

This software is released under the MIT License. See [COPYING](../COPYING) for details.
