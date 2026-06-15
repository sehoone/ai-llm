package com.example.mcpserver.global.security.apikey;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
public class ApiKeyAuthFilter extends OncePerRequestFilter {

    private static final String BEARER_PREFIX = "Bearer ";
    private static final long CACHE_TTL_MS = 5 * 60 * 1000L; // 5분

    private final RestClient restClient;
    private final ObjectMapper objectMapper;
    private final ConcurrentHashMap<String, CachedResult> cache = new ConcurrentHashMap<>();

    public ApiKeyAuthFilter(ApiKeyProperties props, ObjectMapper objectMapper) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(java.time.Duration.ofSeconds(3));
        factory.setReadTimeout(java.time.Duration.ofSeconds(5));
        this.restClient = RestClient.builder()
                .baseUrl(props.getPlatformUrl())
                .requestFactory(factory)
                .build();
        this.objectMapper = objectMapper;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String authHeader = request.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith(BEARER_PREFIX)) {
            chain.doFilter(request, response);
            return;
        }

        String apiKey = authHeader.substring(BEARER_PREFIX.length()).trim();

        ApiKeyInfo info = resolveApiKey(apiKey);
        if (info == null) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json;charset=UTF-8");
            objectMapper.writeValue(response.getWriter(), Map.of("error", "Unauthorized"));
            return;
        }

        var authorities = List.of(
                (org.springframework.security.core.GrantedAuthority)
                new SimpleGrantedAuthority("ROLE_" + info.role().toUpperCase().replace("-", "_"))
        );
        var auth = new UsernamePasswordAuthenticationToken(info.username(), null, authorities);
        SecurityContextHolder.getContext().setAuthentication(auth);
        log.debug("[ApiKey] authenticated: username={}, role={}", info.username(), info.role());

        chain.doFilter(request, response);
    }

    private ApiKeyInfo resolveApiKey(String apiKey) {
        CachedResult cached = cache.get(apiKey);
        if (cached != null && !cached.isExpired()) {
            return cached.info();
        }

        try {
            String body = restClient.post()
                    .uri("/api/v1/api-keys/validate")
                    .contentType(MediaType.APPLICATION_JSON)
                    .body(Map.of("key", apiKey))
                    .retrieve()
                    .body(String.class);

            JsonNode root = objectMapper.readTree(body);
            JsonNode data = root.get("data");
            if (data == null || data.isNull()) return null;

            ApiKeyInfo info = new ApiKeyInfo(
                    data.get("userId").asLong(),
                    data.get("username").asText(),
                    data.get("role").asText()
            );
            cache.put(apiKey, new CachedResult(info));
            return info;

        } catch (HttpClientErrorException e) {
            if (e.getStatusCode() == HttpStatus.UNAUTHORIZED) {
                cache.remove(apiKey);
                return null;
            }
            log.warn("[ApiKey] platform-server error: {}", e.getMessage());
            return null;
        } catch (Exception e) {
            log.warn("[ApiKey] validation failed: {}", e.getMessage());
            return null;
        }
    }

    record ApiKeyInfo(Long userId, String username, String role) {}

    record CachedResult(ApiKeyInfo info, long createdAt) {
        CachedResult(ApiKeyInfo info) {
            this(info, System.currentTimeMillis());
        }

        boolean isExpired() {
            return System.currentTimeMillis() - createdAt > CACHE_TTL_MS;
        }
    }
}
