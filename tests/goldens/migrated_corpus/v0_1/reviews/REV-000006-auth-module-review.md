---
id: REV-6
sequence_id: 6
type: review
title: Auth module review
slug: auth-module-review
status: Requested
author: dev-agent
created_at: '2025-01-10T09:00:00Z'
updated_at: '2025-01-10T09:00:00Z'
---
<!-- sq:body -->
# Auth module review

Review of the JWT authentication implementation.
<!-- sq:body:end -->

## Findings

1. The token expiry (`exp` claim) is not validated on every endpoint.
2. The signing key is read from an environment variable with no rotation story.

## Discussion

<!-- sq:findings -->
<!-- sq:findings:end -->

<!-- sq:discussion -->
<!-- sq:discussion:end -->
