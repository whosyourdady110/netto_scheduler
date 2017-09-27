#!/bin/sh
userPyPath=/data/service/netto_scheduler
export PYTHONPATH=${PYTHONPATH}:$userPyPath
#nohup python3 $userPyPath/netto_scheduler_agent/scripts/main.py >web.log \
#"$@" &
python3 $userPyPath/netto_scheduler_agent/scripts/main.py
