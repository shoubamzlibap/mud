#!/bin/bash

settings="../settings.py"
user=$(awk '/user/ {print $2}' ${settings} |sed "s/[,']//g")
pass=$(awk '/passwd/ {print $2}' ${settings} |sed "s/[,']//g")

mysql -u ${user} --password=${pass} dejavu
