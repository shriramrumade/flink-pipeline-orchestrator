# Microservices Failure Scenarios (FAANG-Level Deep Dive)

This document explains common **distributed system failures** observed
in large-scale systems at companies like Amazon, Google, and Netflix,
along with real-world use cases and implementation approaches.

------------------------------------------------------------------------

# 1. Cascading Failure

## Problem

A failure in one downstream service propagates through the entire
system.

### Example Architecture

User Service → Order Service → Payment Service → Fraud Service

If Fraud Service slows down: 1. Payment waits for Fraud 2. Order waits
for Payment 3. Requests pile up 4. Thread pools exhaust 5. Entire system
slows or crashes

## Root Causes

-   No timeouts
-   No circuit breakers
-   Blocking synchronous calls
-   Thread pool exhaustion

## Solution

### Circuit Breaker Pattern

Stops requests to failing services.

Common Java library: Resilience4j

Flow: Service → Circuit Breaker → Dependency

If dependency fails repeatedly: - Circuit opens - Calls stop
temporarily - Fallback logic executes

### Timeout Configuration Example

resilience4j: timelimiter: instances: paymentService: timeoutDuration:
2s

### Bulkhead Pattern

Separate thread pools per dependency.

Example:

ThreadPool-Payment ThreadPool-Inventory ThreadPool-Shipping

Failure in one dependency doesn't block others.

### Spring Boot Example

@CircuitBreaker(name="paymentService", fallbackMethod="fallbackPayment")
public PaymentResponse processPayment(Order order){ return
paymentClient.charge(order); }

public PaymentResponse fallbackPayment(Order order, Throwable ex){
return new PaymentResponse("Payment temporarily unavailable"); }

------------------------------------------------------------------------

# 2. Retry Storm

## Problem

When a service fails, thousands of clients retry simultaneously,
amplifying traffic.

Example:

10,000 clients call Payment Service. Service fails → All retry
instantly.

Now system receives 30,000+ requests.

System overloads further.

## Solution

### Exponential Backoff

Retry delays increase progressively.

Retry1 = 1s\
Retry2 = 2s\
Retry3 = 4s\
Retry4 = 8s

### Add Jitter

Random delay prevents synchronized retries.

Retry delay = baseDelay + random jitter

### Spring Boot Example

resilience4j: retry: instances: paymentService: maxAttempts: 3
waitDuration: 1s

Example usage:

@Retry(name="paymentService") public PaymentResponse callPayment(){
return paymentClient.charge(); }

------------------------------------------------------------------------

# 3. Database Overload

## Problem

A high-traffic endpoint causes massive database load.

Example API:

GET /product/{id}

Millions of users call this endpoint simultaneously.

Database becomes bottleneck.

## Solution

### Introduce Cache Layer

Architecture:

Client → Service → Redis Cache → Database

Flow: 1. Check cache 2. Cache miss → query DB 3. Store result in cache

### Spring Boot Implementation

@Cacheable(value="products", key="#id") public Product getProduct(Long
id){ return productRepository.findById(id); }

------------------------------------------------------------------------

# 4. Message Queue Backlog

## Problem

Message production exceeds consumption rate.

Example:

Events produced: 50k/sec\
Consumers process: 20k/sec

Backlog grows indefinitely.

## Solution

### Autoscale Consumers

Scaling rule example:

Lag \> 100k → scale to 10 consumers\
Lag \> 1M → scale to 50 consumers

### Dead Letter Queue (DLQ)

Failed messages move to DLQ for investigation.

Main Queue → Consumer → DLQ (if processing fails)

------------------------------------------------------------------------

# 5. Deployment Failures

## Problem

New deployment introduces breaking API changes.

Example:

Old API: /payment

New deployment removes response field.

Older services crash.

## Solution

### API Versioning

/v1/payment\
/v2/payment

### Canary Deployment

Traffic rollout:

1% → new version\
5% → new version\
50% → new version

Monitor metrics. Roll back if errors increase.

------------------------------------------------------------------------

# Summary

  ------------------------------------------------------------------------
  Failure           Root Cause                    Solution
  ----------------- ----------------------------- ------------------------
  Cascading Failure Dependency failure            Circuit breaker

  Retry Storm       Synchronized retries          Exponential backoff +
                                                  jitter

  Database Overload High traffic                  Cache layer

  Queue Backlog     Slow consumers                Autoscaling + DLQ

  Deployment        Breaking API change           Canary deployment +
  Failure                                         versioning
  ------------------------------------------------------------------------

------------------------------------------------------------------------

# Key Distributed System Principle

Every dependency will fail eventually.\
Architecture must tolerate those failures.
