# syntax=docker/dockerfile:1.4.1
FROM ubuntu:20.04 AS build

ENV PATH "/root/.local/bin/:$PATH"
ENV POETRY_INSTALLER_MAX_WORKERS 8

RUN apt-get update && apt-get install -y --no-install-recommends \
	python3 \
    build-essential \
    ca-certificates \
    ca-certificates \
    curl \
    git \
    python3-dev \
    python3-venv\
    && rm -rf /var/lib/apt/lists/*

RUN curl -sSL https://install.python-poetry.org | python3 -

COPY . /pythontemplate

WORKDIR /pythontemplate

RUN poetry install --without=dev,docs \
    && rm -rf .git




FROM ubuntu:20.04

ENV PATH ".venv/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /pythontemplate /pythontemplate
WORKDIR /pythontemplate
