package com.example.mcpserver.global.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.scheduling.annotation.Scheduled;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 2)
public class RateLimitFilter extends OncePerRequestFilter {

    private static final int MAX_REQUESTS = 60;
    private static final long WINDOW_MS = 60_000L;
    // 고유 IP 수를 제한해 OOM 방지: 한계 초과 시 해당 IP는 레이트 리밋 없이 통과
    private static final int MAX_BUCKET_ENTRIES = 100_000;

    // [requestCount, windowStartMs]
    private final ConcurrentHashMap<String, long[]> buckets = new ConcurrentHashMap<>();
    private final ObjectMapper objectMapper;

    public RateLimitFilter(ObjectMapper objectMapper) {
        this.objectMapper = objectMapper;
    }

    @Scheduled(fixedDelay = 300_000)
    void cleanup() {
        long stale = System.currentTimeMillis() - WINDOW_MS * 2;
        buckets.entrySet().removeIf(e -> e.getValue()[1] < stale);
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {

        String ip = request.getRemoteAddr();
        long now = System.currentTimeMillis();
        long[] bucket = buckets.computeIfAbsent(ip, k -> {
            if (buckets.size() < MAX_BUCKET_ENTRIES) {
                return new long[]{0L, now};
            }
            // 한계 초과 시 가장 오래된 항목 제거 후 신규 버킷 생성
            buckets.entrySet().stream()
                    .min(java.util.Comparator.comparingLong(e -> e.getValue()[1]))
                    .map(java.util.Map.Entry::getKey)
                    .ifPresent(buckets::remove);
            return new long[]{0L, now};
        });

        boolean allowed;
        synchronized (bucket) {
            if (now - bucket[1] >= WINDOW_MS) {
                bucket[0] = 1;
                bucket[1] = now;
                allowed = true;
            } else if (bucket[0] < MAX_REQUESTS) {
                bucket[0]++;
                allowed = true;
            } else {
                allowed = false;
            }
        }

        if (allowed) {
            chain.doFilter(request, response);
        } else {
            response.setStatus(429);
            response.setContentType("application/json;charset=UTF-8");
            objectMapper.writeValue(response.getWriter(), Map.of("error", "Too Many Requests"));
        }
    }
}
