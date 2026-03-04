#!/bin/bash
# Remote desktop to the GTYC server via Tailscale + VNC
# Opens an SSH tunnel then launches the macOS VNC viewer

# Kill any existing tunnel on port 5900
lsof -ti:5900 | xargs kill 2>/dev/null

# Start SSH tunnel in background
ssh -L 5900:localhost:5900 gtyc@100.94.1.31 -N -f

# Wait for tunnel to establish
sleep 1

# Open macOS VNC viewer
open vnc://localhost:5900
