# Changelog

All notable changes to this project will be documented in this file.

---

## [0.2.0] - 2026-06-12

### Added
- **Production Foundation**: Configured settings, JSON structured logging, rate limiting middleware, Prometheus metrics endpoints, and health monitoring.
- **Agent Runtime Engine**: Decoupled agent execution workers, topic messaging channels, and cron-based background schedulers.
- **Knowledge & RAG Engine**: Parse upload formats, semantic overlaps text splitter, Ollama vectorizer, and source bracket prompt citations.
- **Workflow Runtime**: Parallel node runs using `asyncio.gather`, state logs checkpoints database saves, and exponential retry policies.
- **Developer Ecosystem**: Base custom Python BaseTool classes, folder loaders, and signed HMAC webhooks.
- **Advanced Automated Test Suite**: Integration tests covering RAG text ingestion, parallel workflow DAG checks, and webhook loops.
