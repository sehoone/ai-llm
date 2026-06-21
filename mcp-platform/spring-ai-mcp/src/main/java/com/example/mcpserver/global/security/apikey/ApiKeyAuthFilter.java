package com.example.mcpserver.global.security.apikey;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.github.benmanes.caffeine.cache.Cache;
import com.github.benmanes.caffeine.cache.Caffeine;
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
import java.time.Duration;
import java.util.List;
import java.util.Map;

@Slf4j
public class ApiKeyAuthFilter extends OncePerRequestFilter {

    private static final String BEARER_PREFIX = "Bearer ";
    private static final String INTERNAL_SECRET_HEADER = "X-Internal-Secret";

    private final RestClient restClient;
    private final ObjectMapper objectMapper;
    private final String internalSecret;

    /** 최대 10,000개 항목 / 5분 만료 bounded cache */
    private final Cache<String, ApiKeyInfo> cache = Caffeine.newBuilder()
            .maximumSize(10_000)
            .expireAfterWrite(Duration.ofMinutes(5))
            .build();

    public ApiKeyAuthFilter(ApiKeyProperties props, ObjectMapper objectMapper) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(3));
        factory.setReadTimeout(Duration.ofSeconds(5));
        this.restClient = RestClient.builder()
                .baseUrl(props.getPlatformUrl())
                .requestFactory(factory)
                .build();
        this.objectMapper = objectMapper;
        this.internalSecret = props.getInternalSecret();
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
        ApiKeyInfo cached = cache.getIfPresent(apiKey);
        if (cached != null) return cached;

        try {
            String body = restClient.post()
                    .uri("/api/v1/api-keys/validate")
                    .contentType(MediaType.APPLICATION_JSON)
                    .headers(headers -> {
                        if (internalSecret != null && !internalSecret.isBlank()) {
                            headers.set(INTERNAL_SECRET_HEADER, internalSecret);
                        }
                    })
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
            cache.put(apiKey, info);
            return info;

        } catch (HttpClientErrorException e) {
            if (e.getStatusCode() == HttpStatus.UNAUTHORIZED) {
                cache.invalidate(apiKey);
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
}
