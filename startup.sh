#!/usr/bin/env sh
set -eu

LOCAL_PATH="${LOCAL_PATH:-/usr/src/app/local_data}"
mkdir -p "$LOCAL_PATH"

exec python -m mcp_server.server
