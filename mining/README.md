# Radiant Mining Suite

A complete mining solution for Radiant blockchain with both CPU and GPU support.

## Quick Start

### GPU Mining (Recommended - 50-100x faster)
```bash
# Install dependencies
pip install pyopencl numpy

# Start mining
./mining/start_gpu_miner.sh
```

### CPU Mining (Fallback)
```bash
# Start mining
./mining/start_cpu_miner.sh
```

## Features

- ✅ **GPU Mining** - OpenCL acceleration (50-100x speedup)
- ✅ **CPU Mining** - Python fallback
- ✅ **Auto-configuration** - Detects testnet/mainnet
- ✅ **Monitoring** - Real-time stats dashboard
- ✅ **Easy setup** - One-command start

## Requirements

### GPU Mining
- Python 3.11+
- PyOpenCL
- NumPy
- OpenCL-compatible GPU (Apple Silicon, NVIDIA, AMD)

### CPU Mining
- Python 3.11+
- Standard library only

## Configuration

### Node Profiles Integration

Radiant supports three node profiles optimized for different use cases:

| Profile | Description | Storage | Mining Recommended |
|---------|-------------|---------|-------------------|
| **archive** | Full history with transaction index | Unlimited | ❌ Higher resource usage |
| **agent** | Minimal UTXO-focused node | 550 MB | ❌ Heavy pruning affects mining |
| **mining** | Optimized for mining operations | 4 GB | ✅ Balanced performance |

### Start Node with Mining Profile
```bash
# Start node optimized for mining
./build/src/radiantd -testnet -nodeprofile=mining -server -rpcuser=testnet -rpcpassword=testnetpass123

# Or use the helper script
./mining/start_mining_node.sh
```

### Environment Variables
```bash
# RPC Settings (auto-configured for node profile)
export RPC_USER="testnet"
export RPC_PASS="testnetpass123"
export RPC_PORT="27332"  # Testnet port

# Mining Settings
export PROJECT_DIR="/path/to/radiant-core"
export BATCH_SIZE="4194304"  # GPU batch size
```

### Config File (mining/config.json)
```json
{
  "node_profiles": {
    "archive": {
      "description": "Full history node with transaction index",
      "prune": 0,
      "txindex": 1,
      "rpc": {"port": 8332, "testnet_port": 27332},
      "mining": {"recommended": false, "reason": "Full node with txindex"}
    },
    "agent": {
      "description": "Minimal node for UTXO-focused operations", 
      "prune": 550,
      "txindex": 0,
      "rpc": {"port": 8332, "testnet_port": 27332},
      "mining": {"recommended": false, "reason": "Heavy pruning affects mining"}
    },
    "mining": {
      "description": "Optimized for mining operations",
      "prune": 4000,
      "txindex": 0,
      "rpc": {"port": 8332, "testnet_port": 27332},
      "mining": {"recommended": true, "reason": "Balanced storage with recent blocks"}
    }
  },
  "network": "testnet",
  "genesis_hash": "000000000d8ada264d16f87a590b2af320cd3c7e3f9be5482163e830fd00aca2",
  "rpc": {
    "user": "testnet",
    "pass": "testnetpass123", 
    "port": 27332,
    "timeout": 30
  },
  "gpu": {
    "enabled": true,
    "batch_size": 4194304,
    "device": "auto",
    "platform": "auto"
  },
  "cpu": {
    "enabled": false,
    "threads": 4,
    "priority": "low"
  }
}
```

## Usage

### 1. Installation
```bash
# Install dependencies and setup configuration
./mining/install.sh
```

### 2. Start Node (Mining Profile)
```bash
# Start node optimized for mining
./mining/start_mining_node.sh

# Or for mainnet
./mining/start_mining_node.sh --mainnet
```

### 3. Start Mining
```bash
# Auto-detect and start best miner
./mining/start_mining.sh

# Or choose specific miner
./mining/start_gpu_miner.sh
./mining/start_cpu_miner.sh

# For mainnet
./mining/start_mining.sh --mainnet
```

### 4. Monitor
```bash
# Real-time dashboard
./mining/monitor.sh

# Quick status
./build/src/radiant-cli -testnet getblockchaininfo
```

## Performance

| Miner | Hash Rate | Speedup |
|-------|-----------|---------|
| GPU (Apple M3) | ~60M H/s | 85x |
| GPU (RTX 3080) | ~100M H/s | 140x |
| CPU (8-core) | ~700K H/s | 1x |

## ASIC Mining

Radiant uses SHA-512/256d algorithm. While theoretically compatible with SHA-256 ASICs, optimal performance requires dedicated SHA-512/256d hardware.

**Solution**: Run a Stratum Proxy that bridges ASIC miners to your Radiant node.

### Supported ASICs

#### Native SHA-512/256d ASICs (Recommended)
- **DragonBall A11** - First dedicated SHA-512/256d miner
- **Iceriver RX0** - High-performance SHA-512/256d miner
- **Future SHA-512/256d ASICs** - Emerging hardware ecosystem

#### SHA-256 ASICs (Compatible)
- **Antminer S9/S17/S19** series
- **WhatsMiner M30/M50** series  
- **AvalonMiner** series
- Any SHA-256 ASIC miner

**Note**: SHA-256 ASICs will work but may not achieve optimal efficiency compared to native SHA-512/256d hardware.

### Architecture
```
ASIC Miner → Stratum Proxy → Radiant Node
```

### Quick Setup (Recommended)

#### 1. Start Radiant Node
```bash
./mining/start_mining_node.sh
```

#### 2. Start Stratum Proxy
```bash
# Start proxy for testnet
./mining/start_stratum_proxy.sh

# For mainnet
./mining/start_stratum_proxy.sh --mainnet

# Custom port
./mining/start_stratum_proxy.sh --port=3333
```

The proxy will show connection details like:
```
ASIC Connection Details:
  URL: stratum+tcp://192.168.1.100:3333
  Worker: radiant.YOUR_WORKER_NAME
  Password: (any value or leave blank)
```

#### 3. Configure ASIC Miner

**For Antminer (Web Interface):**
1. Navigate to Miner Configuration → Pool Settings
2. Pool URL: `stratum+tcp://YOUR_IP:3333`
3. Worker: `radiant.ASIC_01`
4. Password: Leave blank or use `x`
5. Save and restart miner

**For WhatsMiner:**
1. Pool URL: `stratum+tcp://YOUR_IP:3333`
2. Worker: `radiant.ASIC_01`
3. Password: (leave blank)

**For cgminer/sgminer:**
```bash
cgminer --url stratum+tcp://YOUR_IP:3333 \
        --user radiant.ASIC_01 \
        --pass x
```

### Manual Setup

#### 1. Start Node
```bash
./mining/start_mining_node.sh
```

#### 2. Start Proxy
```bash
cd mining
python3 stratum_proxy.py
```

#### 3. Configure ASIC
Use the connection details shown when starting the proxy.

### Verification
```bash
# Check proxy is running
netstat -an | grep 3333

# Check node status
./build/src/radiant-cli -testnet getmininginfo
```

### ASIC Performance

#### Native SHA-512/256d ASICs
| Model | Hash Rate | Power | Efficiency |
|-------|-----------|-------|-------------|
| DragonBall A11 | ~400 GH/s | ~3200W | 8 J/GH |
| Iceriver RX0 | ~250 GH/s | ~2100W | 8.4 J/GH |

#### SHA-256 ASICs (Compatible)
| Model | Hash Rate | Power | Efficiency |
|-------|-----------|-------|-------------|
| Antminer S19 Pro | 110 TH/s | 3250W | 35 J/TH |
| WhatsMiner M50 | 126 TH/s | 3400W | 27 J/TH |
| Antminer S9 | 13 TH/s | 1350W | 104 J/TH |

**Note**: Native SHA-512/256d ASICs provide optimal performance. SHA-256 ASICs are compatible but may have reduced efficiency due to algorithm differences.

### Mining Pool vs Solo Mining

#### Solo Mining (Recommended)
- **Direct to node**: Configure ASIC to connect directly to your Radiant node
- **Full rewards**: Keep 100% of block rewards + fees
- **No pool fees**: No pool operator takes a cut
- **Privacy**: Blocks mined directly to your node

#### Mining Pool (Future)
- **Steady payouts**: More consistent earnings
- **Lower variance**: Regular payments vs occasional blocks
- **Pool fees**: Typically 1-3% fee
- **Note**: Radiant mining pools are not yet widely available

### Troubleshooting ASIC Mining

#### Connection Issues
```bash
# Check if node is accepting connections
netstat -an | grep 27333

# Verify RPC is enabled
./build/src/radiant-cli -testnet getinfo
```

#### Common Problems
- **"Connection refused"**: Ensure `-server` flag is set and port is open
- **"Authorization failed"**: Check RPC credentials match
- **"High difficulty"**: ASICs handle difficulty automatically
- **"No shares accepted"**: Verify stratum protocol compatibility

#### Optimize for ASICs
```bash
# Start node with optimal settings for ASICs
./build/src/radiantd -testnet \
    -nodeprofile=mining \
    -server \
    -rpcuser=testnet \
    -rpcpassword=testnetpass123 \
    -maxconnections=50 \
    -rpcallowip=0.0.0.0/0
```

### Security Considerations

1. **Firewall**: Only open necessary ports (27333/8332)
2. **RPC Access**: Use strong RPC passwords
3. **Network**: Consider VPN for remote ASIC connections
4. **Monitoring**: Monitor for unauthorized connections

### Hybrid Mining

Combine ASIC and GPU mining for maximum efficiency:
- **ASICs**: Primary mining power (solo to your node)
- **GPU**: Backup mining when ASICs are offline
- **CPU**: Fallback for testing/development

## Troubleshooting

### GPU Issues
```bash
# Check OpenCL support
./check_gpu.sh

# Reset GPU driver
./reset_gpu.sh
```

### Common Problems
- **"PyOpenCL not found"**: Run `./install.sh`
- **"No GPU devices"**: Check OpenCL drivers
- **"RPC connection failed"**: Verify radiantd is running

## Advanced

### Mining Pool Support
```bash
# Configure pool mining
./setup_pool.sh POOL_URL WORKER_NAME
```

### Custom Kernels
```bash
# Compile optimized kernels
./compile_kernels.sh
```

## Support

- Issues: Check `logs/` directory
- Performance: Use `benchmark.sh`
- Community: Radiant Discord

## License

MIT License - See LICENSE file
