# Radiant Mining Setup Guide

## Prerequisites

1. **Radiant Node Built and Ready**
   ```bash
   # Build Radiant Core if not already done
   cd /path/to/radiant-core
   mkdir -p build && cd build
   cmake .. && make -j$(nproc)
   ```

2. **Python 3.8+** (3.11+ recommended for GPU mining)

## Initial Configuration

### 1. Set RPC Credentials

**IMPORTANT**: Never use default credentials. Set strong, unique credentials:

```bash
# Generate strong credentials
export RPC_USER="your_unique_username"
export RPC_PASS="$(openssl rand -base64 32)"

# Save to your shell profile for persistence
echo "export RPC_USER=\"your_unique_username\"" >> ~/.bashrc
echo "export RPC_PASS=\"your_secure_password\"" >> ~/.bashrc
source ~/.bashrc
```

### 2. Create Mining Wallet

Before mining, create a wallet to receive rewards:

```bash
# For testnet
./build/src/radiant-cli -testnet createwallet "miner"

# For mainnet
./build/src/radiant-cli createwallet "miner"
```

Verify wallet creation:
```bash
./build/src/radiant-cli -testnet -rpcwallet=miner getwalletinfo
```

### 3. Install Mining Dependencies

```bash
cd mining
./install.sh
```

This will:
- Install Python dependencies (numpy, pyopencl)
- Generate random RPC credentials (secure)
- Create config file: `~/.radiant_mining/config.json`
- Create matching `~/.radiant/radiant.conf` for node

**View generated credentials:**
```bash
cat ~/.radiant_mining/config.json
```

**Security Note**: Random credentials are generated automatically. Keep these files secure and backed up.

## Mining Methods

### GPU Mining (Recommended - 50-100x faster)

**Requirements:**
- OpenCL-compatible GPU (Apple Silicon, NVIDIA, AMD)
- PyOpenCL installed

**Start mining:**
```bash
# Set credentials
export RPC_USER="your_username"
export RPC_PASS="your_password"

# Start node
./mining/start_mining_node.sh

# Start GPU miner
./mining/start_gpu_miner.sh
```

**Optional: Adjust batch size for your GPU:**
```bash
export BATCH_SIZE=8388608  # 2^23 for powerful GPUs
./mining/start_gpu_miner.sh
```

### CPU Mining (Fallback)

```bash
# Set credentials
export RPC_USER="your_username"
export RPC_PASS="your_password"

# Start node
./mining/start_mining_node.sh

# Start CPU miner
./mining/start_cpu_miner.sh
```

### ASIC Mining

**Step 1: Start Radiant node with mining profile**
```bash
export RPC_USER="your_username"
export RPC_PASS="your_password"
./mining/start_mining_node.sh
```

**Step 2: Configure Worker Allowlist (IMPORTANT)**
```bash
# For security, configure allowed worker names
export ALLOWED_WORKERS=worker1,worker2,worker3
```

**Step 3: Start Stratum Proxy**
```bash
export RPC_USER="your_username"
export RPC_PASS="your_password"
export RPC_WALLET="miner"  # Your wallet name
./mining/start_stratum_proxy.sh
```

**Stratum Security Options:**
```bash
export MAX_SHARES_PER_MINUTE="600"   # Rate limit per client (default: 600)
export MAX_AUTH_FAILURES="5"         # Ban after N failed auths (default: 5)
export AUTH_FAILURE_BAN_TIME="300"   # Ban duration in seconds (default: 300)
```

**Step 4: Configure your ASIC**

The proxy will display connection details:
```
ASIC Connection Details:
  URL: stratum+tcp://YOUR_IP:3333
  Worker: YOUR_WORKER_NAME
  Password: (any value)
```

Configure your ASIC miner:
- **URL**: `stratum+tcp://YOUR_IP:3333`
- **Worker**: `worker1` (must be in ALLOWED_WORKERS)
- **Password**: `x` (or leave blank)

**IMPORTANT**: Worker name MUST match one in your ALLOWED_WORKERS list.

## Network Configuration

### Testnet (Default)
```bash
export NETWORK="testnet"
export RPC_PORT="27332"
```

### Mainnet
```bash
export NETWORK="mainnet"
export RPC_PORT="8332"
```

## Security Best Practices

### 1. Credential Management

✅ **DO:**
- Use strong, unique RPC credentials
- Store credentials in environment variables
- Use different credentials for testnet and mainnet
- Rotate credentials periodically

❌ **DON'T:**
- Use default credentials
- Hardcode credentials in scripts
- Share credentials between systems
- Use weak passwords

### 2. Network Security

For **local mining** (same machine - RECOMMENDED):
```bash
# Node listens on localhost only (secure)
./build/src/radiantd -testnet -server \
  -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS \
  -rpcbind=127.0.0.1 \
  -rpcallowip=127.0.0.1
```

**Note**: ASICs connect via Stratum proxy (port 3333), NOT directly to RPC.

For **LAN ASIC mining** (local network):
```bash
# RPC still on localhost, Stratum proxy handles ASIC connections
./build/src/radiantd -testnet -server \
  -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS \
  -rpcbind=127.0.0.1 \
  -rpcallowip=127.0.0.1

# Start Stratum proxy to accept connections from LAN
# Proxy binds to 0.0.0.0:3333 by default
./mining/start_stratum_proxy.sh
```

For **remote access** (not recommended without VPN):
```bash
# Use firewall and strong credentials
# Consider TLS/VPN for production
./build/src/radiantd -testnet -server \
  -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS \
  -rpcallowip=SPECIFIC_IP/32
```

### 3. Firewall Configuration

```bash
# Allow only necessary ports
# RPC: 27332 (testnet) or 8332 (mainnet) - localhost only
# Stratum: 3333 (for ASIC mining) - LAN if needed
# P2P: 17333 (testnet) or 7333 (mainnet)

# Example: ufw
# RPC should NOT be exposed - bind to localhost only
# Only open Stratum port for ASIC miners
sudo ufw allow from 192.168.1.0/24 to any port 3333  # Stratum (LAN only)
sudo ufw allow 17333/tcp  # P2P
```

### 4. Worker Allowlist (Stratum Proxy)

```bash
# Configure allowed worker names for production
export ALLOWED_WORKERS=asic1,asic2,gpu_rig1

# Miners not in this list will be rejected
# Leave empty only for testing (security risk)
```

### 5. Stratum Proxy Security

For production ASIC mining:

```bash
# Required: Set allowed workers
export ALLOWED_WORKERS="worker1,worker2,worker3"

# Optional: Adjust rate limiting
export MAX_SHARES_PER_MINUTE="600"  # Per-client limit
export MAX_AUTH_FAILURES="5"        # Ban threshold
export AUTH_FAILURE_BAN_TIME="300"  # 5 minute ban
```

**Security Features:**
- **Worker Allowlist**: Only listed workers can connect
- **Rate Limiting**: Prevents share flooding (600/min default)
- **Auth Failure Bans**: Temporary IP bans after failed auths
- **Hex Validation**: All parameters validated before processing
## Troubleshooting

### "RPC connection failed"
- Ensure node is running: `ps aux | grep radiantd`
- Check RPC credentials are set: `echo $RPC_USER $RPC_PASS`
- Verify port: `netstat -an | grep 27332`

### "Wallet not found"
- Create wallet: `./build/src/radiant-cli -testnet createwallet "miner"`
- List wallets: `./build/src/radiant-cli -testnet listwallets`

### "PyOpenCL not found"
- Install: `pip install pyopencl numpy`
- Verify: `python3 -c "import pyopencl"`
- Fallback to CPU mining if GPU not available

### Low hash rate
- **GPU Mining**: Adjust BATCH_SIZE environment variable
- **CPU Mining**: Expected (~700K H/s), GPU is 50-100x faster
- **ASIC Mining**: Check stratum proxy connection on port 3333

### Stratum proxy issues
- **"Worker not authorized"**: Add worker to ALLOWED_WORKERS
- **"Connection refused"**: Check proxy is running on port 3333
- **"Temporarily banned"**: Too many auth failures, wait 5 minutes

### Graceful shutdown
- **CPU/GPU Miners**: Press Ctrl+C to exit cleanly
- **Stratum Proxy**: Press Ctrl+C to stop accepting connections
- **Node**: Use `radiant-cli stop` command

### Permission denied
```bash
# Make scripts executable
chmod +x mining/*.sh
```

## Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `RPC_USER` | RPC username | - | ✅ Yes* |
| `RPC_PASS` | RPC password | - | ✅ Yes* |
| `RPC_PORT` | RPC port | 27332 (testnet) | No |
| `RPC_HOST` | RPC host | 127.0.0.1 | No |
| `RPC_WALLET` | Wallet name for rewards | miner | No |
| `NETWORK` | Network (testnet/mainnet/regtest) | testnet | No |
| `BATCH_SIZE` | GPU batch size (max 16777216) | 4194304 | No |
| `STRATUM_PORT` | Stratum proxy port | 3333 | No |
| `DIFFICULTY` | Initial stratum difficulty | 0.001 | No |
| `ALLOWED_WORKERS` | Comma-separated worker names | (empty) | Recommended |
| `PROJECT_DIR` | Path to radiant-core | Auto-detected | No |
| `CONFIG_FILE` | Path to config.json | ~/.radiant_mining/config.json | No |
| `MAX_SHARES_PER_MINUTE` | Rate limit per client | 600 | No |
| `MAX_AUTH_FAILURES` | Auth failures before ban | 5 | No |
| `AUTH_FAILURE_BAN_TIME` | Ban duration (seconds) | 300 | No |

*Can be set via config file `~/.radiant_mining/config.json` instead
## New Features (2024 Audit)

### Graceful Shutdown
- Press **Ctrl+C** to exit cleanly
- Miners handle SIGINT and SIGTERM signals
- Proper cleanup of resources

### Config File Support
- Auto-generated: `~/.radiant_mining/config.json`
- Random credentials created by install.sh
- Environment variables override config values
- Fallback chain: ENV → Config → Error

### Security Improvements
- **No credential exposure**: RPC credentials passed via stdin
- **Random credentials**: Generated automatically by install.sh
- **Rate limiting**: Built-in auth failure tracking
- **Worker allowlist**: ALLOWED_WORKERS for Stratum proxy
- **Localhost binding**: RPC bound to 127.0.0.1 by default

### Code Quality
- **mining_utils.py**: Shared utility module (no duplication)
- **Memory leak fixes**: Proper cleanup of old jobs
- **Race condition fixes**: Job cache locking
- **Better error handling**: Detailed error messages

## Support

For issues or questions:
1. Check logs: `tail -f ~/.radiant_testnet/debug.log`
2. Check config: `cat ~/.radiant_mining/config.json`
3. Review this guide and `FIXES.md`
4. Visit Radiant Discord/Community channels
5. Check GitHub issues

## Monitoring

### Check Mining Status
```bash
# Node info
./build/src/radiant-cli -testnet -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS getmininginfo

# Blockchain info
./build/src/radiant-cli -testnet -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS getblockchaininfo

# Wallet balance
./build/src/radiant-cli -testnet -rpcwallet=miner -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS getbalance
```

### Log Files
- Node logs: `~/.radiant_testnet/debug.log`
- Mining output: Check terminal where miner is running

## Example: Complete Setup (Testnet)

```bash
# 1. Set credentials
export RPC_USER="miner_testnet"
export RPC_PASS="$(openssl rand -base64 32)"

# 2. Create wallet
./build/src/radiant-cli -testnet createwallet "miner"

# 3. Start node
./mining/start_mining_node.sh

# 4. Wait for sync (check with)
./build/src/radiant-cli -testnet -rpcuser=$RPC_USER -rpcpassword=$RPC_PASS getblockcount

# 5. Start mining (GPU preferred)
./mining/start_gpu_miner.sh

# Or auto-detect best miner
./mining/start_mining.sh
```

## Config File Reference

Location: `~/.radiant_mining/config.json`

```json
{
  "network": "testnet",
  "rpc": {
    "user": "your_username",
    "pass": "your_password",
    "port": 27332,
    "timeout": 30
  },
  "gpu": {
    "enabled": true,
    "batch_size": 4194304
  }
}
```

Environment variables always override config file values.
