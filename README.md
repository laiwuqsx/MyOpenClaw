# MYCLAW

MYCLAW is a local agent runtime for transparent, controllable, and extensible AI workflows.

It is designed for developers who want more than a chat wrapper. The project focuses on making agent behavior observable, bounded, and practical in a local workspace environment.

## What It Does

MYCLAW provides a command-line agent that can:

- respond to user instructions
- call local tools
- work inside a constrained workspace
- maintain persistent user memory
- load external skills from local folders
- log and monitor its own behavior
- handle scheduled background tasks

## Core Features

### Transparent Agent Execution

The runtime records key events across the full interaction flow:

- model input
- tool calls
- tool results
- assistant messages
- system actions

This makes the agent easier to debug, inspect, and trust.

### Constrained Local Workspace

MYCLAW is built around a dedicated local workspace model.

- file operations are restricted to a controlled area
- shell commands execute within workspace boundaries
- dangerous path traversal and unsafe command patterns can be blocked

The goal is to reduce accidental overreach while keeping the agent useful.

### Persistent Memory

The system separates memory into two layers:

- long-term user profile
- short-term conversation context with summary compression

This helps preserve continuity without letting context grow without bound.

### Extensible Skill System

Skills can be loaded from local directories and exposed as callable capabilities.

Each skill can provide:

- a human-readable manual
- an execution interface
- a two-step workflow where the agent can inspect first and execute second

This keeps extensions flexible while preserving interpretability.

### Live Monitoring and Audit Logs

Agent activity can be written to structured logs and rendered in a live monitor view.

This is useful for:

- debugging tool usage
- reviewing model decisions
- understanding runtime behavior over time

### Background Task Handling

MYCLAW can support scheduled reminders and recurring tasks through a heartbeat-style task loop.

Background events are fed back into the same runtime instead of being handled by a disconnected subsystem.

## Intended Use Cases

- local AI assistant development
- agent runtime experimentation
- tool-calling workflow prototypes
- transparent developer assistants
- sandboxed local automation

## Design Philosophy

MYCLAW is built around a few practical ideas:

- local-first execution
- transparent behavior over black-box magic
- controlled extensibility
- incremental complexity
- developer-readable architecture

## Status

This project is under active development.

The current focus is on establishing a solid runtime foundation before expanding the ecosystem around it.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
myopenclaw run
```

Useful commands:

- `myopenclaw config`
- `myopenclaw run`
- `myopenclaw monitor`
