#!/usr/bin/env python3
"""
Radiant Core Node - Simple browser-based interface for running a Radiant node
Designed for non-technical users to easily start and manage their node.
Uses only Python standard library - no external dependencies required.
"""

import http.server
import json
import os
import platform
import subprocess
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import socketserver
import signal
import sys

# Global state
node_process = None
node_output = []
MAX_LOG_LINES = 500

class NodeManager:
    def __init__(self):
        self.base_path = Path(__file__).parent.parent
        self.config_file = self.base_path / "gui" / "node_settings.json"
        self.settings = self._load_settings()
        self.process = None
        self.output_lines = []
        self.is_running = False
        self.log_thread = None
        self._check_initial_state()
        
    def _get_default_datadir(self):
        system = platform.system()
        if system == "Darwin":
            return str(Path.home() / "Library" / "Application Support" / "Radiant")
        elif system == "Windows":
            return str(Path(os.environ.get("APPDATA", "")) / "Radiant")
        else:
            return str(Path.home() / ".radiant")
    
    def _load_settings(self):
        default = {
            "datadir": self._get_default_datadir(),
            "network": "mainnet",
            "prune": False,
            "prune_size": 550,
            "auto_start": True,
        }
        try:
            if self.config_file.exists():
                with open(self.config_file) as f:
                    default.update(json.load(f))
        except Exception:
            pass
        return default
    
    def _save_settings(self):
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception:
            pass
    
    def _check_initial_state(self):
        """Check if node is already running on GUI startup."""
        self._log("Checking for running node...")
        if self._is_node_running_externally():
            self._log("Connected to existing Radiant node")
            # Get initial info
            cli = self._find_binary("radiant-cli")
            if cli:
                try:
                    result = subprocess.run([cli, "getblockchaininfo"], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        info = json.loads(result.stdout)
                        self._log(f"Network: {info.get('chain', 'unknown')}")
                        self._log(f"Block height: {info.get('blocks', 0):,}")
                        self._log(f"Sync progress: {info.get('verificationprogress', 0) * 100:.1f}%")
                except Exception:
                    pass
        else:
            binary = self._find_binary("radiantd")
            if binary:
                self._log(f"Found radiantd: {binary}")
                self._log("Ready to start node")
            else:
                self._log("Warning: radiantd binary not found")
                self._log("Please build the project or install binaries")
    
    def _find_binary(self, name):
        if platform.system() == "Windows":
            name += ".exe"
        paths = [
            self.base_path / "build" / "src" / name,
            self.base_path / "src" / name,
            self.base_path / name,
            # Release binaries
            self.base_path / "releases" / "Mac - Apple Silicon" / "radiant-core-macos-arm64" / name,
            self.base_path / "releases" / "Mac - Intel" / "radiant-core-macos-x64" / name,
            self.base_path / "releases" / "Linux" / "radiant-core-linux-x64" / name,
            self.base_path / "releases" / "Windows" / "radiant-core-windows-x64" / name,
            Path("/usr/local/bin") / name,
            Path("/usr/bin") / name,
        ]
        for p in paths:
            if p.exists():
                return str(p)
        return None
    
    def _run_cli(self, *args, timeout=10):
        """Run a radiant-cli command and return the result."""
        cli = self._find_binary("radiant-cli")
        if not cli:
            return None, "CLI not found"
        try:
            result = subprocess.run([cli] + list(args), capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0:
                return result.stdout.strip(), None
            return None, result.stderr.strip() or f"Command failed with code {result.returncode}"
        except subprocess.TimeoutExpired:
            return None, "Command timed out"
        except Exception as e:
            return None, str(e)
    
    def _is_node_running_externally(self):
        """Check if a node is already running (started outside GUI) via RPC."""
        cli = self._find_binary("radiant-cli")
        if not cli:
            return False
        try:
            result = subprocess.run([cli, "getblockchaininfo"], capture_output=True, text=True, timeout=3)
            return result.returncode == 0
        except Exception:
            return False
    
    def get_status(self):
        # Check if node is running externally (not started by GUI)
        external_running = self._is_node_running_externally()
        actually_running = self.is_running or external_running
        
        info = {
            "running": actually_running,
            "started_by_gui": self.is_running,
            "settings": self.settings,
            "logs": self.output_lines[-100:],
            "binary_found": self._find_binary("radiantd") is not None,
        }
        
        if actually_running:
            cli = self._find_binary("radiant-cli")
            if cli:
                try:
                    result = subprocess.run(
                        [cli, "getblockchaininfo"],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        bc_info = json.loads(result.stdout)
                        info["blocks"] = bc_info.get("blocks", 0)
                        info["progress"] = bc_info.get("verificationprogress", 0) * 100
                        info["chain"] = bc_info.get("chain", "unknown")
                except Exception:
                    pass
                
                try:
                    result = subprocess.run(
                        [cli, "getconnectioncount"],
                        capture_output=True, text=True, timeout=5
                    )
                    if result.returncode == 0:
                        info["peers"] = int(result.stdout.strip())
                except Exception:
                    pass
        
        return info
    
    def _log(self, msg):
        timestamp = time.strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        self.output_lines.append(line)
        if len(self.output_lines) > MAX_LOG_LINES:
            self.output_lines = self.output_lines[-MAX_LOG_LINES:]
    
    def _read_output(self):
        try:
            while self.process and self.process.poll() is None:
                line = self.process.stdout.readline()
                if line:
                    self._log(line.strip())
        except Exception:
            pass
        
        if self.process:
            self._log("Node process ended")
            self.is_running = False
    
    def start(self, settings=None):
        if self.is_running:
            return {"success": False, "error": "Node already running (started by GUI)"}
        
        # Check if node is already running externally
        if self._is_node_running_externally():
            self._log("Detected existing node running - connecting to it")
            return {"success": True, "message": "Connected to existing node"}
        
        binary = self._find_binary("radiantd")
        if not binary:
            return {"success": False, "error": "radiantd binary not found. Please build the project first."}
        
        if settings:
            self.settings.update(settings)
            self._save_settings()
        
        cmd = [binary]
        
        datadir = self.settings.get("datadir")
        if datadir:
            cmd.append(f"-datadir={datadir}")
            Path(datadir).mkdir(parents=True, exist_ok=True)
        
        network = self.settings.get("network", "mainnet")
        if network == "testnet":
            cmd.append("-testnet")
        elif network == "regtest":
            cmd.append("-regtest")
        
        if self.settings.get("prune"):
            size = self.settings.get("prune_size", 550)
            cmd.append(f"-prune={size}")
        
        cmd.extend(["-daemon=0", "-printtoconsole", "-server=1", "-disablewallet=0"])
        
        self._log(f"Starting: {' '.join(cmd)}")
        
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            self.is_running = True
            self._log("Node started successfully")
            
            self.log_thread = threading.Thread(target=self._read_output, daemon=True)
            self.log_thread.start()
            
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def stop(self):
        if not self.is_running:
            return {"success": False, "error": "Node not running"}
        
        self._log("Stopping node...")
        
        cli = self._find_binary("radiant-cli")
        if cli:
            try:
                subprocess.run([cli, "stop"], capture_output=True, timeout=10)
            except Exception:
                pass
        
        if self.process:
            try:
                self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self._log("Force terminating...")
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill()
        
        self.process = None
        self.is_running = False
        self._log("Node stopped")
        return {"success": True}
    
    def get_info(self):
        cli = self._find_binary("radiant-cli")
        if not cli:
            return {"error": "CLI not found"}
        
        info = {}
        commands = ["getblockchaininfo", "getnetworkinfo", "getpeerinfo"]
        for cmd in commands:
            try:
                result = subprocess.run([cli, cmd], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    info[cmd] = json.loads(result.stdout)
            except Exception as e:
                info[cmd] = {"error": str(e)}
        return info
    
    def _is_node_available(self):
        """Check if node is available (started by GUI or running externally)."""
        return self.is_running or self._is_node_running_externally()
    
    def _is_wallet_supported(self):
        """Check if node was compiled with wallet support."""
        result, err = self._run_cli("help", "getbalance")
        if err and "Method not found" in err:
            return False
        return True
    
    # Wallet functions
    def get_wallet_info(self):
        if not self._is_node_available():
            return {"error": "Node not running"}
        
        # Check if wallet is supported
        if not self._is_wallet_supported():
            return {
                "error": "Wallet not available",
                "wallet_disabled": True,
                "message": "Node was compiled without wallet support. Rebuild with -DBUILD_RADIANT_WALLET=ON"
            }
        
        result = {}
        
        # Get balance
        balance, err = self._run_cli("getbalance")
        if balance is not None:
            try:
                result["balance"] = float(balance)
            except:
                result["balance"] = 0
        else:
            result["balance"] = 0
            result["balance_error"] = err
        
        # Get unconfirmed balance
        unconf, _ = self._run_cli("getunconfirmedbalance")
        if unconf is not None:
            try:
                result["unconfirmed"] = float(unconf)
            except:
                result["unconfirmed"] = 0
        else:
            result["unconfirmed"] = 0
        
        # Get wallet info
        winfo, _ = self._run_cli("getwalletinfo")
        if winfo:
            try:
                result["wallet_info"] = json.loads(winfo)
            except:
                pass
        
        return result
    
    def get_new_address(self, label=""):
        if not self._is_node_available():
            return {"error": "Node not running"}
        
        args = ["getnewaddress"]
        if label:
            args.append(label)
        
        address, err = self._run_cli(*args)
        if address:
            return {"success": True, "address": address}
        return {"success": False, "error": err or "Failed to generate address"}
    
    def get_addresses(self):
        if not self._is_node_available():
            return {"error": "Node not running"}
        
        # Get receiving addresses
        result, err = self._run_cli("listreceivedbyaddress", "0", "true")
        if result:
            try:
                addresses = json.loads(result)
                return {"success": True, "addresses": addresses}
            except:
                pass
        
        return {"success": False, "error": err or "Failed to list addresses", "addresses": []}
    
    def send_rxd(self, address, amount):
        if not self._is_node_available():
            return {"error": "Node not running"}
        
        if not address:
            return {"success": False, "error": "Address is required"}
        
        try:
            amount = float(amount)
            if amount <= 0:
                return {"success": False, "error": "Amount must be positive"}
        except:
            return {"success": False, "error": "Invalid amount"}
        
        # Validate address
        valid, _ = self._run_cli("validateaddress", address)
        if valid:
            try:
                vdata = json.loads(valid)
                if not vdata.get("isvalid"):
                    return {"success": False, "error": "Invalid RXD address"}
            except:
                pass
        
        # Send transaction
        txid, err = self._run_cli("sendtoaddress", address, str(amount))
        if txid:
            self._log(f"Sent {amount} RXD to {address[:16]}... - TXID: {txid[:16]}...")
            return {"success": True, "txid": txid}
        
        return {"success": False, "error": err or "Transaction failed"}
    
    def get_transactions(self, count=20):
        if not self._is_node_available():
            return {"error": "Node not running"}
        
        result, err = self._run_cli("listtransactions", "*", str(count))
        if result:
            try:
                txs = json.loads(result)
                return {"success": True, "transactions": txs}
            except:
                pass
        
        return {"success": False, "error": err or "Failed to list transactions", "transactions": []}


# Global node manager
manager = NodeManager()

HTML_PAGE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Radiant Core Node</title>
    <style>
        :root {
            --bg-primary: #0f0f14;
            --bg-secondary: #1a1a24;
            --bg-tertiary: #252532;
            --text-primary: #f0f0f5;
            --text-secondary: #a0a0b0;
            --text-muted: #606070;
            --border-color: #2a2a3a;
            --accent: #00d9ff;
            --accent-green: #00e88a;
            --accent-red: #ff5a6a;
            --accent-orange: #ffaa00;
        }
        [data-theme="light"] {
            --bg-primary: #f5f7fa;
            --bg-secondary: #ffffff;
            --bg-tertiary: #e8edf2;
            --text-primary: #1a1a2e;
            --text-secondary: #4a4a5a;
            --text-muted: #8a8a9a;
            --border-color: #d0d5dd;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            background: var(--bg-primary);
            min-height: 100vh;
            color: var(--text-primary);
            padding: 20px;
            transition: background 0.3s, color 0.3s;
        }
        .container { max-width: 900px; margin: 0 auto; }
        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 20px 0;
            border-bottom: 1px solid var(--border-color);
            margin-bottom: 20px;
        }
        .header-left { display: flex; align-items: center; gap: 12px; }
        .logo { width: 40px; height: 40px; }
        .logo-dark { display: block; }
        .logo-light { display: none; }
        [data-theme="light"] .logo-dark { display: none; }
        [data-theme="light"] .logo-light { display: block; }
        h1 {
            font-size: 24px;
            color: var(--text-primary);
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .header-right { display: flex; align-items: center; gap: 12px; }
        .theme-toggle {
            background: var(--bg-tertiary);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 8px 12px;
            cursor: pointer;
            color: var(--text-secondary);
            font-size: 16px;
        }
        .theme-toggle:hover { background: var(--border-color); }
        .status {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 13px;
            padding: 8px 14px;
            background: var(--bg-secondary);
            border: 1px solid var(--border-color);
            border-radius: 20px;
        }
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: var(--text-muted);
            transition: background 0.3s;
        }
        .status-dot.running { background: var(--accent-green); box-shadow: 0 0 8px var(--accent-green); }
        .status-dot.starting { background: var(--accent-orange); animation: pulse 1s infinite; }
        @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
        
        .tabs {
            display: flex;
            gap: 4px;
            margin-bottom: 20px;
            background: var(--bg-secondary);
            padding: 4px;
            border-radius: 10px;
            border: 1px solid var(--border-color);
        }
        .tab {
            flex: 1;
            padding: 10px 24px;
            background: transparent;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            border-radius: 8px;
            transition: all 0.2s;
        }
        .tab:hover { color: var(--text-primary); background: var(--bg-tertiary); }
        .tab.active {
            color: #fff;
            background: var(--accent);
        }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        button {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            transition: all 0.2s;
        }
        .btn-start {
            background: linear-gradient(135deg, var(--accent), var(--accent-green));
            color: #0a0a0f;
        }
        .btn-start:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(0,217,255,0.4); }
        .btn-start:disabled { background: var(--bg-tertiary); color: var(--text-muted); cursor: not-allowed; transform: none; box-shadow: none; }
        .btn-stop { background: var(--accent-red); color: white; }
        .btn-stop:hover { opacity: 0.9; }
        .btn-stop:disabled { background: var(--bg-tertiary); color: var(--text-muted); cursor: not-allowed; }
        .btn-secondary { background: var(--bg-tertiary); color: var(--text-primary); border: 1px solid var(--border-color); }
        .btn-secondary:hover { background: var(--border-color); }
        .btn-send { background: linear-gradient(135deg, #ff6b6b, #ff8e53); color: white; }
        .btn-send:hover { transform: translateY(-2px); box-shadow: 0 4px 15px rgba(255,107,107,0.4); }
        .btn-receive { background: linear-gradient(135deg, var(--accent), var(--accent-green)); color: #0a0a0f; }
        .btn-small { padding: 8px 16px; font-size: 12px; }
        
        .panel {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
            border: 1px solid var(--border-color);
        }
        .panel h2 {
            font-size: 13px;
            margin-bottom: 15px;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
        }
        .stat {
            text-align: center;
            padding: 15px;
            background: var(--bg-tertiary);
            border-radius: 8px;
        }
        .stat-value {
            font-size: 24px;
            font-weight: bold;
            color: var(--accent);
        }
        .stat-value.balance { color: var(--accent-green); }
        .stat-label { font-size: 12px; color: var(--text-muted); margin-top: 5px; }
        
        .settings-grid {
            display: grid;
            gap: 15px;
        }
        .setting {
            display: flex;
            align-items: center;
            gap: 15px;
            flex-wrap: wrap;
        }
        .setting label { min-width: 100px; font-size: 14px; color: var(--text-secondary); }
        .setting input, .setting select {
            flex: 1;
            min-width: 150px;
            padding: 10px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: var(--bg-primary);
            color: var(--text-primary);
            font-size: 14px;
        }
        .setting input:focus, .setting select:focus {
            outline: none;
            border-color: var(--accent);
        }
        .setting input[type="checkbox"] {
            width: 20px;
            height: 20px;
            min-width: 20px;
            flex: none;
            accent-color: var(--accent);
        }
        .prune-size { width: 100px !important; min-width: 100px !important; flex: none !important; }
        
        .log-container {
            background: var(--bg-primary);
            border-radius: 8px;
            padding: 15px;
            height: 200px;
            overflow-y: auto;
            font-family: "Monaco", "Menlo", monospace;
            font-size: 12px;
            line-height: 1.6;
            border: 1px solid var(--border-color);
        }
        .log-line { color: var(--text-muted); }
        .log-line:last-child { color: var(--accent-green); }
        
        /* Wallet Styles */
        .wallet-balance {
            text-align: center;
            padding: 30px;
            background: linear-gradient(135deg, rgba(0,217,255,0.08), rgba(0,232,138,0.08));
            border-radius: 12px;
            margin-bottom: 20px;
            border: 1px solid var(--border-color);
        }
        .wallet-balance .amount {
            font-size: 42px;
            font-weight: bold;
            color: var(--accent-green);
        }
        .wallet-balance .currency { font-size: 20px; color: var(--text-muted); margin-left: 8px; }
        .wallet-balance .unconfirmed { font-size: 14px; color: var(--accent-orange); margin-top: 5px; }
        
        .wallet-actions {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 20px;
        }
        .wallet-action {
            padding: 20px;
            background: var(--bg-secondary);
            border-radius: 12px;
            text-align: center;
            border: 1px solid var(--border-color);
        }
        .wallet-action h3 { margin-bottom: 15px; color: var(--text-primary); }
        
        .address-box {
            background: var(--bg-primary);
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            font-size: 13px;
            word-break: break-all;
            margin: 10px 0;
            color: var(--accent);
            cursor: pointer;
            transition: all 0.2s;
            border: 1px solid var(--border-color);
        }
        .address-box:hover { border-color: var(--accent); }
        .address-box.copied { background: rgba(0,232,138,0.15); border-color: var(--accent-green); }
        
        .form-group {
            margin-bottom: 15px;
            text-align: left;
        }
        .form-group label {
            display: block;
            margin-bottom: 5px;
            color: var(--text-secondary);
            font-size: 13px;
        }
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: var(--bg-primary);
            color: var(--text-primary);
            font-size: 14px;
        }
        .form-group input:focus { outline: none; border-color: var(--accent); }
        
        .tx-list {
            max-height: 300px;
            overflow-y: auto;
        }
        .tx-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 12px;
            border-bottom: 1px solid var(--border-color);
        }
        .tx-item:last-child { border-bottom: none; }
        .tx-amount { font-weight: bold; }
        .tx-amount.positive { color: var(--accent-green); }
        .tx-amount.negative { color: var(--accent-red); }
        .tx-info { font-size: 12px; color: var(--text-muted); }
        .tx-confirmations { font-size: 11px; padding: 2px 6px; background: var(--bg-tertiary); border-radius: 4px; color: var(--text-secondary); }
        
        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.7);
            justify-content: center;
            align-items: center;
            z-index: 1000;
            backdrop-filter: blur(4px);
        }
        .modal.show { display: flex; }
        .modal-content {
            background: var(--bg-secondary);
            border-radius: 12px;
            padding: 25px;
            max-width: 700px;
            max-height: 80vh;
            overflow-y: auto;
            width: 90%;
            border: 1px solid var(--border-color);
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }
        .modal-close {
            background: var(--bg-tertiary);
            border: none;
            color: var(--text-secondary);
            font-size: 20px;
            cursor: pointer;
            width: 32px;
            height: 32px;
            border-radius: 6px;
        }
        .modal-close:hover { background: var(--border-color); }
        pre {
            background: var(--bg-primary);
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            font-size: 11px;
            line-height: 1.5;
            border: 1px solid var(--border-color);
        }
        
        .alert {
            padding: 12px 15px;
            border-radius: 8px;
            margin-bottom: 15px;
            font-size: 14px;
        }
        .alert-success { background: rgba(0,232,138,0.2); color: var(--accent-green); }
        .alert-error { background: rgba(255,90,106,0.2); color: var(--accent-red); }
        .alert-warning { background: rgba(255,170,0,0.2); color: var(--accent-orange); }
        
        footer {
            text-align: center;
            padding: 20px;
            color: var(--text-muted);
            font-size: 12px;
        }
        footer a { color: var(--accent); text-decoration: none; }
        footer a:hover { text-decoration: underline; }
        
        .disabled-overlay {
            position: relative;
        }
        .disabled-overlay::after {
            content: "Start node to use wallet";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: var(--bg-primary);
            opacity: 0.92;
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--text-muted);
            font-size: 16px;
            border-radius: 12px;
        }
    </style>
</head>
<body data-theme="dark">
    <div class="container">
        <header>
            <div class="header-left">
                <img class="logo logo-dark" src="/logo-light.svg" alt="Radiant Logo">
                <img class="logo logo-light" src="/logo-dark.svg" alt="Radiant Logo">
                <h1>Radiant Core Node</h1>
            </div>
            <div class="header-right">
                <button class="theme-toggle" onclick="toggleTheme()" title="Toggle theme">🌙</button>
                <div class="status">
                    <div class="status-dot" id="statusDot"></div>
                    <span id="statusText">Checking...</span>
                </div>
            </div>
        </header>
        
        <div class="tabs">
            <button class="tab active" onclick="switchTab('node')">Node</button>
            <button class="tab" onclick="switchTab('wallet')">Wallet</button>
        </div>
        
        <!-- NODE TAB -->
        <div id="nodeTab" class="tab-content active">
            <div class="controls">
                <button class="btn-start" id="startBtn" onclick="startNode()">▶ Start Node</button>
                <button class="btn-stop" id="stopBtn" onclick="stopNode()" disabled>■ Stop Node</button>
                <button class="btn-secondary" onclick="showInfo()">ℹ Node Info</button>
            </div>
            
            <div class="panel" id="statsPanel" style="display:none;">
                <h2>Node Status</h2>
                <div class="stats">
                    <div class="stat">
                        <div class="stat-value" id="blockHeight">-</div>
                        <div class="stat-label">Block Height</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="syncProgress">-</div>
                        <div class="stat-label">Sync Progress</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="peerCount">-</div>
                        <div class="stat-label">Peers</div>
                    </div>
                    <div class="stat">
                        <div class="stat-value" id="networkName">-</div>
                        <div class="stat-label">Network</div>
                    </div>
                </div>
            </div>
            
            <div class="panel">
                <h2>Settings</h2>
                <div class="settings-grid">
                    <div class="setting">
                        <label>Network</label>
                        <select id="network">
                            <option value="mainnet">Mainnet</option>
                            <option value="testnet">Testnet</option>
                            <option value="regtest">Regtest</option>
                        </select>
                    </div>
                    <div class="setting">
                        <label>Data Dir</label>
                        <input type="text" id="datadir" placeholder="Blockchain data directory">
                    </div>
                    <div class="setting">
                        <label>Auto-start</label>
                        <input type="checkbox" id="autoStart" checked>
                        <span style="color:#888;">Start node when app opens</span>
                    </div>
                    <div class="setting">
                        <label>Pruning</label>
                        <input type="checkbox" id="prune" onchange="togglePrune()">
                        <span style="color:#888;">Enable (saves disk space)</span>
                        <input type="number" id="pruneSize" class="prune-size" value="550" min="550" disabled>
                        <span style="color:#888;">MB</span>
                    </div>
                </div>
            </div>
            
            <div class="panel">
                <h2>Log Output</h2>
                <div class="log-container" id="logOutput">
                    <div class="log-line">Initializing...</div>
                </div>
            </div>
        </div>
        
        <!-- WALLET TAB -->
        <div id="walletTab" class="tab-content">
            <div id="walletContent">
                <div class="wallet-balance">
                    <div><span class="amount" id="walletBalance">0.00</span><span class="currency">RXD</span></div>
                    <div class="unconfirmed" id="unconfirmedBalance"></div>
                </div>
                
                <div class="wallet-actions">
                    <div class="wallet-action">
                        <h3>Receive RXD</h3>
                        <p style="font-size:13px;color:#888;margin-bottom:15px;">Share this address to receive RXD</p>
                        <div class="address-box" id="receiveAddress" onclick="copyAddress()" title="Click to copy">
                            Generate a new address
                        </div>
                        <button class="btn-receive btn-small" onclick="generateAddress()">New Address</button>
                    </div>
                    <div class="wallet-action">
                        <h3>Send RXD</h3>
                        <div class="form-group">
                            <label>Recipient Address</label>
                            <input type="text" id="sendAddress" placeholder="Enter RXD address">
                        </div>
                        <div class="form-group">
                            <label>Amount (RXD)</label>
                            <input type="number" id="sendAmount" placeholder="0.00" step="0.00000001" min="0">
                        </div>
                        <button class="btn-send" onclick="sendRXD()">Send RXD</button>
                    </div>
                </div>
                
                <div class="panel">
                    <h2>Recent Transactions</h2>
                    <div class="tx-list" id="txList">
                        <div style="text-align:center;color:#888;padding:20px;">Loading transactions...</div>
                    </div>
                </div>
            </div>
        </div>
        
        <footer>
            Need help? Visit <a href="https://radiantblockchain.org" target="_blank">radiantblockchain.org</a>
        </footer>
    </div>
    
    <div class="modal" id="infoModal">
        <div class="modal-content">
            <div class="modal-header">
                <h2>Node Information</h2>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <pre id="infoContent">Loading...</pre>
        </div>
    </div>
    
    <script>
        let refreshInterval;
        let walletInterval;
        let nodeRunning = false;
        let settingsLoaded = false;
        let autoStartTriggered = false;
        
        // Theme toggle functionality
        function toggleTheme() {
            const body = document.body;
            const btn = document.querySelector('.theme-toggle');
            if (body.getAttribute('data-theme') === 'dark') {
                body.setAttribute('data-theme', 'light');
                btn.textContent = '☀️';
                localStorage.setItem('theme', 'light');
            } else {
                body.setAttribute('data-theme', 'dark');
                btn.textContent = '🌙';
                localStorage.setItem('theme', 'dark');
            }
        }
        
        // Load saved theme on page load
        (function() {
            const savedTheme = localStorage.getItem('theme') || 'dark';
            document.body.setAttribute('data-theme', savedTheme);
            const btn = document.querySelector('.theme-toggle');
            if (btn) btn.textContent = savedTheme === 'dark' ? '🌙' : '☀️';
        })();
        
        function switchTab(tab) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            document.querySelector(`.tab[onclick="switchTab('${tab}')"]`).classList.add('active');
            document.getElementById(tab + 'Tab').classList.add('active');
            
            if (tab === 'wallet' && nodeRunning) {
                updateWallet();
            }
        }
        
        function updateStatus() {
            fetch('/api/status')
                .then(r => r.json())
                .then(data => {
                    const dot = document.getElementById('statusDot');
                    const text = document.getElementById('statusText');
                    const startBtn = document.getElementById('startBtn');
                    const stopBtn = document.getElementById('stopBtn');
                    const statsPanel = document.getElementById('statsPanel');
                    const walletContent = document.getElementById('walletContent');
                    
                    nodeRunning = data.running;
                    
                    if (data.running) {
                        dot.className = 'status-dot running';
                        text.textContent = 'Running';
                        startBtn.disabled = true;
                        stopBtn.disabled = false;
                        statsPanel.style.display = 'block';
                        walletContent.classList.remove('disabled-overlay');
                        
                        document.getElementById('blockHeight').textContent = 
                            data.blocks ? data.blocks.toLocaleString() : '-';
                        document.getElementById('syncProgress').textContent = 
                            data.progress ? data.progress.toFixed(1) + '%' : '-';
                        document.getElementById('peerCount').textContent = 
                            data.peers !== undefined ? data.peers : '-';
                        document.getElementById('networkName').textContent = 
                            data.chain || '-';
                    } else {
                        dot.className = 'status-dot';
                        text.textContent = 'Not Running';
                        startBtn.disabled = !data.binary_found;
                        stopBtn.disabled = true;
                        statsPanel.style.display = 'none';
                        walletContent.classList.add('disabled-overlay');
                    }
                    
                    if (!data.binary_found) {
                        text.textContent = 'Binary Not Found';
                    }
                    
                    // Update settings (only first time)
                    if (data.settings && !settingsLoaded) {
                        settingsLoaded = true;
                        document.getElementById('network').value = data.settings.network || 'mainnet';
                        document.getElementById('datadir').value = data.settings.datadir || '';
                        document.getElementById('autoStart').checked = data.settings.auto_start !== false;
                        document.getElementById('prune').checked = data.settings.prune || false;
                        document.getElementById('pruneSize').value = data.settings.prune_size || 550;
                        document.getElementById('pruneSize').disabled = !data.settings.prune;
                        
                        // Auto-start if enabled and binary found
                        if (data.settings.auto_start !== false && data.binary_found && !data.running && !autoStartTriggered) {
                            autoStartTriggered = true;
                            setTimeout(() => startNode(), 500);
                        }
                    }
                    
                    // Update logs
                    if (data.logs && data.logs.length) {
                        const logDiv = document.getElementById('logOutput');
                        logDiv.innerHTML = data.logs.map(l => 
                            '<div class="log-line">' + escapeHtml(l) + '</div>'
                        ).join('');
                        logDiv.scrollTop = logDiv.scrollHeight;
                    }
                });
        }
        
        function updateWallet() {
            if (!nodeRunning) return;
            
            fetch('/api/wallet/info')
                .then(r => r.json())
                .then(data => {
                    if (data.wallet_disabled) {
                        document.getElementById('walletBalance').textContent = 'N/A';
                        document.getElementById('unconfirmedBalance').innerHTML = 
                            '<span style="color:var(--accent-orange);">Wallet not available - node compiled without wallet support.<br>Rebuild with: cmake -DBUILD_RADIANT_WALLET=ON ..</span>';
                        document.getElementById('walletContent').classList.add('wallet-disabled');
                        return;
                    }
                    document.getElementById('walletContent').classList.remove('wallet-disabled');
                    if (data.balance !== undefined) {
                        document.getElementById('walletBalance').textContent = 
                            data.balance.toFixed(8);
                    }
                    if (data.unconfirmed > 0) {
                        document.getElementById('unconfirmedBalance').textContent = 
                            '+' + data.unconfirmed.toFixed(8) + ' RXD unconfirmed';
                    } else {
                        document.getElementById('unconfirmedBalance').textContent = '';
                    }
                });
            
            fetch('/api/wallet/transactions')
                .then(r => r.json())
                .then(data => {
                    const txList = document.getElementById('txList');
                    if (data.transactions && data.transactions.length) {
                        txList.innerHTML = data.transactions.slice().reverse().map(tx => {
                            const isReceive = tx.category === 'receive';
                            const amount = tx.amount || 0;
                            const conf = tx.confirmations || 0;
                            const time = tx.time ? new Date(tx.time * 1000).toLocaleString() : '';
                            return `<div class="tx-item">
                                <div>
                                    <div class="tx-amount ${isReceive ? 'positive' : 'negative'}">
                                        ${isReceive ? '+' : ''}${amount.toFixed(8)} RXD
                                    </div>
                                    <div class="tx-info">${time}</div>
                                </div>
                                <div class="tx-confirmations">${conf} conf</div>
                            </div>`;
                        }).join('');
                    } else {
                        txList.innerHTML = '<div style="text-align:center;color:#888;padding:20px;">No transactions yet</div>';
                    }
                });
        }
        
        function generateAddress() {
            fetch('/api/wallet/newaddress', { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    if (data.success) {
                        document.getElementById('receiveAddress').textContent = data.address;
                    } else {
                        alert('Error: ' + (data.error || 'Failed to generate address'));
                    }
                });
        }
        
        function copyAddress() {
            const addr = document.getElementById('receiveAddress').textContent;
            if (addr && addr !== 'Generate a new address') {
                navigator.clipboard.writeText(addr);
                const box = document.getElementById('receiveAddress');
                box.classList.add('copied');
                setTimeout(() => box.classList.remove('copied'), 1000);
            }
        }
        
        function sendRXD() {
            const address = document.getElementById('sendAddress').value.trim();
            const amount = document.getElementById('sendAmount').value;
            
            if (!address) {
                alert('Please enter a recipient address');
                return;
            }
            if (!amount || parseFloat(amount) <= 0) {
                alert('Please enter a valid amount');
                return;
            }
            
            if (!confirm(`Send ${amount} RXD to ${address}?`)) return;
            
            fetch('/api/wallet/send', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ address, amount })
            })
            .then(r => r.json())
            .then(data => {
                if (data.success) {
                    alert('Transaction sent!\\nTXID: ' + data.txid);
                    document.getElementById('sendAddress').value = '';
                    document.getElementById('sendAmount').value = '';
                    updateWallet();
                } else {
                    alert('Error: ' + (data.error || 'Transaction failed'));
                }
            });
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function getSettings() {
            return {
                network: document.getElementById('network').value,
                datadir: document.getElementById('datadir').value,
                auto_start: document.getElementById('autoStart').checked,
                prune: document.getElementById('prune').checked,
                prune_size: parseInt(document.getElementById('pruneSize').value) || 550
            };
        }
        
        function startNode() {
            document.getElementById('startBtn').disabled = true;
            document.getElementById('statusDot').className = 'status-dot starting';
            document.getElementById('statusText').textContent = 'Starting...';
            
            fetch('/api/start', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(getSettings())
            })
            .then(r => r.json())
            .then(data => {
                if (!data.success) {
                    alert('Error: ' + data.error);
                }
                updateStatus();
            });
        }
        
        function stopNode() {
            document.getElementById('stopBtn').disabled = true;
            document.getElementById('statusText').textContent = 'Stopping...';
            
            fetch('/api/stop', {method: 'POST'})
                .then(r => r.json())
                .then(data => {
                    if (!data.success) {
                        alert('Error: ' + data.error);
                    }
                    updateStatus();
                });
        }
        
        function showInfo() {
            document.getElementById('infoModal').classList.add('show');
            document.getElementById('infoContent').textContent = 'Loading...';
            
            fetch('/api/info')
                .then(r => r.json())
                .then(data => {
                    document.getElementById('infoContent').textContent = 
                        JSON.stringify(data, null, 2);
                });
        }
        
        function closeModal() {
            document.getElementById('infoModal').classList.remove('show');
        }
        
        function togglePrune() {
            document.getElementById('pruneSize').disabled = 
                !document.getElementById('prune').checked;
        }
        
        // Initial load and start refresh
        updateStatus();
        refreshInterval = setInterval(updateStatus, 3000);
        walletInterval = setInterval(() => {
            if (nodeRunning && document.getElementById('walletTab').classList.contains('active')) {
                updateWallet();
            }
        }, 10000);
        
        // Close modal on escape
        document.addEventListener('keydown', e => {
            if (e.key === 'Escape') closeModal();
        });
    </script>
</body>
</html>
'''


class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Suppress log messages
    
    def do_GET(self):
        parsed = urlparse(self.path)
        
        if parsed.path == "/" or parsed.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())
        
        elif parsed.path == "/api/status":
            self.send_json(manager.get_status())
        
        elif parsed.path == "/api/info":
            self.send_json(manager.get_info())
        
        elif parsed.path == "/api/wallet/info":
            self.send_json(manager.get_wallet_info())
        
        elif parsed.path == "/api/wallet/transactions":
            self.send_json(manager.get_transactions())
        
        elif parsed.path == "/api/wallet/addresses":
            self.send_json(manager.get_addresses())
        
        elif parsed.path == "/logo-light.svg":
            self.serve_logo("RXD_light_logo.svg")
        
        elif parsed.path == "/logo-dark.svg":
            self.serve_logo("RXD_dark_logo.svg")
        
        else:
            self.send_error(404)
    
    def serve_logo(self, filename):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        logo_path = os.path.join(script_dir, "..", "doc", "images", filename)
        try:
            with open(logo_path, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Cache-Control", "max-age=86400")
            self.end_headers()
            self.wfile.write(content)
        except FileNotFoundError:
            self.send_error(404)
    
    def do_POST(self):
        parsed = urlparse(self.path)
        
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode() if content_length else "{}"
        
        try:
            data = json.loads(body) if body else {}
        except json.JSONDecodeError:
            data = {}
        
        if parsed.path == "/api/start":
            result = manager.start(data)
            self.send_json(result)
        
        elif parsed.path == "/api/stop":
            result = manager.stop()
            self.send_json(result)
        
        elif parsed.path == "/api/wallet/newaddress":
            label = data.get("label", "")
            result = manager.get_new_address(label)
            self.send_json(result)
        
        elif parsed.path == "/api/wallet/send":
            address = data.get("address", "")
            amount = data.get("amount", 0)
            result = manager.send_rxd(address, amount)
            self.send_json(result)
        
        else:
            self.send_error(404)
    
    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True


def main():
    port = 8765
    server = ThreadedHTTPServer(("127.0.0.1", port), RequestHandler)
    
    url = f"http://127.0.0.1:{port}"
    print(f"\n{'='*50}")
    print("  Radiant Core Node")
    print(f"{'='*50}")
    print(f"\n  Opening browser at: {url}")
    print(f"\n  Press Ctrl+C to quit\n")
    print(f"{'='*50}\n")
    
    # Open browser after a short delay
    def open_browser():
        time.sleep(0.5)
        webbrowser.open(url)
    
    threading.Thread(target=open_browser, daemon=True).start()
    
    def signal_handler(sig, frame):
        print("\nShutting down...")
        if manager.is_running:
            manager.stop()
        server.shutdown()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if manager.is_running:
            print("Stopping node...")
            manager.stop()
        server.server_close()


if __name__ == "__main__":
    main()
