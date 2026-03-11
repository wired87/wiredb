#!/bin/bash

# Paths
JOURNALD_CONF_FILE="/etc/systemd/journald.conf"
LOCAL_CONF_SOURCE="/home/derbenedikt_sterra/betse_drf/gunicorn/cfg/journald.conf"    # <-- your local config file
CUSTOM_LOG_DIR="/home/derbenedikt_sterra/betse_drf/gunicorn/logs"

# 1. Backup existing config
sudo cp "$JOURNALD_CONF_FILE" "${JOURNALD_CONF_FILE}.bak"

# 2. Overwrite with local config
sudo cp "$LOCAL_CONF_SOURCE" "$JOURNALD_CONF_FILE"

# 3. Create custom log directory
sudo mkdir -p "$CUSTOM_LOG_DIR"

# 4. Move old logs if any
if [ -d "/var/log/journal" ]; then
    sudo mv /var/log/journal/* "$CUSTOM_LOG_DIR/" 2>/dev/null || true
    sudo rm -r /var/log/journal
fi

# 5. Symlink new log directory
sudo ln -s "$CUSTOM_LOG_DIR" /var/log/journal

# 6. Set correct permissions
sudo chown -R root:systemd-journal "$CUSTOM_LOG_DIR"
sudo chmod 2755 "$CUSTOM_LOG_DIR"

# 7. Restart journald
sudo systemctl restart systemd-journald

echo "✅ Journald reconfigured and restarted successfully."
# RUN
#chmod +x setup_journald.sh
#./setup_journald.sh