#!/bin/bash
# setup.sh

# install dependencies
install_dependencies(){
    # enable Fusion repos if not already done
    yum repolist |grep Fusion >/dev/null || sudo yum localinstall \
        --nogpgcheck http://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm \
        http://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
    sudo yum install numpy scipy python-matplotlib ffmpeg portaudio-devel gcc mariadb-server python-eyed3 python-pip
    sudo pip install --allow-external PyAudio --allow-unverified PyAudio PyAudio
    sudo pip install pydub 
    sudo pip install PyDejavu
    # configure mariadb
    sudo sed -i '/\[mysqld\]/a  innodb_file_per_table = 1' /etc/my.cnf.d/server.cnf
    sudo systemctl start mariadb
    sudo mysql_secure_installation
    sudo systemctl enable mariadb
}

# create settings.py file with the db credentials
create_settings(){
    user_name=$1
    user_pw=$2
    db_name=$3
    cat >>settings.py<<EOF
# settings.py
# settins file for mud

# dejavu db settings
dejavu_config = {
     'database': {
         'host': '127.0.0.1',
         'user': '${user_name}',
         'passwd': '${user_pw}', 
         'db': '${db_name}',
     },
    'fingerprint_limit' : 30,
 }

# base directory for music files
music_base_dir = '/tmp'

EOF
    
}

# setup database
# assuming local database
setup_database(){
    echo "Warning: if someone else is logged in to this system right now, it might be"
    echo "able to read the MariaDB root password from the process list"
    echo
    read -ers -p "Please enter MariaDB root password:" rootpw
    echo
    db_name="dejavu"
    mysql -u root --password=${rootpw} -e "CREATE DATABASE IF NOT EXISTS ${db_name};"
    user_name="dejavu-admin"
    user_pw=$(openssl rand -base64 23)
    mysql -u root --password=${rootpw} -e "grant all on dejavu.* to '${user_name}'@'localhost' identified by '${user_pw}';"
    create_settings ${user_name} ${user_pw} ${db_name}
    
}

print_help(){
    cat <<EOF
Setup everything needed to use mud.

usage: setup.sh [--help] [--install|--setup]

If no options are given, setup.sh will install dependencies and do 
the database setup.

Optins:

    --help      Print this message and exit.
    --install   Install dependencies
    --setup     Do the database setup

EOF
}

case $1 in
    --install) install_dependencies ;;
    --setup) setup_database ;;
    --help) print_help ; exit 0 ;;
    *)
        install_dependencies
        setup_database ;;
esac
