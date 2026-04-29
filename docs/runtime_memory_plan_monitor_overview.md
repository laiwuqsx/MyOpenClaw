# MyOpenClaw Runtime, Memory, Plan, and Monitor Overview

## Purpose

This document summarizes the current architecture implemented in `MyOpenClaw` as of the current control-plane work.

It focuses on:

- the LangGraph runtime structure
- the agent state model
- the memory system
- the plan and approval control plane
- the audit/monitor pipeline
- the current CLI workflow and known limits

This is intended as an implementation-oriented reference for contributors.

## High-Level Status

The project is no longer just a minimal tool-calling loop.

The current runtime now includes:

- a two-node LangGraph execution graph
- project-scoped memory and working summary injection
- explicit runtime state for task plans
- explicit runtime state for pending approvals
- permission-aware tool execution
- structured JSONL audit events
- terminal monitor views over the event stream

The system is still intentionally small, but it now has the beginnings of a real control plane.

## Runtime Architecture

Core assembly lives in [`myopenclaw/core/runtime.py`](../myopenclaw/core/runtime.py).

The graph is still a simple two-node loop:

1. `agent`
2. `tools`

The routing rule is:

- start at `agent`
- if the final `AIMessage` contains `tool_calls`, route to `tools`
- after `tools`, route back to `agent`
- if there are no tool calls, terminate at `END`

So the graph is still fundamentally a ReAct-style loop:

`START -> agent -> tools? -> agent -> ... -> END`

## AgentState

The shared graph state schema lives in [`myopenclaw/core/context.py`](../myopenclaw/core/context.py).

Current fields:

- `messages`
- `summary`
- `summary_state`
- `plan_state`
- `approval_state`

### Meaning of each field

`messages`

- the main conversational state
- includes user messages, assistant messages, and tool results

`summary`

- the short-term working summary used during context compaction
- persisted to project-level `SUMMARY.md`

`summary_state`

- currently light-weight and mostly reserved for future richer summary metadata

`plan_state`

- explicit task-plan runtime state
- not a prompt-only convention
- stored in the graph state and persisted by the checkpointer

`approval_state`

- explicit pending-approval runtime state
- used when a tool call is blocked by policy and requires user approval

## LangGraph Usage

The runtime uses LangGraph in three main ways.

### 1. `StateGraph`

`StateGraph(AgentState)` defines the graph schema and persistence boundary.

This means `messages`, `summary`, `plan_state`, and `approval_state` are part of the actual graph state, not just ad hoc Python variables.

### 2. `ToolNode`

The tool execution node is created with:

```python
ToolNode(actual_tools, wrap_tool_call=wrap_tool_call_with_permissions)
```

This is important because tool execution is not just "invoke the tool".

It is now:

- inspect the tool request
- evaluate tool permission policy
- either block and write approval state
- or allow and execute the tool

### 3. `Command(update=...)`

This is the key mechanism used to make tools modify runtime state directly.

Two important current uses:

- `update_plan(...)` returns `Command(update={"plan_state": ...})`
- blocked approval-required tool calls return `Command(update={"approval_state": ...})`

This is what turns plans and approvals into real runtime state rather than plain text.

## Current Prompt Construction

Prompt assembly happens in [`myopenclaw/core/context_pipeline.py`](../myopenclaw/core/context_pipeline.py) and [`myopenclaw/core/prompt_builder.py`](../myopenclaw/core/prompt_builder.py).

For each agent turn, the runtime:

1. loads the current message history
2. normalizes or loads the current working summary
3. compacts old turns if needed
4. loads memory blocks
5. renders `plan_state` into prompt text if present
6. renders `approval_state` into prompt text if present
7. builds one final `SystemMessage`
8. prepends that `SystemMessage` to the retained non-system messages

### Current system prompt sections

- base system prompt
- injected memory
- working summary
- plan state
- pending approval

The model therefore sees not just conversation history, but also the current memory layer and control-plane state.

## Memory System

The memory system is split into dedicated modules under [`myopenclaw/core/memory/`](../myopenclaw/core/memory/).

### Main pieces

[`models.py`](../myopenclaw/core/memory/models.py)

- shared memory data structures

[`files.py`](../myopenclaw/core/memory/files.py)

- file reads
- recent daily-memory discovery

[`injection.py`](../myopenclaw/core/memory/injection.py)

- decides which memory files should be injected into the prompt
- formats loaded memory blocks for prompt injection

[`summary.py`](../myopenclaw/core/memory/summary.py)

- working summary load/save/normalize logic

### Current memory layers

Global durable memory:

- global `USER.md`
- global `MEMORY.md`
- global `SOUL.md`

Project-scoped memory:

- repo `OPENCLAW.md`
- repo `.myopenclaw/OPENCLAW.md`
- project auto-memory `MEMORY.md`
- project `SUMMARY.md`
- optional project daily notes

Compatibility inputs:

- legacy `AGENTS.md`
- optional legacy `user_profile.md`

### Runtime memory behavior

The runtime distinguishes between:

- durable memory
- project instructions
- short-term working summary
- daily notes

Current policy:

- daily memory is not injected by default
- legacy profile memory is not injected by default
- working summary is loaded and updated through compaction
- durable memory is injected into the system prompt as structured blocks

## Plan State

Plan logic lives in [`myopenclaw/core/control.py`](../myopenclaw/core/control.py) and is exposed to the model through the built-in tool [`update_plan`](../myopenclaw/core/tools/builtins.py).

### What `plan_state` is

`plan_state` is a graph state field containing:

- `items`
- `explanation`
- `updated_at`

Each plan item has:

- `step`
- `status`

Supported statuses:

- `pending`
- `in_progress`
- `completed`

The runtime currently enforces that at most one step can be `in_progress`.

### What `update_plan` does

`update_plan(...)` is a real tool call, not a prompt convention.

It:

1. validates plan items
2. builds normalized `plan_state`
3. logs a `plan_updated` audit event
4. returns `Command(update={"plan_state": ...})`
5. also emits a matching `ToolMessage` for the tool call

### Current behavior limits

The runtime now supports plan state, but it does not yet force all complex tasks to create a plan first.

So at the moment:

- the agent can use `update_plan`
- the current plan is visible through `/plan`
- the plan survives in the checkpoint
- but plan-first execution is still instruction-driven, not yet hard-enforced by runtime policy

## Approval State and Tool Permissioning

Permission logic lives in [`myopenclaw/core/permissions.py`](../myopenclaw/core/permissions.py).

### Current permission model

Tools carry contracts including fields such as:

- `risk`
- `permission_mode`
- `requires_approval`
- `read_only`
- `write_scope`

Those contracts are read at tool-execution time by `wrap_tool_call_with_permissions(...)`.

### Approval flow

When a tool request is evaluated:

- if the tool is allowed, it executes normally
- if it is blocked and requires approval, the wrapper does not execute the tool
- instead it creates `approval_state`
- logs `approval_requested`
- returns `Command(update={"approval_state": ...})`

### Current `approval_state`

The pending approval object currently stores:

- `status`
- `tool_name`
- `permission_mode`
- `risk`
- `write_scope`
- `reason`
- `tool_args`
- `requested_at`

### Current CLI behavior

The CLI currently supports:

- `/plan`
- `/approvals`
- `/approve <tool_name|permission_mode>`

Important current limitation:

- approval does not yet automatically replay the previously blocked tool call
- after approval, the user must ask again for the action to be executed

## Monitor and Audit Pipeline

Audit logging lives in [`myopenclaw/core/logger.py`](../myopenclaw/core/logger.py).

Monitor rendering lives in [`myopenclaw/core/monitor.py`](../myopenclaw/core/monitor.py).

CLI monitor entry lives in [`entry/monitor.py`](../entry/monitor.py).

### Current audit model

The runtime writes structured JSONL events including:

- `llm_input`
- `tool_call`
- `tool_result`
- `ai_message`
- `tool_permission`
- `tool_blocked`
- `approval_requested`
- `plan_updated`
- shell-related events such as `shell_executed`, `shell_blocked`, `shell_timeout`, and `shell_error`

Events include metadata such as:

- `thread_id`
- `session_id`
- `session_mode`
- `provider`
- `model`
- `tool`
- `duration_ms`
- `error`
- `risk`
- `permission`
- `approval_required`
- `contract`

### Current monitor views

The monitor currently supports:

- `dashboard`
- `thread`
- `replay`

These views summarize thread activity, event counts, recent events, anomalies, and chronological execution chains.

## CLI Runtime Behavior

The interactive runtime is implemented in [`entry/main.py`](../entry/main.py).

Current behavior:

- starts one local thread id: `local_main`
- uses the LangGraph app with SQLite checkpointing
- accepts user input from the terminal
- streams runtime updates back to the user
- shows tool calls as they happen
- supports `/plan`, `/approvals`, and `/approve ...`

For compatibility with terminals that did not render the previous ANSI-heavy output correctly, the CLI currently uses plain-text output rather than rich inline color formatting.

## End-to-End Flow

The current end-to-end flow is:

1. user types a message in the CLI
2. the message is wrapped as a `HumanMessage`
3. the graph enters the `agent` node
4. context is prepared from:
   - retained messages
   - memory
   - working summary
   - plan state
   - approval state
5. the LLM produces either:
   - a final answer
   - or a tool call
6. if there is a tool call, the graph enters `tools`
7. the permission wrapper evaluates the request
8. the tool either:
   - executes and produces a `ToolMessage`
   - updates `plan_state`
   - or writes `approval_state` instead of executing
9. control returns to `agent`
10. if no new tool call is emitted, the graph terminates at `END`
11. the final assistant answer is displayed to the user

## Current Limits

Important current limitations include:

- complex tasks are not yet forced into a plan-first workflow
- approval does not yet replay blocked tool calls automatically
- approval granularity is session-level by tool or permission, not per-request id
- tool permission contracts are present but still relatively simple
- memory is layered correctly, but detailed topic-file retrieval is not yet mature
- skill loading and heartbeat remain separate future phases

## Summary

The current runtime should be understood as:

- still a compact two-node LangGraph loop
- but no longer just a plain ReAct tool runner

It now has:

- persistent project-scoped memory
- summary compaction
- explicit plan state
- explicit approval state
- permission-aware tool execution
- structured audit events
- monitor views over the event stream

This is the current foundation for moving from a small local tool-calling runtime toward a more controlled coding-agent runtime.
