import os, slack, json, math, time, datetime
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from clog import log
import re
import subprocess


def readmake_json(path, default={}):
    """Reads and returns JSON file as dictionary, if none exists one will be created with default value."""
    if not os.path.exists(path):
        log.error("No file at path '" + path + "'.")
        with open(path, "w+") as json_file:
            json_file.write(json.dumps(default))
        log.error("Empty file created")

    with open(path) as json_file:
        log.debug(path + " loaded.")
        return json.load(json_file)


loop_start = time.time()

config = readmake_json("config.json", {"triggers": {}})
lazycache_username = readmake_json("cache/lazycache_username.json", {"username_fullname":{}})
dir_parse = re.compile(
    r"(?P<username>\S+)\s+(?P<directory>\S+)\s+(?P<available>((\d|\.)*[A-Z]|0)(?=\s*((\d|\.)*[A-Z]|0)))?\s+(?P<used>(\d|\.)*\D?)?\s+((?P<used_percent>(\d|\.)*)%)?\s+(?P<inodes>\S*)\s+(?P<inodes_used>\S+)\s+(?P<inodes_used_percent>\S+)%\n"
)

sub_input = "squeue --clusters all --state pending,running -h --format=%u | sort -u | sed -re '/(CLUSTER|USER|\s).*/d' | while read line; do sed -r -e '/Filesystem.*/d' -e 's/^/'\"$line\\t\"'/g' /scale_wlg_persistent/filesets/opt_nesi/var/quota/users/$line; done"
log.debug(sub_input)
output = subprocess.check_output(sub_input, shell=True).decode("utf-8")
log.debug(output)
dir_iterator = dir_parse.finditer(output.strip())
# Load cache
for trigger_name, trigger_val in config["triggers"].items():
    trigger_val["cache"] = readmake_json("cache/" + trigger_name + ".json", {})

for directory in dir_iterator:
    dir_dict = directory.groupdict("0")

    if dir_dict["username"] in lazycache_username:
        dir_dict["fullname"]=lazycache_username[dir_dict["username"]]
    else:
        log.debug(dir_dict["username"] + " not in cache. Running ipa show-user" )
        #Try get fullname.
        try:
            sub_input = "ipa user-show " + dir_dict["username"] + " | sed -n -e 's/^.*First name: //p' -e 's/^.*Last name: //p' | tr '\n' ' '"
            dir_dict["fullname"] = subprocess.check_output(sub_input, shell=True).decode("utf-8")
            lazycache_username[dir_dict["username"]]=dir_dict["fullname"]
        except Exception as stuffYouFlake:
            pass
        else:
            dir_dict["fullname"] = "Unknown :sunglasses:"

    # Print whole dict 2 debug.
    log.debug(' '.join('{}:{}'.format(key, val) for key, val in dir_dict.items()))

    disk_percent = float(dir_dict["used_percent"]) if dir_dict["used_percent"] else 0
    inode_percent = float(dir_dict["used_percent"]) if dir_dict["used_percent"] else 0

    for trigger_name, trigger_val in config["triggers"].items():
        in_cache = dir_dict["directory"] in trigger_val["cache"]

        if disk_percent > trigger_val["threshold"] or inode_percent > trigger_val["threshold"]:
            log.info(trigger_name + " fired")
            # If not logged send message.
            if not in_cache:
                getattr(log, trigger_val["level"])(trigger_val["message"].format(**dir_dict))
            trigger_val["cache"][dir_dict["directory"]] = [disk_percent, inode_percent]
        elif in_cache and disk_percent < trigger_val["reset"] and inode_percent < trigger_val["reset"]:
            log.debug(trigger_name + "  trigger reset")
            trigger_val["cache"].pop(dir_dict["directory"])

           
# Update cache.    
for trigger_name, trigger_val in config["triggers"].items():
    with open("cache/" + trigger_name + ".json", "w+") as json_file:
        json_file.write(json.dumps(trigger_val["cache"]))
with open("cache/lazycache_username.json", "w+") as json_file:
    json_file.write(json.dumps(lazycache_username))
log.info("Loop time " + str(time.time()-loop_start) + " ms")