# Go Project Agent Environment

This project uses Docker containers for the coding agent and for build/test execution.

## Requirements

- Docker or Colima (Docker-compatible runtime)
- Make

## Setup

Create required container volumes:

make volumes

Build the agent container:

make build-agent

## Run the coding agent

make run-agent

## Run tests inside the execution container

make test
