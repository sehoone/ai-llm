package com.example.mcpserver.global.security;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Collections;
import java.util.List;

public class ApiKeyFilter extends OncePerRequestFilter {

    private static final String API_KEY_HEADER = "X-API-Key";
    private static final List<String> PUBLIC_PATHS = List.of(
            "/actuator/health", "/actuator/info", "/actuator/prometheus"
    );

    private final byte[] validApiKeyBytes;

    public ApiKeyFilter(String validApiKey) {
        this.validApiKeyBytes = validApiKey.getBytes(StandardCharsets.UTF_8);
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        String path = request.getRequestURI();
        return PUBLIC_PATHS.stream().anyMatch(path::startsWith);
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain filterChain)
            throws ServletException, IOException {
        String requestApiKey = request.getHeader(API_KEY_HEADER);
        if (isValidKey(requestApiKey)) {
            SecurityContextHolder.getContext().setAuthentication(
                    new UsernamePasswordAuthenticationToken("mcp-client", null, Collections.emptyList())
            );
            filterChain.doFilter(request, response);
        } else {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write("{\"error\":\"Unauthorized\"}");
        }
    }

    // 타이밍 공격 방지: 상수 시간 바이트 비교
    private boolean isValidKey(String requestKey) {
        if (requestKey == null) return false;
        byte[] requestKeyBytes = requestKey.getBytes(StandardCharsets.UTF_8);
        return MessageDigest.isEqual(validApiKeyBytes, requestKeyBytes);
    }
}
