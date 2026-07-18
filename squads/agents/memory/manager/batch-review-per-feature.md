---
summary: One batch review per feature, never per task.
created_at: '2026-07-18T20:22:18Z'
---
When running an implementation loop, don't spawn a reviewer per task. Once **all** of a feature's tasks are implemented, spawn one reviewer pass that authors a **single REV** with findings spanning the whole batch.

My own ground-truth verification + the authoritative full-suite run as each task lands is a **separate** gate — it neither replaces nor is replaced by the batch review.

Keep the reviewer independent from the build lineage. Pierre's rule (2026-07-18).