#!/bin/bash
set -e

# Install pgvector if not already present
apt-get update
apt-get install -y postgresql-15-pgvector

# Enable the extension
echo "CREATE EXTENSION IF NOT EXISTS vector;" > /docker-entrypoint-initdb.d/pgvector.sql
