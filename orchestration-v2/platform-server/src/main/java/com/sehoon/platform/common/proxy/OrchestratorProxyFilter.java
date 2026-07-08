package com.sehoon.platform.common.proxy;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Enumeration;
import java.util.List;
import java.util.Set;

/**
 * platform-server 자신이 소유하지 않는 /api/* 경로를 orchestrator-server로 내부 프록시.
 *
 * 요청 흐름:
 *   Nginx → platform-server → (local) auth/users/api-keys/llm-resources 직접 처리
 *                           → (proxy) chatbot/rag/agents/workflow → orchestrator-server
 */
@Component
@Order(Ordered.LOWEST_PRECEDENCE - 10)
public class OrchestratorProxyFilter extends OncePerRequestFilter {

    private static final Logger log = LoggerFactory.getLogger(OrchestratorProxyFilter.class);

    // platform-server가 직접 처리하는 경로 — 이 경로는 프록시하지 않음
    private static final List<String> LOCAL_PREFIXES = List.of(
            "/api/v1/auth",
            "/api/v1/users",
            "/api/v1/api-keys",
            "/api/v1/llm-resources",
            "/actuator",
            "/swagger-ui",
            "/v3/api-docs"
    );

    // HTTP 스펙상 홉 단위 헤더 + Java HttpClient 제한 헤더 — 프록시 시 전달 금지
    private static final Set<String> HOP_BY_HOP_HEADERS = Set.of(
            "host",            // HttpClient가 URI 기반으로 자동 설정
            "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
            "te", "trailers", "transfer-encoding", "upgrade",
            "content-length"   // HttpClient가 바디 기반으로 재계산
    );

    private final String orchestratorBaseUrl;
    private final HttpClient httpClient;

    public OrchestratorProxyFilter(
            @Value("${orchestrator.base-url:http://app:8000}") String orchestratorBaseUrl) {
        this.orchestratorBaseUrl = orchestratorBaseUrl;
        this.httpClient = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(10))
                .version(HttpClient.Version.HTTP_1_1)
                .build();
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getRequestURI();
        return LOCAL_PREFIXES.stream().anyMatch(path::startsWith);
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain filterChain) throws ServletException, IOException {
        String path = request.getRequestURI();

        if (!path.startsWith("/api/")) {
            filterChain.doFilter(request, response);
            return;
        }

        proxy(request, response);
    }

    private void proxy(HttpServletRequest request, HttpServletResponse response) throws IOException {
        URI targetUri = buildTargetUri(request);
        log.debug("proxy {} → {}", request.getMethod(), targetUri);

        byte[] requestBody = request.getInputStream().readAllBytes();

        HttpRequest.Builder builder = HttpRequest.newBuilder()
                .uri(targetUri)
                .timeout(Duration.ofSeconds(120));

        // 요청 헤더 복사 (홉 단위 헤더 제외)
        Enumeration<String> headerNames = request.getHeaderNames();
        if (headerNames != null) {
            while (headerNames.hasMoreElements()) {
                String name = headerNames.nextElement();
                if (!HOP_BY_HOP_HEADERS.contains(name.toLowerCase())) {
                    try {
                        builder.header(name, request.getHeader(name));
                    } catch (IllegalArgumentException ignored) {
                        // Java HttpClient가 거부하는 헤더 무시
                    }
                }
            }
        }

        HttpRequest.BodyPublisher bodyPublisher = requestBody.length > 0
                ? HttpRequest.BodyPublishers.ofByteArray(requestBody)
                : HttpRequest.BodyPublishers.noBody();
        builder.method(request.getMethod(), bodyPublisher);

        try {
            HttpResponse<InputStream> proxyResponse = httpClient.send(
                    builder.build(), HttpResponse.BodyHandlers.ofInputStream());

            response.setStatus(proxyResponse.statusCode());

            // 응답 헤더 복사
            proxyResponse.headers().map().forEach((name, values) -> {
                if (!HOP_BY_HOP_HEADERS.contains(name.toLowerCase())) {
                    values.forEach(value -> response.addHeader(name, value));
                }
            });

            // 응답 바디 스트리밍 (NDJSON/SSE: 청크마다 즉시 flush)
            // transferTo는 Tomcat 버퍼가 찰 때까지 flush하지 않으므로
            // 소형 NDJSON 청크가 스트리밍 끝까지 지연되는 문제 방지
            response.flushBuffer();
            try (InputStream body = proxyResponse.body()) {
                byte[] buf = new byte[1024];
                int n;
                OutputStream out = response.getOutputStream();
                while ((n = body.read(buf)) != -1) {
                    out.write(buf, 0, n);
                    out.flush();
                }
            }

        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("orchestrator proxy timeout: {}", targetUri);
            response.setStatus(HttpServletResponse.SC_GATEWAY_TIMEOUT);
        } catch (Exception e) {
            log.error("orchestrator proxy error: {} {}", targetUri, e.getMessage());
            response.setStatus(HttpServletResponse.SC_BAD_GATEWAY);
        }
    }

    private URI buildTargetUri(HttpServletRequest request) {
        StringBuilder sb = new StringBuilder(orchestratorBaseUrl)
                .append(request.getRequestURI());
        String query = request.getQueryString();
        if (query != null && !query.isEmpty()) {
            sb.append("?").append(query);
        }
        return URI.create(sb.toString());
    }
}
