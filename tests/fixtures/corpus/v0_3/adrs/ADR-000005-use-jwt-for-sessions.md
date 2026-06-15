---
id: ADR-000005
sequence_id: 5
type: decision
title: Use JWT for sessions
slug: use-jwt-for-sessions
status: Accepted
author: dev-agent
created_at: '2025-05-20T11:00:00Z'
updated_at: '2025-05-20T11:00:00Z'
---
<!-- sq:body -->
# Use JWT for sessions

We will use JSON Web Tokens for session management.

## Context

Stateless authentication is required for horizontal scaling.

## Decision

Use JWT signed with HS256.

## Consequences

Tokens cannot be invalidated before expiry without a blocklist.
<!-- sq:body:end -->

## Discussion

<!-- sq:discussion -->
<!-- sq:discussion:end -->
