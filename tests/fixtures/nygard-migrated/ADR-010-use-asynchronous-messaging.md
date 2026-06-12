# ADR-010 Use Asynchronous Messaging Between Services

## Status

Accepted

## Context

The order service calls the notification service synchronously. When the
notification service is slow, order placement times out, and customers see
errors for a failure that has nothing to do with their order. The two
services have different availability requirements.

## Decision

We will decouple the order service from the notification service with a
message queue. The order service publishes an OrderPlaced event and returns;
the notification service consumes the event at its own pace.

## Alternatives Considered

<!-- TODO: document at least 2 alternatives that were considered and rejected, with reasoning. -->

## Consequences

Order placement no longer depends on notification availability. Notification
delivery becomes eventually consistent, so the UI can no longer promise that
the confirmation email was sent. We must operate a message broker and
monitor consumer lag.

## Related Decisions

- None.

## References

<!-- TODO: populate from inline citations or external sources cited in the body. -->
