#!/bin/bash

# Radiant Auto Miner Starter
# Automatically detects and starts the best available miner

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Radiant Auto Miner Starter ===${NC}"
echo

# Default settings
NETWORK="testnet"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MINER_DIR="$(dirname "${BASH_SOURCE[0]}")"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --mainnet)
            NETWORK="mainnet"
            shift
            ;;
        --gpu-only)
            GPU_ONLY=true
            shift
            ;;
        --cpu-only)
            CPU_ONLY=true
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --mainnet      Use mainnet instead of testnet"
            echo "  --gpu-only     Only try GPU mining"
            echo "  --cpu-only     Only try CPU mining"
            echo "  --help         Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${YELLOW}Detecting mining capabilities...${NC}"

# Auto-detect Python
PYTHON=$(command -v python3.11 2>/dev/null || command -v python3 2>/dev/null || echo "python3")
echo -e "${BLUE}Python: $PYTHON${NC}"

# Check GPU capabilities
GPU_AVAILABLE=false
if [ "$CPU_ONLY" != true ]; then
    echo -n "Checking GPU support... "
    if $PYTHON -c "import pyopencl; print('OK')" 2>/dev/null; then
        GPU_AVAILABLE=true
        echo -e "${GREEN}✓ Available${NC}"
    else
        echo -e "${YELLOW}✗ PyOpenCL not available${NC}"
    fi
fi

# Check CPU capabilities
CPU_AVAILABLE=true
if [ "$GPU_ONLY" != true ]; then
    echo -n "Checking CPU support... "
    if $PYTHON -c "print('OK')" 2>/dev/null; then
        echo -e "${GREEN}✓ Available${NC}"
    else
        CPU_AVAILABLE=false
        echo -e "${RED}✗ Python not available${NC}"
    fi
fi

echo

# Choose miner
if [ "$GPU_AVAILABLE" = true ] && [ "$CPU_ONLY" != true ]; then
    echo -e "${GREEN}Starting GPU miner (recommended)...${NC}"
    exec "$MINER_DIR/start_gpu_miner.sh" "$@"
elif [ "$CPU_AVAILABLE" = true ]; then
    echo -e "${YELLOW}Starting CPU miner (fallback)...${NC}"
    exec "$MINER_DIR/start_cpu_miner.sh" "$@"
else
    echo -e "${RED}Error: No mining capabilities available${NC}"
    echo
    echo "To enable GPU mining:"
    echo "  pip install pyopencl numpy"
    echo
    echo "To enable CPU mining:"
    echo "  Install Python 3.11+"
    exit 1
fi
