# 0210 — Architecture Design

```
ui / cli  →  services (search, orchestrator, cleanup, config, locale)
          →  domain (Channel, DownloadJob, match, builders)
          →  infra (m3u, http, paths)
```

Patterns: **Factory**, **Builder**, **Session**, **Flywheel** (Honcho-inspired structure, no hard Honcho dep).

**Invariant:** all media artifacts under `output_root` only.
