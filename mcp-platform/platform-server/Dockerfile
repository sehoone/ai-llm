# ── Build stage ──────────────────────────────────────────────
FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /app

COPY gradle/ gradle/
COPY gradlew gradlew.bat settings.gradle build.gradle ./
RUN chmod +x gradlew

# 의존성 레이어 캐시
RUN ./gradlew dependencies --no-daemon -q || true

COPY src/ src/
RUN ./gradlew bootJar --no-daemon -x test

# ── Runtime stage ─────────────────────────────────────────────
FROM eclipse-temurin:21-jre-alpine AS runtime
WORKDIR /app

RUN apk add --no-cache curl
RUN addgroup -S platform && adduser -S platform -G platform
USER platform

COPY --from=builder /app/build/libs/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", \
  "-Djava.security.egd=file:/dev/./urandom", \
  "-XX:+UseContainerSupport", \
  "-XX:MaxRAMPercentage=75.0", \
  "-jar", "app.jar"]
