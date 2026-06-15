# Build stage
FROM eclipse-temurin:21-jdk-alpine AS builder
WORKDIR /app
COPY gradlew .
COPY gradle gradle
COPY build.gradle .
COPY settings.gradle .
COPY src src
RUN chmod +x gradlew && ./gradlew bootJar -x test

# Run stage
FROM eclipse-temurin:21-jre-alpine
RUN apk add --no-cache curl
RUN addgroup -S app && adduser -S app -G app
WORKDIR /app
RUN mkdir -p /app/logs && chown app:app /app/logs
COPY --from=builder /app/build/libs/*.jar app.jar
USER app
EXPOSE 8080
EXPOSE 8081
ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75.0", "-XX:+UseG1GC", "-jar", "app.jar"]
