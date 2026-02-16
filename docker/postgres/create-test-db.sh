#!/bin/bash
set -e

# This script runs on first Postgres container start (via /docker-entrypoint-initdb.d/).
# It creates the test database alongside the default one.

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE DATABASE planflow_test;
EOSQL
