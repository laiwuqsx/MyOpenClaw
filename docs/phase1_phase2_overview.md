# MyOpenClaw Phase 1 & Phase 2 Overview

## Purpose

This document summarizes what has been completed in Phase 1 and Phase 2 of `MyOpenClaw`, what each important file currently does, and how the runtime flows from user input to final response.

This is an internal learning and implementation note.

## High-Level Summary

The project has completed two major early stages:

- **Phase 1** established the modular runtime foundation
- **Phase 2** connected that foundation to a minimal interactive CLI runtime

The result is no longer a bootstrap shell. It is now a small but real local tool-calling agent runtime.

## What Phase 1 Did

Phase 1 focused on architecture, not on feature breadth.

The main goal was to avoid repeating the original CyberClaw problem where too much logic lived in one place.

### Phase 1 outcomes

- introduced a thin compatibility layer in `agent.py`
- introduced explicit runtime assembly in `runtime.py`
- introduced per-turn execution logic in `turn_manager.py`
- introduced a dedicated context preparation pipeline in `context_pipeline.py`
- introduced a dedicated prompt construction layer in `prompt_builder.py`
- introduced explicit session context in `session_state.py`
- introduced dedicated compaction and summary helpers
- introduced a memory subsystem under `core/memory/`
- expanded config paths for workspace memory files
- added minimum memory tools
- added tests for the new architecture

### Main architectural shift in Phase 1

Before this structure, the typical anti-pattern would be:

- read memory
- build prompt
- compact messages
- call model
- log tool calls
- update summary

all inside one large runtime function.

After Phase 1, those responsibilities are split into dedicated modules.

## What Phase 2 Did

Phase 2 focused on wiring the modular foundation into a usable interactive runtime.

### Phase 2 outcomes

- converted `entry/main.py` from a placeholder into a real CLI runtime
- loaded provider/model configuration from `.env`
- created a LangGraph app through `create_agent_app()`
- used `AsyncSqliteSaver` as the checkpointer
- accepted terminal input through `prompt_toolkit`
- wrapped user input into `HumanMessage`
- streamed runtime updates back to the terminal
- displayed tool-call events in the CLI
- rendered final assistant responses in the CLI
- added a runtime creation test

### Phase 2 result

The project can now:

- start from the CLI
- send a user message into the runtime
- run the agent/tool loop
- return a final response

This is the first point where the project behaves like a real agent runtime instead of a prepared skeleton.

## File-by-File Roles

### Entry Layer

#### `entry/cli.py`

Role:

- top-level command entrypoint
- provides `config`, `run`, and `monitor`

Current use:

- `config` writes local model configuration into `.env`
- `run` starts the interactive runtime
- `monitor` is reserved for later observability work

#### `entry/main.py`

Role:

- actual interactive CLI runtime

Current responsibilities:

- load `.env`
- build the runtime app
- create the sqlite checkpointer
- start the prompt loop
- send user input into the LangGraph app
- display tool calls and final output

### Core Runtime Layer

#### `myopenclaw/core/agent.py`

Role:

- compatibility layer only

Current responsibilities:

- expose `create_agent_app(...)`
- delegate actual runtime construction to `runtime.create_runtime(...)`

Why this matters:

- keeps old-style entrypoints stable
- prevents business logic from growing inside `agent.py`

#### `myopenclaw/core/runtime.py`

Role:

- runtime assembly

Current responsibilities:

- load provider-backed LLM
- collect tools
- bind tools to the model
- create `ToolNode`
- define the LangGraph workflow
- connect `agent -> tools -> agent`

This file is the main graph construction layer.

#### `myopenclaw/core/turn_manager.py`

Role:

- execute one agent turn

Current responsibilities:

- log recent tool results
- call `prepare_context(...)`
- log model input event
- call the model with tools bound
- log tool calls or direct assistant messages
- build `state_updates`

This file is the business logic for one step of the runtime.

#### `myopenclaw/core/context_pipeline.py`

Role:

- prepare the final message list for the model

Current responsibilities:

- inspect current state
- compact old messages if needed
- update working summary if old turns were discarded
- load memory blocks
- build the system prompt
- return final `messages_for_llm`

This file is the main context-preparation layer.

#### `myopenclaw/core/prompt_builder.py`

Role:

- prompt construction only

Current responsibilities:

- define base system prompt
- add memory section
- add summary section
- build final system prompt

It does **not**:

- load files
- compact messages
- call the model

#### `myopenclaw/core/session_state.py`

Role:

- explicit session metadata

Current responsibilities:

- define `SessionContext`
- derive session values from runtime config

Key fields:

- `session_id`
- `session_mode`
- `thread_id`
- `workspace_dir`
- `provider_name`
- `model_name`

#### `myopenclaw/core/compaction.py`

Role:

- compaction and summary update helpers

Current responsibilities:

- determine whether context should be compacted
- trim message history
- summarize discarded messages
- generate `RemoveMessage` commands

#### `myopenclaw/core/context.py`

Role:

- low-level context helper

Current responsibilities:

- define `AgentState`
- implement `trim_context_messages(...)`

Important note:

This is no longer the full context-management layer. It is only a helper module.

### Memory Layer

#### `myopenclaw/core/memory/models.py`

Role:

- shared memory data structures

Current classes:

- `MemoryFileSpec`
- `LoadedMemoryBlock`
- `SummaryState`

#### `myopenclaw/core/memory/files.py`

Role:

- file I/O for memory

Current responsibilities:

- read text files safely
- discover recent daily memory files
- load one memory file from a spec
- load recent daily memory blocks

#### `myopenclaw/core/memory/injection.py`

Role:

- decide which memory files are injected

Current responsibilities:

- build memory file specs by session mode
- load memory blocks
- render blocks into prompt-ready text

#### `myopenclaw/core/memory/summary.py`

Role:

- summary prompt helpers

Current responsibilities:

- build a summary-update prompt
- normalize the summary output

### Support Layer

#### `myopenclaw/core/provider.py`

Role:

- model provider abstraction

Current responsibilities:

- create a LangChain-compatible chat model for:
  - OpenAI
  - Anthropic
  - Ollama
  - other OpenAI-compatible endpoints

#### `myopenclaw/core/logger.py`

Role:

- JSONL event logger

Current responsibilities:

- persist audit events per thread
- write logs asynchronously through a queue

#### `myopenclaw/core/bus.py`

Role:

- shared async queue

Current responsibilities:

- expose `task_queue`
- expose `emit_task(...)`

This becomes more important in later heartbeat/task phases.

#### `myopenclaw/core/skill_loader.py`

Role:

- placeholder for future dynamic skill loading

Current state:

- returns an empty list for now

#### `myopenclaw/core/tools/base.py`

Role:

- shared tool abstraction

Current responsibilities:

- expose `myopenclaw_tool`
- provide a base class for more complex tool implementations

#### `myopenclaw/core/tools/builtins.py`

Role:

- minimum built-in tool set

Current tools:

- `get_current_time`
- `calculator`
- `read_user_profile`
- `save_user_profile`
- `append_daily_memory`

These tools give the runtime a minimal but real tool-calling surface.

#### `myopenclaw/core/tools/sandbox_tools.py`

Role:

- placeholder for workspace sandbox tooling

Current state:

- reserved for later phases

## Current Runtime Flow

This is the current end-to-end flow in Phase 2.

```text
User types into terminal
  ->
entry/main.py receives input
  ->
input is wrapped as HumanMessage
  ->
LangGraph app is called through app.astream(...)
  ->
runtime.py enters the "agent" node
  ->
turn_manager.py runs one turn
  ->
context_pipeline.py prepares prompt context
  ->
compaction.py may compact old messages and update summary
  ->
memory/injection.py loads memory blocks
  ->
prompt_builder.py builds the final system prompt
  ->
turn_manager.py invokes llm_with_tools
  ->
if tool call exists:
  tool node executes tool
  ->
  graph returns to agent node
else:
  final response is returned
  ->
entry/main.py renders output in the terminal
```

## LangChain and LangGraph in This Project

### LangChain is used for

- message objects
- model interfaces
- tool abstractions
- tool binding

Examples in this project:

- `HumanMessage`, `AIMessage`, `SystemMessage`, `ToolMessage`
- `BaseTool`
- `ChatOpenAI`, `ChatAnthropic`, `ChatOllama`
- `llm.bind_tools(...)`

### LangGraph is used for

- stateful runtime orchestration
- agent/tool loop control
- graph construction

Examples in this project:

- `StateGraph`
- `ToolNode`
- `START`
- `END`
- `tools_condition`

## What Is Working Now

At the current point, the project already supports:

- installable package structure
- config-driven model selection
- modular runtime architecture
- minimal memory injection architecture
- summary compaction path
- test-covered runtime foundation
- interactive CLI runtime
- minimal tool-calling loop

## What Is Not Done Yet

The following are still future work:

- full workspace sandbox tools
- dynamic skill loading
- full monitor UI
- heartbeat scheduled tasks
- richer built-in tool set
- stronger runtime integration tests

## Recommended Reading Order

If you want to study the current codebase efficiently, read files in this order:

1. `entry/main.py`
2. `myopenclaw/core/runtime.py`
3. `myopenclaw/core/turn_manager.py`
4. `myopenclaw/core/context_pipeline.py`
5. `myopenclaw/core/prompt_builder.py`
6. `myopenclaw/core/memory/injection.py`
7. `myopenclaw/core/memory/files.py`
8. `myopenclaw/core/compaction.py`
9. `myopenclaw/core/provider.py`
10. `myopenclaw/core/tools/builtins.py`

## One-Sentence Summary

After Phase 1 and Phase 2, `MyOpenClaw` has evolved from a bootstrap skeleton into a small but real modular local agent runtime with a working interactive CLI and a clean internal architecture.
