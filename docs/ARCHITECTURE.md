# Architecture notes

The HTTP layer owns authentication, validation, serialization, and authorization. The processing service owns stage transitions and database writes. The ML package owns model loading, preprocessing, inference, quality, attention, video sampling, and aggregation. The storage service is the only boundary that maps an analysis to private files.

FastAPI background tasks are a deliberate single-service prototype boundary. Every job is persisted before execution, inference is protected by a bounded semaphore, and analysis state survives frontend navigation. A production worker can call the same `process_analysis(analysis_id)` entry point from a durable queue.

The frontend uses route-level product surfaces with a shared authenticated shell. TanStack Query owns server state and polling. Media assets are fetched as authenticated blobs so bearer tokens never appear in asset URLs.

