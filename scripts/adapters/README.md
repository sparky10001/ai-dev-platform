# 🔌 Adapters

Adapters are the **execution layer** between the stable `ai` interface and the underlying runtime.

The system has been simplified:

> **LiteLLM is now the primary execution gateway**
> Everything else is a mode on top of it.

---

## 🧠 Active Adapter

Adapters are selected via:

```bash
AI_ADAPTER in .env