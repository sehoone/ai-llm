FROM gradle:7.6.4-jdk8 AS builder
WORKDIR /app

COPY build.gradle settings.gradle ./
COPY src src

RUN gradle bootJar -x test --no-daemon

FROM eclipse-temurin:8-jre-alpine
WORKDIR /app

RUN addgroup -S spring && adduser -S spring -G spring
USER spring

COPY --from=builder /app/build/libs/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "app.jar"]
