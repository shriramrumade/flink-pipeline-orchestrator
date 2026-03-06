# Java Spring Boot Code Review Checklist

## 1. Architecture & Design

-   [ ] Follows layered architecture (Controller → Service → Repository)
-   [ ] No business logic inside controllers
-   [ ] Single Responsibility Principle followed
-   [ ] Proper separation of concerns
-   [ ] DTOs used instead of exposing entities
-   [ ] No tight coupling between components
-   [ ] Appropriate design patterns used (Factory, Strategy, Builder
    etc.)
-   [ ] Controllers do not access database directly
-   [ ] Configuration separated using @Configuration / application.yml

------------------------------------------------------------------------

## 2. Code Quality

-   [ ] Code is readable and self-explanatory
-   [ ] Meaningful method and variable names
-   [ ] Methods ideally \< 40 lines
-   [ ] Classes not excessively large
-   [ ] DRY principle followed (no duplicate logic)
-   [ ] Proper use of Java 8+ features (Streams, Optional, Lambdas)
-   [ ] Avoid deep nesting and complex logic
-   [ ] Cyclomatic complexity reasonable

------------------------------------------------------------------------

## 3. Spring Boot Best Practices

-   [ ] Correct use of Spring annotations (@RestController, @Service,
    @Repository)
-   [ ] Constructor injection used instead of field injection
-   [ ] Proper use of @Transactional
-   [ ] Configuration properties handled correctly
-   [ ] No heavy logic in configuration classes
-   [ ] Global exception handling via @ControllerAdvice
-   [ ] Avoid unnecessary component scanning

------------------------------------------------------------------------

## 4. API Design

-   [ ] REST standards followed
-   [ ] Proper HTTP methods used (GET, POST, PUT, DELETE)
-   [ ] Proper HTTP response codes returned
-   [ ] Entities not returned directly (use DTOs)
-   [ ] Request validation implemented (@NotNull, @Email, etc.)
-   [ ] Pagination used for large result sets

------------------------------------------------------------------------

## 5. Security

-   [ ] No hardcoded credentials or secrets
-   [ ] Secrets stored in environment variables or secret managers
-   [ ] Input validation implemented
-   [ ] Protection against SQL injection and XSS
-   [ ] Spring Security configured correctly
-   [ ] Authorization checks present where required

------------------------------------------------------------------------

## 6. Exception Handling

-   [ ] Avoid catching generic Exception
-   [ ] Custom exceptions used where appropriate
-   [ ] Global exception handler implemented
-   [ ] Meaningful error messages returned

------------------------------------------------------------------------

## 7. Logging

-   [ ] Logging framework used (SLF4J / Logback)
-   [ ] Proper log levels (INFO, DEBUG, WARN, ERROR)
-   [ ] No System.out.println in code
-   [ ] Sensitive data not logged
-   [ ] Correlation IDs used for tracing requests

------------------------------------------------------------------------

## 8. Database & Persistence

-   [ ] JPA entities designed properly
-   [ ] Avoid N+1 query problems
-   [ ] Correct indexes present
-   [ ] Lazy vs Eager loading reviewed
-   [ ] Transactions handled properly
-   [ ] Queries optimized
-   [ ] Pagination used for large datasets

------------------------------------------------------------------------

## 9. Performance

-   [ ] Heavy processing not done in controllers
-   [ ] Expensive tasks handled asynchronously when needed
-   [ ] Caching used where beneficial (@Cacheable)
-   [ ] Avoid unnecessary database calls
-   [ ] Connection pooling configured (HikariCP)

------------------------------------------------------------------------

## 10. Testing

-   [ ] Unit tests added
-   [ ] Integration tests added where required
-   [ ] Edge cases tested
-   [ ] Failure scenarios tested
-   [ ] Clear test naming conventions
-   [ ] Proper mocking used

------------------------------------------------------------------------

## 11. Configuration & Environments

-   [ ] Environment-specific configuration not hardcoded
-   [ ] Spring profiles used (dev, test, prod)
-   [ ] External configuration supported
-   [ ] Feature flags used when needed

------------------------------------------------------------------------

## 12. Observability

-   [ ] Metrics exposed via Micrometer
-   [ ] Distributed tracing enabled (OpenTelemetry / Zipkin / Jaeger)
-   [ ] Health checks available (/actuator/health)
-   [ ] Monitoring dashboards configured

------------------------------------------------------------------------

## 13. Dependency Management

-   [ ] No unnecessary dependencies
-   [ ] Dependency versions managed centrally
-   [ ] Vulnerabilities checked (OWASP Dependency Check)

------------------------------------------------------------------------

## 14. Documentation

-   [ ] Code comments for complex logic
-   [ ] API documentation available (Swagger / OpenAPI)
-   [ ] README updated
-   [ ] Architecture or flow diagrams included if needed

------------------------------------------------------------------------

## 15. Git / PR Standards

-   [ ] PR size manageable
-   [ ] Meaningful commit messages
-   [ ] No dead/commented code
-   [ ] No debug leftovers
-   [ ] CI pipeline passing

------------------------------------------------------------------------

## 16. Production Readiness

-   [ ] Graceful shutdown supported
-   [ ] Timeouts configured
-   [ ] Retry mechanisms implemented
-   [ ] Circuit breakers used when required (Resilience4j)
-   [ ] Rate limiting applied if needed
