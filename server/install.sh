TARGET_LIB=/usr/local/lib/humidoscope
TARGET_ETC=/usr/local/etc
CONFIG_TARGET=$TARGET_ETC/humidoscope.config
PYTHON=python3
SYSTEMD_SERVICE=humidoscope.service
SYSTEMD_UNIT=/etc/systemd/system/$SYSTEMD_SERVICE

set -e
if [ ! -d $TARGET_LIB ]; then
    mkdir -p $TARGET_LIB
fi

# Copy files to install locations
install -m 644 *.py requirements.txt $TARGET_LIB
install -m 400 config.json $CONFIG_TARGET

# Set up python
cd $TARGET_LIB
if [ ! -d venv ]; then
    $PYTHON -m venv venv
fi
./venv/bin/pip install -r requirements.txt

# Set up systemd
cat <<EOF > $SYSTEMD_UNIT
[Unit]
Description=Humidity Monitoring System

[Service]
WorkingDirectory=$TARGET_LIB
Environment="CONFIG_PATH=$CONFIG_TARGET"
ExecStart=$TARGET_LIB/venv/bin/python -u main.py

[Install]
WantedBy=multi-user.target
EOF
chmod 644 $SYSTEMD_UNIT
systemctl daemon-reload
systemctl start $SYSTEMD_SERVICE
systemctl enable $SYSTEMD_SERVICE

