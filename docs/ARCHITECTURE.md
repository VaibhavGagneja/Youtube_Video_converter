# Architecture Guide

## System Overview

The Video-to-MP3 Converter is a **microservices-based** application designed for scalability, fault tolerance, and async processing. It uses an **event-driven architecture** with RabbitMQ as the message broker.

## Service Communication

```
                    ┌──────────────────────────────────────────────┐
                    │                Kubernetes Cluster             │
                    │                                              │
  User ──▶ Ingress ──▶ ┌─────────┐     ┌──────┐     ┌───────┐   │
                    │  │ Gateway │────▶│ Auth │────▶│ MySQL │   │
                    │  │  :8080  │     │ :5000│     │ :3306 │   │
                    │  └────┬────┘     └──────┘     └───────┘   │
                    │       │                                     │
                    │       ├────▶ ┌─────────┐                   │
                    │       │      │ MongoDB │ (GridFS)          │
                    │       │      │ :27017  │◀───────┐          │
                    │       │      └─────────┘        │          │
                    │       │                         │          │
                    │       └────▶ ┌──────────┐  ┌────┴──────┐  │
                    │              │ RabbitMQ │──│ Converter │  │
                    │              │  :5672   │  │ (worker)  │  │
                    │              └────┬─────┘  └───────────┘  │
                    │                   │                        │
                    │              ┌────┴──────────┐            │
                    │              │ Notification  │            │
                    │              │  (worker)     │──▶ SMTP    │
                    │              └───────────────┘            │
                    └──────────────────────────────────────────────┘
```

## Data Flow

1. **Upload:** Gateway stores video in MongoDB (GridFS) → publishes message to `video` queue
2. **Convert:** Converter consumes from `video` queue → extracts audio → stores MP3 in MongoDB → publishes to `mp3` queue
3. **Notify:** Notification consumes from `mp3` queue → sends email with download ID
4. **Download:** User retrieves MP3 from Gateway using the file ID

## Design Decisions

| Decision | Rationale |
|----------|-----------|
| **GridFS for file storage** | Handles large files, no external storage needed |
| **RabbitMQ for messaging** | Reliable delivery, dead letter queues, management UI |
| **Separate auth service** | Independent scaling, clear security boundary |
| **StatefulSets for DBs** | Persistent storage, ordered deployment |
| **Spot instances for converter** | CPU-intensive but fault-tolerant workload |
| **Network policies** | Zero-trust: only allow required service-to-service traffic |

## Scaling Strategy

- **Gateway:** HPA based on CPU (2–5 pods in staging, 3–8 in production)
- **Converter:** HPA based on CPU (2–10 pods in staging, 3–15 in production). Uses spot instances for cost savings.
- **Auth:** Fixed replicas (stateless, low traffic)
- **Notification:** Fixed replicas (lightweight, email-bound)
