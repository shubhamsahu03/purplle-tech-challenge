# System Design & Architecture Overview

## The Decoupled Edge-to-Cloud Paradigm
The Purplle Store Intelligence platform is designed around a decoupled, event-driven architecture, mirroring enterprise-grade IoT and retail analytics deployments. Rather than forcing a single monolithic container to handle heavy GPU tensor operations alongside lightweight web requests, the system is strictly divided into an offline/edge detection layer and a real-time online API layer. 

This separation of concerns ensures that the intelligence API remains highly available, horizontally scalable, and resilient to upstream edge device failures. 

### 1. The Detection Layer (Edge / Batch)
The detection pipeline acts as the physical store's edge compute, driven by a multi-tenant `STORE_CONFIGS` router that dynamically maps physical camera polygons to semantic retail zones. 
**Tracking & Grouping:** It utilizes YOLOv8m for high-accuracy bounding box detection, coupled with ByteTrack for persistent cross-frame tracking.To handle the group entry edge case, it applies a temporal clustering algorithm that assigns a shared `group_id` to visitors entering within a 3.0-second window. Cross-camera tracking is strictly isolated per store using a Store-Scoped ReID graph.
* **Hybrid Staff Exclusion:** To separate staff from customers, the pipeline uses a hybrid ensemble approach. A subject is flagged as staff if they meet *any* of three conditions: (1) appearing on an excluded "staff-only" camera, (2) scoring above a 0.28 threshold via zero-shot Hugging Face CLIP analysis, or (3) spending >50% of their tracked frames inside a designated staff polygon. 
* **Output:** This layer processes raw video arrays into sparse, high-value state-change payloads (e.g., `ZONE_ENTER`, `BILLING_QUEUE_JOIN`) and outputs them to an `events.jsonl` artifact.

### 2. The Intelligence API (Cloud / Online)
The backend is a FastAPI application backed by a highly asynchronous SQLAlchemy + SQLite database. It exposes an idempotent `POST /events/ingest` endpoint. Designing data pipelines for large-scale asynchronous environments necessitates strict idempotency; if a network partition causes the edge node to re-transmit a batch of 500 events, the API safely catches `IntegrityError` exceptions on the `event_id` primary key, preventing double-counting in the funnel metrics. 

### 3. The Presentation Layer (Operations)
The Streamlit frontend acts as the control plane for store operators. It polls the FastAPI endpoints, rendering live zone heatmaps, funnel drop-offs, and critical operational anomalies (like queue spikes or dead zones) in real-time.

---

## AI-Assisted Decisions

Throughout the development lifecycle, LLMs (Large Language Models) were utilized as pair-programmers and architectural sounding boards.

**1. Database Idempotency Logic (Agreed)**
* **Context:** When designing the `/events/ingest` endpoint, I initially considered using a simple Pandas in-memory dataframe cache for rapid hackathon prototyping.
* **AI Input:** The AI pointed out that Pandas lacks native primary-key constraints, which would make handling duplicate network payloads fragile. It suggested migrating to SQLAlchemy and leveraging `IntegrityError` rollbacks.
* **Verdict:** **Agreed.** I adopted the SQLAlchemy approach. While heavier to implement, it made the system inherently fault-tolerant and perfectly satisfied the "Production Readiness" idempotency rubric requirement.

**2. Dwell Time Calculation (Overrode & Iterated)**
* **Context:** Calculating how long a shopper spends in the `MAKEUP` zone. 
* **AI Input:** The AI initially suggested adding a `dwell_ms` variable to the tracker state and incrementing it frame-by-frame (e.g., adding 66ms per frame at 15 FPS), then passing that calculated integer in the JSON payload.
* **Verdict:** **Overrode.** Calculating time incrementally across frames is prone to left-censoring bugs if a bounding box drops for a split second. I overrode the AI's suggestion and redesigned the pipeline to pass raw UTC timestamps instead. I then worked with the AI to write a robust Pandas `groupby()` aggregation in the API layer that calculates true physical dwell time by subtracting the absolute `min` timestamp from the `max` timestamp of a given session in a zone. This fundamentally shifted the math from a brittle edge-calculation to a resilient database calculation.

**3. Headless VLM Loading in Constrained Environments (Agreed & Refined)**
* **Context:** Implementing the CLIP model for zero-shot staff detection inside a hosted Kaggle/Docker environment.
* **AI Input:** The AI flagged that standard Hugging Face initializations often crash or deadlock in notebook environments due to aggressive progress-bar stdout buffering and parallel tokenizer warnings. It provided a "Circuit Breaker" boilerplate.
* **Verdict:** **Agreed & Refined.** I integrated the AI's suggestions (`HF_HUB_DISABLE_PROGRESS_BARS=1`, `TOKENIZERS_PARALLELISM=false`) and further optimized the model loading by injecting `low_cpu_mem_usage=True` to stream weight parameters directly to the GPU. This prevented Out-Of-Memory (OOM) crashes during container builds and ensured the pipeline degraded gracefully.