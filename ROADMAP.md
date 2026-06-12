# AgentForge Release Roadmap

This roadmap tracks feature implementations, phases milestones, and upcoming architectural improvements.

---

## 🚀 Phase Status & Milestones

### **Completed Milestones**
- **Phase 0.5: Production Foundation**: Configured settings, JSON logging, middleware rate limiting, Prometheus metrics endpoints, and health monitoring.
- **Phase 4.5: Agent Runtime Engine**: Decoupled agent execution workers, topic messaging channels, and cron-based background schedulers.
- **Phase 5.5: Knowledge & RAG Engine**: Parse upload formats, semantic overlaps text splitter, Ollama vectorizer, and source bracket prompt citations.
- **Phase 6.5: Workflow Runtime**: Parallel node runs using `asyncio.gather`, state logs checkpoints database saves, and exponential retry policies.
- **Phase 8: Developer Ecosystem**: Base custom Python BaseTool classes, folder loaders, and signed HMAC webhooks.

### **Upcoming Milestones (Next Releases)**
- **Phase 7: High Fidelity Web UI Dashboard**: Refactor Next.js client layout matching modern styles:
  - Sidebar workspace.
  - Drag-and-drop ingestion file panels.
  - Side-by-side agent conversation tester.
- **Phase 10: Production Deployments**: Maintain production compose stacks and production Kubernetes manifests.

---

## 🔮 Future Research Directions
- **Distributed Orchestration**: Moving scheduler and task execution queues from in-process asyncio to Redis/Celery.
- **Agent Sandbox Containment**: Isolate executing custom Python scripts inside secure Docker containers instead of native subprocess execution environments.
- **Alternative Vector Drivers**: Support PGVector and Qdrant integration.
