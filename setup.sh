#!/bin/bash
# setup.sh

settings=settings.py

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

# create settings file with the db credentials
create_settings_head(){
    if [ -e ${settings} ]; then
        mv ${settings} ${settings}.$$
    fi
    cat >>${settings}<<EOF
# ${settings}
# settins file for mud

# base directory for music files
music_base_dir = '/tmp'

# localtion and name of the log file
log_file = 'mud.log'

# dejavu db settings
dejavu_configs = [
EOF
}

create_settings_db(){
    user_name=$1
    user_pw=$2
    db_name=$3
    fp_limit=$4
    cat >>${settings}<<EOF
    {   'database': {
            'host': '127.0.0.1',
            'user': '${user_name}',
            'passwd': '${user_pw}', 
            'db': '${db_name}',},
        'fingerprint_limit' : ${fp_limit}, },
EOF
}

create_settings_end(){
    cat >>${settings}<<EOF
]
EOF
}

# setup database
# assuming local database
setup_database(){
    # number of databases to create
    num_dbs=3
    # factor for initial fingerprint length config
    fp_factor=10 
    echo "Warning: if someone else is logged in to this system right now, it might be"
    echo "able to read the MariaDB root password from the process list"
    echo
    read -ers -p "Please enter MariaDB root password:" rootpw
    echo
    user_name="dejavu-admin"
    user_pw=$(openssl rand -base64 23)
    create_settings_head
    for i in $(seq ${num_dbs}); do
        db_name="dejavu_${i}"
        mysql -u root --password=${rootpw} -e "CREATE DATABASE IF NOT EXISTS ${db_name};"
        mysql -u root --password=${rootpw} -e "grant all on ${db_name}.* to '${user_name}'@'localhost' identified by '${user_pw}';"
        fp_length=$(( ${i} * ${fp_factor} ))
        create_settings_db ${user_name} ${user_pw} ${db_name} ${fp_length}
    done
    create_settings_end
}

print_help(){
    cat <<EOF
Setup everything needed to use mud.

usage: setup.sh [-h] [-i] [-s]

If no options are given, setup.sh will install dependencies and do 
the database setup.

Options:

    -h, --help      Print this message and exit.
    -i, --install   Install dependencies
    -s, --setup     Do the database setup

EOF
}

case $1 in
    "-i" | "--install") install_dependencies ;;
    "-s" | "--setup") setup_database ;;
    "-h" | "--help") print_help ; exit 0 ;;
    *)
        install_dependencies
        setup_database ;;
esac
