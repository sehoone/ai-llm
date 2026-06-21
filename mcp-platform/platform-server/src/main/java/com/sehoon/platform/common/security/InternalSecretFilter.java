package com.sehoon.platform.common.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.Ordered;
import org.springframework.core.annotation.Order;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;
import java.util.Map;

/**
 * /api/v1/api-keys/validate 엔드포인트를 내부 서비스 전용으로 보호.
 * INTERNAL_SECRET 환경변수가 설정된 경우에만 활성화되며,
 * X-Internal-Secret 헤더가 일치하지 않으면 401을 반환한다.
 */
@Component
@Order(Ordered.HIGHEST_PRECEDENCE + 3)
public class InternalSecretFilter extends OncePerRequestFilter {

    private static final String VALIDATE_PATH = "/api/v1/api-keys/validate";
    private static final String HEADER_NAME = "X-Internal-Secret";

    private final String internalSecret;
    private final ObjectMapper objectMapper;

    public InternalSecretFilter(
            @Value("${app.internal-secret:}") String internalSecret,
            ObjectMapper objectMapper) {
        this.internalSecret = internalSecret;
        this.objectMapper = objectMapper;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        return internalSecret == null || internalSecret.isBlank()
                || !VALIDATE_PATH.equals(request.getRequestURI());
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String provided = request.getHeader(HEADER_NAME);
        if (!internalSecret.equals(provided)) {
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json;charset=UTF-8");
            objectMapper.writeValue(response.getWriter(),
                    Map.of("success", false, "message", "Internal secret required"));
            return;
        }
        chain.doFilter(request, response);
    }
}
