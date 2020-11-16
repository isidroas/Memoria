#!/bin/python3
import glob
import shutil
import os

contents= glob.glob("../../rpi_vision_uav/*")

contents_filter = [] 

for con in contents:
    if 'build' not in con and 'videos' not in con and 'calibration' not in con and 'results' not in con and not '.git' in con:
        contents_filter.append(con)


for con in contents_filter:
    os.system("cp -R " + con + " rpi_vision_uav")
