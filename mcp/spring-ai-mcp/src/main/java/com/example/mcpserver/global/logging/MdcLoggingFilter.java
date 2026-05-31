package com.example.mcpserver.global.logging;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;
import org.slf4j.MDC;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.UUID;

@Slf4j
@Component
// ForwardedHeaderFilter(HIGHEST_PRECEDENCE) 이후에 실행되어 getRemoteAddr()가 올바른 IP를 반환하도록 +1
@Order(Ordered.HIGHEST_PRECEDENCE + 1)
public class MdcLoggingFilter extends OncePerRequestFilter {

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String requestId = UUID.randomUUID().toString().replace("-", "").substring(0, 12);
        MDC.put("requestId", requestId);
        MDC.put("uri", request.getRequestURI());
        MDC.put("method", request.getMethod());
        // server.forward-headers-strategy=FRAMEWORK 설정으로 Spring이 X-Forwarded-For를 처리
        MDC.put("clientIp", request.getRemoteAddr());

        long start = System.currentTimeMillis();
        try {
            log.info("[REQUEST]  {} {} from={}", request.getMethod(), request.getRequestURI(), MDC.get("clientIp"));
            chain.doFilter(request, response);
        } finally {
            log.info("[RESPONSE] status={} elapsed={}ms", response.getStatus(), System.currentTimeMillis() - start);
            MDC.clear();
        }
    }
}
