# syntax=docker/dockerfile:1
# =============================================================================
# Multi-stage build: the final image contains ONLY a JRE and the application,
# not Maven or the source code. The same image runs in Docker Compose and ECS.
# =============================================================================

# ---------- Stage 1: build the jar with Maven ----------
# The Java major version here and in stage 2 must match <java.version> in pom.xml (25)
FROM maven:3.9-eclipse-temurin-25-alpine AS build
WORKDIR /workspace

# Copy the POM first and download dependencies. Docker caches this layer, so
# dependencies are only re-downloaded when pom.xml changes.
# --mount=type=cache keeps the Maven repository between builds (BuildKit feature).
COPY pom.xml .
RUN --mount=type=cache,target=/root/.m2 mvn -B -q dependency:go-offline

# Now copy the sources and build. Tests run separately (mvn test) because the
# integration test needs Docker, which is not available inside a Docker build.
COPY src ./src
RUN --mount=type=cache,target=/root/.m2 mvn -B -q package -DskipTests

# Split the fat jar into layers: dependencies (change rarely) vs application
# classes (change often). This makes rebuilds and pushes to ECR much faster.
RUN java -Djarmode=tools -jar target/product-app.jar extract --layers --destination target/extracted

# ---------- Stage 2: minimal runtime image ----------
FROM eclipse-temurin:25-jre-alpine

# Install the newest Alpine security fixes: the base image can lag behind the Alpine repository.
# (The first ECR scan found a CRITICAL CVE in zlib 1.3.2-r1 while Alpine already offered a newer zlib.)
RUN apk upgrade --no-cache

# Run as a non-root user (security best practice)
RUN addgroup -S app && adduser -S app -G app
WORKDIR /app

# Copy layers in order from least to most frequently changing
COPY --from=build /workspace/target/extracted/dependencies/ ./
COPY --from=build /workspace/target/extracted/spring-boot-loader/ ./
COPY --from=build /workspace/target/extracted/snapshot-dependencies/ ./
COPY --from=build /workspace/target/extracted/application/ ./

USER app
EXPOSE 8080

# Docker-level health check (Docker Compose uses it; ECS uses the task definition's healthCheck)
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD wget -qO- http://localhost:8080/actuator/health || exit 1

# MaxRAMPercentage: let the JVM use 75% of the container's memory limit for the heap.
# Extra JVM flags can be added at runtime through the JAVA_TOOL_OPTIONS environment variable.
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75.0", "-jar", "product-app.jar"]
