#!/bin/bash

cd ~/Work
source sys_venv/bin/activate
cd /home/cnc/linuxcnc/configs/sim.axis/
/home/cnc/Work/linuxcnc-dev2/scripts/linuxcnc weiler_lathe.ini


