#!/bin/sh

TUNNEL_SETUP="60501:localhost:22"
TUNNEL_REMOTE_HOST="192.168.1.165"
TUNNEL_REMOTE_PORT="60105"
PID_FILENAME="$HOME/sshtunnel.pid"

CMD="$1"

RUNNING=
PID=

if [ -f "$PID_FILENAME" ] ; then
  PID=$(cat "$PID_FILENAME")
  if ps -p "$PID" ; then
    RUNNING=YES
  fi
fi

if [ "$CMD" = "stop" ] ; then
  if [ "$RUNNING" = "YES" ] ; then
    kill "$PID"
  fi
  exit
fi

if [ -n "$CMD" ] ; then
  echo "Invalid command: $CMD" >&2
  exit 1
fi

if [ -z "$RUNNING" ] ; then
  nohup ssh -N -R $TUNNEL_SETUP aamcmycroft@192.168.1.165 2>&1 >/dev/null &
  echo $! > "$PID_FILENAME"
fi

