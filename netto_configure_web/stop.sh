#!/bin/sh

PROCESS_PATH=/data/service/netto_scheduler/netto_configure_web
PIDPROC=`ps -ef | grep "${PROCESS_PATH}" | grep -v 'grep'| awk '{print $2}'`
if [ -z "$PIDPROC" ];then
 echo "$PROCESS_PATH is not running"
 exit 0
fi

echo "PIDPROC: "$PIDPROC
for PID in $PIDPROC
do
if kill -9 $PID
   then echo "process $PROCESS_PATH (Pid:$PID) was force stopped at " `date`
fi
done
