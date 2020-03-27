#!/bin/bash

. ~/.bashrc > /dev/null 
cd ~/fs_monitor
module load Python/3.8.2-gimkl-2020a
python check_fs.py > /dev/null

