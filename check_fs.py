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

triggers: {"trigger1": {"threshold": 95, "reset": 80, "level": "warning", "message": "directory: '{1}', user: '{0}', disk:  {3}% of {2}, inodes: {7}% of {5}"}}

dir_parse = re.compile(
    r"(?P<username>\S+)\s+(?P<directory>\S+)\s+(?P<available>(\d|\.)*\D?)\s+(?P<used>(\d|\.)*\D?)\s+(?P<used_percent>(\d|\.)*)%?\s+(?P<inodes>\S+)\s+(?P<inodes_used>\S+)\s+(?P<inodes_used_percent>\S+)%\n"
)

sub_input = "squeue --clusters all --state pending,running -h --format=%u | sort -u | sed -re '/(CLUSTER|USER|\s).*/d' | while read line; do sed -r -e '/Filesystem.*/d' -e 's/^/'\"$line\\t\"'/g' /scale_wlg_persistent/filesets/opt_nesi/var/quota/users/$line; done"
log.debug(sub_input)
output = subprocess.check_output(sub_input, shell=True).decode("utf-8")
log.debug(output)
dir_dict = dir_parse.findall(output.strip())

for trigger_name, trigger_val in config["triggers"].items():
    # Load cache
    cache = readmake_json("cache/" + trigger_name + ".json", {})
    for directory in dir_dict:
        log.debug(
            "directory: '" + directory[1] + "', user: '" + directory[0] + "', disk: " + directory[3] + "% of " + directory[2] + ", inodes: " + directory[7] + "% of " + directory[5]
        )            
        in_cache = directory[1] in cache

        disk_percent = float(directory[3]) if directory[3] else 0
        inode_percent = float(directory[3]) if directory[7] else 0

        if disk_percent > trigger_val["threshold"] or inode_percent > trigger_val["threshold"]:
            log.info(trigger_name + " fired")
            # If not logged send message.
            if not in_cache:
                getattr(log, trigger_val["level"])(trigger_val["message"].format(directory))
            cache[directory[1]] = [directory[3], directory[7]]
        elif in_cache and float(directory[3]) < trigger_val["reset"] and float(directory[7]) < trigger_val["reset"]:
            log.debug(trigger_name + "  trigger reset")
            cache.pop(directory)

    # Update cache.        
    with open("cache/" + trigger_name + ".json", "w+") as json_file:
        json_file.write(json.dumps(cache))

log.info("Loop time " + str(time.time()-loop_start) + " ms")