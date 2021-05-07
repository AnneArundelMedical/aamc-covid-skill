#!/bin/sh

cd "$(cd "$(dirname -- "$0")" && pwd)"
TUNNEL_LISTEN_PORT_BASE="60500"
TUNNEL_LISTEN_HOST=localhost
TUNNEL_REDIRECT_PORT=8222
TUNNEL_REMOTE_USER=aamcmycroft
TUNNEL_REMOTE_HOST=192.168.1.165
TUNNEL_REMOTE_PORT=60105
PID_FILENAME="$HOME/sshtunnel.pid"

CMD="$1"

RUNNING=
PID=

MY_IP=$(hostname -I)
MY_LAST_OCTET=$(hostname -I | sed 's/^.*\.//')

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

if ! expr 0 + "$CMD" >/dev/null 2>&1 ; then
  echo "Invalid command: $CMD" >&2
  exit 1
fi

DEVICE_ID="$CMD"

# SSH args:
#  -N  Don't log in.
#  -R  Tunnel setup.
#  -p  Remote server's SSH port.

if [ -z "$RUNNING" ] ; then
  TUNNEL_LISTEN_PORT=$(expr $TUNNEL_LISTEN_PORT_BASE + $DEVICE_ID)
  TUNNEL_SETUP="$TUNNEL_LISTEN_PORT:$TUNNEL_LISTEN_HOST:$TUNNEL_REDIRECT_PORT"
  TUNNEL_REMOTE="$TUNNEL_REMOTE_USER@$TUNNEL_REMOTE_HOST"
  nohup ssh -N -R "$TUNNEL_SETUP" -p "$TUNNEL_REMOTE_PORT" "$TUNNEL_REMOTE" >/dev/null 2>&1 &
  echo $! > "$PID_FILENAME"
fi

