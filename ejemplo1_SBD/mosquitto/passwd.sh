#!/bin/sh
set -eu

mkdir -p /mosquitto/config

if [ -n "${MOSQUITTO_USERNAME:-}" ] && [ -n "${MOSQUITTO_PASSWORD:-}" ]; then
  PASSFILE="/mosquitto/config/passwd"
  if [ ! -f "$PASSFILE" ]; then
    mosquitto_passwd -b -c "$PASSFILE" "$MOSQUITTO_USERNAME" "$MOSQUITTO_PASSWORD"
  else
    mosquitto_passwd -b "$PASSFILE" "$MOSQUITTO_USERNAME" "$MOSQUITTO_PASSWORD"
  fi

  chown mosquitto:mosquitto "$PASSFILE"
  chmod 600 "$PASSFILE"
else
  echo "Aviso: MOSQUITTO_USERNAME/MOSQUITTO_PASSWORD no definidos; se omitirá la generación de /mosquitto/config/passwd" >&2
fi

exec /docker-entrypoint.sh "$@"
