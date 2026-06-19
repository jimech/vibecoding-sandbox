
# AI Coding Agent Sandbox

This project is a Streamlit dashboard for testing an AI coding agent inside a security-constrained sandbox.

## Overview

The demo shows how a local AI coding agent can propose commands while a sandbox layer checks and blocks risky actions before execution.

The dashboard includes:

- A Streamlit interface
- Local model support through Ollama
- Docker-based sandbox execution
- Boundary-violation detection
- Logs for security observations and blocked commands
- Tabs for benign tasks, pre-built attacks, live sandbox commands, and agent chat

## Screenshots

### Chat with agent

![Chat with agent](docs/images/streamlit-chat.png)

### Dashboard

![Dashboard](docs/images/streamlit-dashboard.png)

### Live sandbox

![Live sandbox](docs/images/streamlit-live.png)

## How to run

Start the Ollama model:

```bash
ollama run qwen2.5-coder:14b
