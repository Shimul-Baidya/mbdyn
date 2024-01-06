#!/bin/sh -f

OUTPUT_FORMAT=pid,comm,tty,state,cputime,vsize,uname,pcpu,pmem,tty

AWK_FILTER_CMD="/mbdyn|octave/{if(\$3==\"?\"&&\$4!=\"Z\"){print \$1};}"

ps -u $(whoami) -o ${OUTPUT_FORMAT} | awk "${AWK_FILTER_CMD}"

success="yes"

for pid in $(ps -u $(whoami) -o pid,comm,tty,state | awk "${AWK_FILTER_CMD}"); do
    ps -p ${pid} -o ${OUTPUT_FORMAT}
    if test "${MBD_FORCE_KILL}" = "yes"; then
        echo "Process ${pid} will be killed"
        if ! kill -9 ${pid}; then
            echo "Failed to kill ${pid}"
            success="no"
        fi
    else
        echo "Process ${pid} is still running: use MBD_FORCE_KILL=yes to kill this process!"
        success="no"
    fi
done

ps -u $(whoami) -o ${OUTPUT_FORMAT} | awk "${AWK_FILTER_CMD}"

if test "${MBD_FORCE_KILL}" = "yes" && ! test "${success}" = "yes"; then
    exit 1;
fi

if test "${MBD_FORCE_KILL}" = "no" && ! test "${success}" = "yes"; then
    exit 1;
fi
