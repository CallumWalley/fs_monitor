#!/bin/bash

. ~/.bashrc > /dev/null 
cd /nesi/project/nesi99999/Callum/fs_monitor
module load Python/3.8.2-gimkl-2020a
export STARTMSG="FALSE"
python check_fs.py

