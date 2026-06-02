#!/usr/bin/env sh
set -eu

# Prefer new variable name, keep backward-compatible fallback.
SERVERDIR="${DEVPISERVER_SERVERDIR:-${DEVPI_SERVERDIR:-/data/server}}"
SECRETFILE="${DEVPISERVER_SECRETFILE:-${SERVERDIR}/.secret}"
THREADS="${DEVPISERVER_THREADS:-8}"
CONNECTION_LIMIT="${DEVPISERVER_CONNECTION_LIMIT:-20}"
KEYFS_CACHE_SIZE="${DEVPISERVER_KEYFS_CACHE_SIZE:-2000}"
INDEXER_BACKEND="${DEVPISERVER_INDEXER_BACKEND:-whoosh}"

mkdir -p "${SERVERDIR}"

if [ ! -f "${SERVERDIR}/.serverversion" ]; then
  devpi-init --serverdir "${SERVERDIR}"
fi

if [ ! -f "${SECRETFILE}" ]; then
  devpi-gen-secret --secretfile "${SECRETFILE}"
  chmod 600 "${SECRETFILE}"
fi

exec devpi-server \
  --serverdir "${SERVERDIR}" \
  --secretfile "${SECRETFILE}" \
  --threads "${THREADS}" \
  --connection-limit "${CONNECTION_LIMIT}" \
  --keyfs-cache-size "${KEYFS_CACHE_SIZE}" \
  --indexer-backend "${INDEXER_BACKEND}" \
  --host 0.0.0.0 \
  --port "${DEVPI_PORT}"

