# AgentForge Platform Architecture

AgentForge is a production-grade, local-first AI operating platform built for developers, enabling autonomous multi-agent creation, visual workflow graph building, and local document RAG ingestion.

---

## 1. System Overview

AgentForge is structured as a monolithic repository dividing execution concerns between a robust Python FastAPI backend and a Next.js 14 responsive web frontend.

```
+-------------------------------------------------------------+
|                        AgentForge Web                       |
|           (Next.js, TailwindCSS, React Flow Studio)          |
+------------------------------+------------------------------+
                               |
                               | REST & WebSockets
                               v
+-------------------------------------------------------------+
|                      FastAPI Web Server                     |
|           (Uvicorn, Rate-limiting, OTel Metrics)            |
+------+-----------------------+-----------------------+------+
       |                       |                       |
       | Database CRUD         | Vector Search         | LLM Completion Streams
       v                       v                       v
+------+------+         +------+------+         +------+------+
|  SQLModel   |         |  ChromaDB   |         |    Local    |
| (SQLite /   |         | (Persistent |         | Ollama Node |
| PostgreSQL) |         |   Client)   |         |    API      |
+-------------+         +-------------+         +-------------+
```

---

## 2. Core Subsystems

### 2.1 Agent Runtime Engine
Decoupled execution manager isolates running agent jobs from incoming WebSocket/REST drops.
- **AgentSessionManager**: Spawns and manages async workers.
- **EventBus**: Asynchronous queue routing intermediate outputs (thought, tool calls, and text tokens) over real-time WebSockets to the web clients.
- **AgentMessageChannel**: Decoupled pub/sub topic broker enabling multiple executing agent workers to subscribe to named message queues and coordinate outputs.

### 2.2 Knowledge & RAG Engine
- **Ingestion Pipeline**: Processes PDF document uploads using `pypdf`, strips Markdown layouts, and scrapes website HTML paragraphs.
- **Chunking Splitter**: Iterates over inputs using overlapping character windows (defaulting to 600 characters size, 80 characters overlap).
- **Embedding client**: Posts blocks to local Ollama (`POST /api/embeddings` using `nomic-embed-text`) and saves float arrays inside ChromaDB collection slices.
- **Context Citations**: Similars matches from ChromaDB are formatted into structured citations bracket templates injected in the Agent prompt context.

### 2.3 Workflow DAG Graph Runner
- **Concurrently Processing**: Independent steps in the visual React Flow workflow graph run in parallel using python `asyncio.gather()`.
- **Node Log Checkpointing**: Outputs and execution state parameters (`pending`, `running`, `completed`, `failed`) are logged in the database table log `WorkflowNodeExecutionLog` at every step, supporting execution resumes.
- **Retry Logic**: Supports custom maximum retries and exponential backoff configuration per step.

### 2.4 Developer Webhooks
- **Dispatcher Loop**: Dispatch triggers sign outgoing JSON payloads with HMAC-SHA256 signatures (`X-AgentForge-Signature` header) using subscription secrets and write delivery logs.

---

## 3. Database Schema Layout

```
                  +-------------------+
                  |       User        |
                  +---------+---------+
                            | 1
                            |
                            | *
                  +---------v---------+
                  |    Conversation   |
                  +---------+---------+
                            | 1
                            |
                            | *
                  +---------v---------+
                  |      Message      |
                  +-------------------+

+-----------------------------------------------------------+

                  +-------------------+
                  |     Workflow      |
                  +---------+---------+
                            | 1
                            |
                            | *
                  +---------v---------+
                  | WorkflowExecution |
                  +---------+---------+
                            | 1
                            |
                            | *
                  +---------v---------+
                  |  NodeExecutionLog |
                  +-------------------+
```
- **Agent**: Contains persona settings, linked MCP tools configuration, and the related `knowledge_collection_id`.
- **ScheduledJob**: Tracks cron schedule definitions managed by the background Task Scheduler.
