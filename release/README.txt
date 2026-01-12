Radiant Core Release Notes
==========================

These are release artifacts for Radiant Core v2.0.0.

Windows Support:
---------------
Native Windows builds are deprecated. Please use WSL2 (Windows Subsystem for Linux) to run Radiant Core on Windows.

Quick Start with WSL2:
--------------------
1. Install WSL2 with Ubuntu:
   wsl --install -d Ubuntu-22.04

2. In WSL2, download and extract the Linux release:
   wget https://github.com/Radiant-Core/Radiant-Core/releases/download/v2.0.0/radiant-core-linux-x86_64.tar.gz
   tar -xzf radiant-core-linux-x86_64.tar.gz

3. Run the daemon:
   ./radiantd

4. Check daemon status:
   ./radiant-cli getblockchaininfo

Linux/macOS Users:
-----------------
Download the appropriate release from GitHub Releases and follow the standard Unix instructions.

System Requirements:
-------------------
- Windows 10/11 (64-bit) with WSL2
- Ubuntu 22.04 in WSL2
- Or: Linux x86_64, macOS Universal

Build Information:
-----------------
- Version: v2.0.0-7cfb963
- Cross-platform builds available

For more information, visit: https://radiantblockchain.org
