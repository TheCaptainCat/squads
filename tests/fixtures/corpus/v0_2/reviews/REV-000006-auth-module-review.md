---
id: REV-000006
type: review
title: Auth module review
slug: auth-module-review
status: Requested
author: dev-agent
refs:
- TASK-000003:addresses
created_at: '2025-03-15T10:00:00Z'
updated_at: '2025-03-15T10:00:00Z'
---
<!-- sq:body -->
# Auth module review

Review of the JWT authentication implementation.
<!-- sq:body:end -->

<!-- sq:findings -->
<!-- sq:finding:F1 -->

### F1 — Missing token expiry check

<!-- sq:finding:F1:meta -->
status: Open
severity: high
<!-- sq:finding:F1:meta:end -->

<!-- sq:finding:F1:body -->
The token expiry (`exp` claim) is not validated on every endpoint.
<!-- sq:finding:F1:body:end -->

<!-- sq:finding:F1:discussion -->
<!-- sq:finding:F1:discussion:end -->

<!-- sq:finding:F1:end -->
<!-- sq:findings:end -->

<!-- sq:summary -->
| Finding | Title | Severity | Status |
|---|---|---|---|
| F1 | Missing token expiry check | 🟠 High | 🔴 Open |
<!-- sq:summary:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
