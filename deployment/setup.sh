#!/bin/bash
# Setup script for data collection on EC2 instance (Amazon Linux 2)

set -e

echo "Updating system packages..."
sudo yum update -y

echo "Installing Python 3 and pip..."
sudo yum install -y python3 python3-pip

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing Python requirements..."
cd "$SCRIPT_DIR"
pip3 install -r requirements.txt

echo "Setting system timezone to Europe/Stockholm..."
sudo timedatectl set-timezone Europe/Stockholm

echo "Setting up cron job to run every 2 minutes..."
CRON_JOB="*/2 * * * * cd $SCRIPT_DIR && /usr/bin/python3 sl_departures.py >> $SCRIPT_DIR/cron.log 2>&1"

# Add the cron job if it doesn't already exist
(crontab -l 2>/dev/null | grep -F "sl_departures.py" > /dev/null) && echo "Cron job already exists" || (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

echo "Setup complete!"
