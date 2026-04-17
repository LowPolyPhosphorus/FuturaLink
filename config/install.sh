#!/bin/bash
sudo cp config/futuralink.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable futuralink
sudo systemctl start futuralink
echo "FuturaLink service installed and started"