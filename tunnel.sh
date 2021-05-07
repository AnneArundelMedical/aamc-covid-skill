#!/bin/sh

TUNNEL_LISTEN_PORT="60501"
TUNNEL_LISTEN_HOST=localhost
TUNNEL_REDIRECT_PORT=8222
TUNNEL_SETUP="$TUNNEL_LISTEN_PORT:$TUNNEL_LISTEN_HOST:$TUNNEL_REDIRECT_PORT"
TUNNEL_REMOTE_USER=aamcmycroft
TUNNEL_REMOTE_HOST=192.168.1.165
TUNNEL_REMOTE_PORT=60105
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
  TUNNEL_REMOTE="$TUNNEL_REMOTE_USER@$TUNNEL_REMOTE_HOST"
  nohup ssh -N -R "$TUNNEL_SETUP" -p "$TUNNEL_REMOTE_PORT" "$TUNNEL_REMOTE" 2>&1 >/dev/null &
  echo $! > "$PID_FILENAME"
fi

