# FAANG-Level Microservices Architecture Review Checklist

## 1. Service Boundaries & Domain Design

1.  Service boundaries align with bounded contexts (Domain Driven
    Design).
2.  Each service owns its own data store.
3.  No shared databases across services.
4.  Clear domain ownership and responsibilities.
5.  APIs represent business capabilities.
6.  Avoid chatty inter-service communication.
7.  Services are independently deployable.
8.  No cyclic dependencies between services.
9.  Data ownership clearly defined.
10. Domain events used where appropriate.

## 2. API Design & Contracts

11. APIs follow consistent design standards.
12. API versioning strategy defined.
13. Backward compatibility maintained.
14. Clear request/response schemas.
15. Pagination for large datasets.
16. Proper HTTP semantics used.
17. Idempotent operations supported.
18. API documentation provided (OpenAPI/Swagger).
19. Consumer-driven contract testing implemented.
20. API deprecation strategy defined.

## 3. Communication & Messaging

21. Synchronous vs asynchronous communication chosen appropriately.
22. Messaging used to decouple services where needed.
23. Reliable message delivery mechanisms.
24. Message schemas versioned.
25. Event-driven architecture supported.
26. Dead letter queues configured.
27. Retry strategies implemented.
28. Backpressure handling implemented.
29. Message ordering considered.
30. Idempotent message processing ensured.

## 4. Service Discovery & Networking

31. Dynamic service discovery supported.
32. DNS or registry-based discovery implemented.
33. Services do not hardcode endpoints.
34. Internal networking secured.
35. Service mesh considered if required.
36. Network policies defined.
37. Cross-zone networking optimized.
38. Latency impact analyzed.

## 5. Resilience & Fault Tolerance

39. Timeouts configured for remote calls.
40. Retry policies implemented.
41. Circuit breakers used.
42. Bulkhead pattern applied.
43. Graceful degradation supported.
44. Partial failures handled.
45. Downstream dependency failures managed.
46. Fail-fast where appropriate.
47. Fallback responses implemented.
48. Idempotent retry handling ensured.
49. Rate limiting implemented.
50. Chaos testing performed.

## 6. Data Management & Consistency

51. Database-per-service model enforced.
52. No distributed ACID transactions across services.
53. Eventual consistency strategy defined.
54. Saga pattern used where necessary.
55. Data replication strategy defined.
56. Data schema versioning supported.
57. Backward-compatible schema evolution.
58. Data migration processes defined.
59. Cache invalidation strategy defined.
60. Data lineage documented.

## 7. Security Architecture

61. Authentication centralized (OAuth2/OIDC).
62. Authorization enforced per service.
63. Mutual TLS used for service-to-service calls.
64. API gateway implemented.
65. Data encrypted in transit.
66. Data encrypted at rest.
67. Secrets managed using a secure vault.
68. API rate limiting enforced.
69. Audit logging enabled.
70. Security scanning integrated into CI/CD.

## 8. Observability & Monitoring

71. Distributed tracing implemented.
72. Metrics exposed for monitoring.
73. Centralized logging implemented.
74. Correlation IDs propagated across services.
75. Health checks implemented.
76. Alerting configured.
77. Service Level Objectives (SLOs) defined.
78. Service Level Agreements (SLAs) documented.
79. Error budgets defined.
80. Operational runbooks available.

## 9. Scalability & Performance

81. Services stateless where possible.
82. Horizontal scaling supported.
83. Autoscaling configured.
84. Database scaling strategy defined.
85. Caching implemented where beneficial.
86. CDN used where appropriate.
87. Large payload responses avoided.
88. API response latency monitored.
89. Load testing performed.
90. Capacity planning documented.

## 10. CI/CD & Deployment

91. Fully automated CI/CD pipeline.
92. Infrastructure defined as code.
93. Blue/green deployment supported.
94. Canary deployment supported.
95. Rollback strategy defined.
96. Zero-downtime deployments supported.
97. Container images scanned for vulnerabilities.
98. Immutable deployments used.
99. Environment parity maintained.
100. Deployment audit trails maintained.

------------------------------------------------------------------------

## Common Red Flags (Deployment Blockers)

-   Shared database across multiple services
-   No observability or tracing
-   Missing retry/timeout strategy
-   Hardcoded service endpoints
-   No rollback deployment plan
-   No load testing performed
-   No API versioning strategy
