#!/usr/bin/env python3
"""
Radiant Node GUI - Simple windowed application for running a Radiant node
Designed for non-technical users to easily start and manage their node.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import subprocess
import threading
import os
import sys
import platform
import json
import time
from pathlib import Path


class RadiantNodeGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Radiant Node")
        self.root.geometry("700x550")
        self.root.minsize(600, 450)
        
        # Set app icon if available
        self._set_icon()
        
        # Node process reference
        self.node_process = None
        self.is_running = False
        self.log_thread = None
        self.stop_log_thread = False
        
        # Paths
        self.base_path = Path(__file__).parent.parent
        self.config_file = self.base_path / "gui" / "node_settings.json"
        self.default_datadir = self._get_default_datadir()
        
        # Load settings
        self.settings = self._load_settings()
        
        # Build UI
        self._create_ui()
        
        # Check node status on startup
        self.root.after(500, self._check_existing_node)
        
        # Handle window close
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _set_icon(self):
        """Set application icon if available."""
        try:
            icon_path = self.base_path / "share" / "pixmaps" / "bitcoin128.png"
            if icon_path.exists():
                icon = tk.PhotoImage(file=str(icon_path))
                self.root.iconphoto(True, icon)
        except Exception:
            pass
    
    def _get_default_datadir(self):
        """Get platform-specific default data directory."""
        system = platform.system()
        if system == "Darwin":
            return Path.home() / "Library" / "Application Support" / "Radiant"
        elif system == "Windows":
            return Path(os.environ.get("APPDATA", "")) / "Radiant"
        else:
            return Path.home() / ".radiant"
    
    def _get_node_binary(self):
        """Find the node binary path."""
        binary_name = "radiantd" if platform.system() != "Windows" else "radiantd.exe"
        
        # Check common locations
        search_paths = [
            self.base_path / "build" / "src" / binary_name,
            self.base_path / "src" / binary_name,
            self.base_path / binary_name,
            Path("/usr/local/bin") / binary_name,
            Path("/usr/bin") / binary_name,
        ]
        
        # Add custom path from settings
        if self.settings.get("binary_path"):
            search_paths.insert(0, Path(self.settings["binary_path"]))
        
        for path in search_paths:
            if path.exists():
                return str(path)
        
        return None
    
    def _get_cli_binary(self):
        """Find the CLI binary path."""
        binary_name = "radiant-cli" if platform.system() != "Windows" else "radiant-cli.exe"
        
        search_paths = [
            self.base_path / "build" / "src" / binary_name,
            self.base_path / "src" / binary_name,
            self.base_path / binary_name,
            Path("/usr/local/bin") / binary_name,
            Path("/usr/bin") / binary_name,
        ]
        
        if self.settings.get("cli_path"):
            search_paths.insert(0, Path(self.settings["cli_path"]))
        
        for path in search_paths:
            if path.exists():
                return str(path)
        
        return None
    
    def _load_settings(self):
        """Load settings from JSON file."""
        default_settings = {
            "datadir": str(self.default_datadir),
            "network": "mainnet",
            "prune": False,
            "prune_size": 550,
            "binary_path": "",
            "cli_path": "",
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    saved = json.load(f)
                    default_settings.update(saved)
        except Exception:
            pass
        
        return default_settings
    
    def _save_settings(self):
        """Save settings to JSON file."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            self._log(f"Warning: Could not save settings: {e}")
    
    def _create_ui(self):
        """Create the main user interface."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(
            header_frame, 
            text="Radiant Node", 
            font=("Helvetica", 18, "bold")
        )
        title_label.pack(side=tk.LEFT)
        
        # Status indicator
        self.status_frame = ttk.Frame(header_frame)
        self.status_frame.pack(side=tk.RIGHT)
        
        self.status_dot = tk.Canvas(self.status_frame, width=12, height=12, highlightthickness=0)
        self.status_dot.pack(side=tk.LEFT, padx=(0, 5))
        self._draw_status_dot("gray")
        
        self.status_label = ttk.Label(self.status_frame, text="Not Running")
        self.status_label.pack(side=tk.LEFT)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.start_btn = ttk.Button(
            button_frame, 
            text="▶ Start Node", 
            command=self._start_node,
            width=15
        )
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = ttk.Button(
            button_frame, 
            text="■ Stop Node", 
            command=self._stop_node,
            state=tk.DISABLED,
            width=15
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        self.info_btn = ttk.Button(
            button_frame, 
            text="ℹ Node Info", 
            command=self._show_node_info,
            width=15
        )
        self.info_btn.pack(side=tk.LEFT, padx=5)
        
        # Settings section
        settings_frame = ttk.LabelFrame(main_frame, text="Settings", padding="10")
        settings_frame.pack(fill=tk.X, pady=10)
        
        # Network selection
        network_frame = ttk.Frame(settings_frame)
        network_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(network_frame, text="Network:", width=12).pack(side=tk.LEFT)
        self.network_var = tk.StringVar(value=self.settings["network"])
        network_combo = ttk.Combobox(
            network_frame, 
            textvariable=self.network_var,
            values=["mainnet", "testnet", "regtest"],
            state="readonly",
            width=15
        )
        network_combo.pack(side=tk.LEFT)
        network_combo.bind("<<ComboboxSelected>>", self._on_network_change)
        
        # Data directory
        datadir_frame = ttk.Frame(settings_frame)
        datadir_frame.pack(fill=tk.X, pady=2)
        
        ttk.Label(datadir_frame, text="Data Dir:", width=12).pack(side=tk.LEFT)
        self.datadir_var = tk.StringVar(value=self.settings["datadir"])
        self.datadir_entry = ttk.Entry(datadir_frame, textvariable=self.datadir_var)
        self.datadir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        browse_btn = ttk.Button(
            datadir_frame, 
            text="Browse...", 
            command=self._browse_datadir,
            width=10
        )
        browse_btn.pack(side=tk.RIGHT)
        
        # Pruning option
        prune_frame = ttk.Frame(settings_frame)
        prune_frame.pack(fill=tk.X, pady=2)
        
        self.prune_var = tk.BooleanVar(value=self.settings["prune"])
        prune_check = ttk.Checkbutton(
            prune_frame, 
            text="Enable pruning (saves disk space)", 
            variable=self.prune_var,
            command=self._on_prune_change
        )
        prune_check.pack(side=tk.LEFT)
        
        ttk.Label(prune_frame, text="Size (MB):").pack(side=tk.LEFT, padx=(20, 5))
        self.prune_size_var = tk.StringVar(value=str(self.settings["prune_size"]))
        self.prune_entry = ttk.Entry(prune_frame, textvariable=self.prune_size_var, width=8)
        self.prune_entry.pack(side=tk.LEFT)
        self.prune_entry.config(state=tk.NORMAL if self.prune_var.get() else tk.DISABLED)
        
        # Log output
        log_frame = ttk.LabelFrame(main_frame, text="Log Output", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame, 
            height=12, 
            state=tk.DISABLED,
            font=("Courier", 10),
            wrap=tk.WORD
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Footer with helpful info
        footer_frame = ttk.Frame(main_frame)
        footer_frame.pack(fill=tk.X)
        
        self.sync_label = ttk.Label(footer_frame, text="", foreground="gray")
        self.sync_label.pack(side=tk.LEFT)
        
        help_label = ttk.Label(
            footer_frame, 
            text="Need help? Visit radiantblockchain.org",
            foreground="blue",
            cursor="hand2"
        )
        help_label.pack(side=tk.RIGHT)
        help_label.bind("<Button-1>", lambda e: self._open_url("https://radiantblockchain.org"))
    
    def _draw_status_dot(self, color):
        """Draw the status indicator dot."""
        self.status_dot.delete("all")
        self.status_dot.create_oval(2, 2, 10, 10, fill=color, outline=color)
    
    def _log(self, message):
        """Add a message to the log output."""
        self.log_text.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
    
    def _check_existing_node(self):
        """Check if a node is already running."""
        cli = self._get_cli_binary()
        if cli:
            try:
                result = subprocess.run(
                    [cli, "getblockchaininfo"],
                    capture_output=True,
                    timeout=5
                )
                if result.returncode == 0:
                    self._set_running_state(True, external=True)
                    self._log("Detected running node")
                    return
            except Exception:
                pass
        
        self._log("Ready to start node")
    
    def _set_running_state(self, running, external=False):
        """Update UI state based on whether node is running."""
        self.is_running = running
        
        if running:
            self._draw_status_dot("green")
            self.status_label.config(text="Running" + (" (external)" if external else ""))
            self.start_btn.config(state=tk.DISABLED)
            self.stop_btn.config(state=tk.NORMAL if not external else tk.DISABLED)
        else:
            self._draw_status_dot("gray")
            self.status_label.config(text="Not Running")
            self.start_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
    
    def _start_node(self):
        """Start the Radiant node."""
        binary = self._get_node_binary()
        
        if not binary:
            messagebox.showerror(
                "Error",
                "Could not find radiantd binary.\n\n"
                "Please build the project first or specify the binary path in settings."
            )
            return
        
        # Save current settings
        self.settings["datadir"] = self.datadir_var.get()
        self.settings["network"] = self.network_var.get()
        self.settings["prune"] = self.prune_var.get()
        try:
            self.settings["prune_size"] = int(self.prune_size_var.get())
        except ValueError:
            self.settings["prune_size"] = 550
        self._save_settings()
        
        # Build command
        cmd = [binary]
        
        # Data directory
        datadir = self.datadir_var.get()
        if datadir:
            cmd.append(f"-datadir={datadir}")
        
        # Network
        network = self.network_var.get()
        if network == "testnet":
            cmd.append("-testnet")
        elif network == "regtest":
            cmd.append("-regtest")
        
        # Pruning
        if self.prune_var.get():
            try:
                prune_size = int(self.prune_size_var.get())
                cmd.append(f"-prune={prune_size}")
            except ValueError:
                pass
        
        # Run as daemon
        cmd.append("-daemon=0")  # Don't daemonize so we can track the process
        cmd.append("-printtoconsole")
        
        self._log(f"Starting node: {' '.join(cmd)}")
        
        try:
            # Create data directory if it doesn't exist
            Path(datadir).mkdir(parents=True, exist_ok=True)
            
            # Start the process
            self.node_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            self._set_running_state(True)
            self._log("Node started successfully")
            
            # Start log reader thread
            self.stop_log_thread = False
            self.log_thread = threading.Thread(target=self._read_node_output, daemon=True)
            self.log_thread.start()
            
            # Start status monitor
            self._monitor_status()
            
        except Exception as e:
            self._log(f"Error starting node: {e}")
            messagebox.showerror("Error", f"Failed to start node:\n{e}")
    
    def _read_node_output(self):
        """Read and display node output in a separate thread."""
        try:
            while not self.stop_log_thread and self.node_process:
                line = self.node_process.stdout.readline()
                if not line:
                    if self.node_process.poll() is not None:
                        break
                    continue
                
                # Schedule log update on main thread
                self.root.after(0, lambda l=line.strip(): self._log(l))
        except Exception:
            pass
    
    def _monitor_status(self):
        """Periodically check node status and update sync progress."""
        if not self.is_running:
            return
        
        # Check if process is still running
        if self.node_process and self.node_process.poll() is not None:
            self._log("Node process ended")
            self._set_running_state(False)
            return
        
        # Try to get blockchain info
        cli = self._get_cli_binary()
        if cli:
            try:
                result = subprocess.run(
                    [cli, "getblockchaininfo"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    info = json.loads(result.stdout)
                    progress = info.get("verificationprogress", 0) * 100
                    blocks = info.get("blocks", 0)
                    self.sync_label.config(
                        text=f"Sync: {progress:.1f}% | Blocks: {blocks:,}"
                    )
            except Exception:
                pass
        
        # Check again in 5 seconds
        self.root.after(5000, self._monitor_status)
    
    def _stop_node(self):
        """Stop the running node."""
        if not self.is_running:
            return
        
        self._log("Stopping node...")
        
        # Try graceful shutdown via CLI first
        cli = self._get_cli_binary()
        if cli:
            try:
                subprocess.run([cli, "stop"], capture_output=True, timeout=10)
                self._log("Sent stop command")
            except Exception:
                pass
        
        # Wait for process to end
        if self.node_process:
            try:
                self.node_process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self._log("Force terminating...")
                self.node_process.terminate()
                try:
                    self.node_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.node_process.kill()
        
        self.stop_log_thread = True
        self.node_process = None
        self._set_running_state(False)
        self._log("Node stopped")
        self.sync_label.config(text="")
    
    def _show_node_info(self):
        """Show detailed node information."""
        cli = self._get_cli_binary()
        if not cli:
            messagebox.showinfo("Info", "CLI binary not found")
            return
        
        try:
            # Get various info
            info_text = "=== Node Information ===\n\n"
            
            commands = [
                ("Blockchain Info", "getblockchaininfo"),
                ("Network Info", "getnetworkinfo"),
                ("Peer Count", "getconnectioncount"),
            ]
            
            for name, cmd in commands:
                try:
                    result = subprocess.run(
                        [cli, cmd],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    if result.returncode == 0:
                        info_text += f"--- {name} ---\n{result.stdout}\n"
                except Exception as e:
                    info_text += f"--- {name} ---\nError: {e}\n"
            
            # Show in a new window
            info_window = tk.Toplevel(self.root)
            info_window.title("Node Information")
            info_window.geometry("600x500")
            
            text = scrolledtext.ScrolledText(info_window, wrap=tk.WORD)
            text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            text.insert(tk.END, info_text)
            text.config(state=tk.DISABLED)
            
        except Exception as e:
            messagebox.showerror("Error", f"Could not get node info:\n{e}")
    
    def _browse_datadir(self):
        """Open dialog to select data directory."""
        directory = filedialog.askdirectory(
            initialdir=self.datadir_var.get(),
            title="Select Data Directory"
        )
        if directory:
            self.datadir_var.set(directory)
            self.settings["datadir"] = directory
            self._save_settings()
    
    def _on_network_change(self, event=None):
        """Handle network selection change."""
        self.settings["network"] = self.network_var.get()
        self._save_settings()
    
    def _on_prune_change(self):
        """Handle prune checkbox change."""
        enabled = self.prune_var.get()
        self.prune_entry.config(state=tk.NORMAL if enabled else tk.DISABLED)
        self.settings["prune"] = enabled
        self._save_settings()
    
    def _open_url(self, url):
        """Open URL in default browser."""
        import webbrowser
        webbrowser.open(url)
    
    def _on_close(self):
        """Handle window close."""
        if self.is_running and self.node_process:
            if messagebox.askyesno(
                "Confirm Exit",
                "The node is still running. Stop it and exit?"
            ):
                self._stop_node()
            else:
                return
        
        self.root.destroy()


def main():
    """Main entry point."""
    root = tk.Tk()
    
    # Set theme
    try:
        if platform.system() == "Darwin":
            root.tk.call("::tk::unsupported::MacWindowStyle", "style", root._w, "document", "closeBox")
    except Exception:
        pass
    
    app = RadiantNodeGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
