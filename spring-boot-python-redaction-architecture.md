# Java Spring Boot + Python Redaction Architecture

## Overview

This document describes the architecture for a **Spring Boot Java application** that exposes REST APIs to accept **text or files containing sensitive data**, invokes a **Python redaction/anonymization library**, and returns **redacted text or files** to consumers.

The Python redaction logic is executed **inside the same JVM** using an embedded Python runtime (JEP-style integration), ensuring **low latency, high throughput, and no external process spawning**.

---

## High-Level Architecture

```
┌────────────────────────┐
│        Consumer        │
│  (UI / API Client)     │
│  - Text Input          │
│  - File Upload         │
└───────────┬────────────┘
            │ HTTP(S)
            ▼
┌──────────────────────────────────────────────┐
│            Spring Boot Application            │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │ REST Controller                         │  │
│  │ - /redact/text                          │  │
│  │ - /redact/file                          │  │
│  └──────────────┬─────────────────────────┘  │
│                 │                             │
│  ┌──────────────▼─────────────────────────┐  │
│  │ Redaction Service Layer                  │  │
│  │ - Validation                             │  │
│  │ - File handling                          │  │
│  │ - Orchestration                          │  │
│  └──────────────┬─────────────────────────┘  │
│                 │ Embedded Python (JEP)       │
│  ┌──────────────▼─────────────────────────┐  │
│  │ Python Runtime (Embedded in JVM)         │  │
│  │ - Interpreter Pool                       │  │
│  │ - Thread-safe execution                  │  │
│  └──────────────┬─────────────────────────┘  │
│                 │                             │
│  ┌──────────────▼─────────────────────────┐  │
│  │ Python Redaction Library                 │  │
│  │ - PII Detection                          │  │
│  │ - Masking / Tokenization                 │  │
│  │ - Anonymization                          │  │
│  └────────────────────────────────────────┘  │
│                                              │
└───────────┬──────────────────────────────────┘
            │
            ▼
┌────────────────────────┐
│   Redacted Response    │
│   - Text               │
│   - File               │
└────────────────────────┘
```

---

## Components

### Consumer
- Web UI / API client
- Sends text or file
- Receives redacted output

### Spring Boot Application
- REST APIs
- Validation and orchestration
- Calls embedded Python redaction logic

### Java ↔ Python Integration
- Embedded Python runtime
- No external process
- Low-latency execution

### Python Redaction Library
- Detects PII
- Applies masking/anonymization
- Returns redacted output

---

## Request Flow

```
Client → Controller → Service → Python → Service → Controller → Client
```

---

## Security & Scalability

- TLS encryption
- In-memory processing
- Horizontal scaling via multiple JVM instances
- Configurable interpreter pool

---

## Summary

This architecture provides a **production-grade**, **low-latency**, and **secure** solution for sensitive data redaction using Spring Boot and embedded Python.
