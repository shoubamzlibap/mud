#!/bin/bash
# setup.sh

# install dependencies
sudo yum install numpy scipy python-matplotlib ffmpeg portaudio-devel gcc mariadb-server
sudo pip install --allow-external PyAudio --allow-unverified PyAudio PyAudio
sudo pip install pydub 
sudo pip install PyDejavu
sudo mysql_secure_installation
sudo systemctl enable mariadb
sudo systemctl start mariadb
# setup database


