#!/bin/sh
userPyPath=/data/service/netto_scheduler
export PYTHONPATH=${PYTHONPATH}:$userPyPath
#nohup python3 $userPyPath/netto_configure_web/main.py >web.log \
#"$@" &
python3 $userPyPath/netto_configure_web/main.py
