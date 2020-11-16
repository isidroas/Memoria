#!/bin/python3
import glob
import shutil
import os

contents= glob.glob("../../quadrotor_simulator/*")

contents_filter = [] 

for con in contents:
    if 'images' not in con and not '.git' in con:
        contents_filter.append(con)


for con in contents_filter:
    os.system("cp -R " + con + " quadrotor_simulator")
