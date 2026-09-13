FROM ghcr.io/evokoa/pggraph:1.2.0

ARG PG_MAJOR=17

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-${PG_MAJOR}-pgvector \
    && rm -rf /var/lib/apt/lists/*

COPY 02-create-pgvector.sql /docker-entrypoint-initdb.d/
