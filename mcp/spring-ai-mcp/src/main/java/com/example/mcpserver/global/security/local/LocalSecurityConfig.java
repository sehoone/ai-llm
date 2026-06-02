package com.example.mcpserver.global.security.local;

import jakarta.servlet.http.HttpServletResponse;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.factory.PasswordEncoderFactories;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.oauth2.jwt.NimbusJwtDecoder;
import org.springframework.security.web.SecurityFilterChain;

import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;

/**
 * AUTH_MODE=local 일 때 활성화.
 *
 * POST /auth/token → username/password 검증 → 자체 서명 JWT 발급
 * 이후 요청은 Authorization: Bearer <jwt> 로 인증한다.
 *
 * JWT 서명 알고리즘: HMAC-SHA256 (LOCAL_JWT_SECRET, 최소 32자)
 * JWT 클레임 구조: { "sub": username, "roles": [...], "iss": "spring-ai-mcp-local" }
 *
 * 비밀번호 인코딩: Spring Security DelegatingPasswordEncoder
 *   - {noop}plain-text  → 평문 비교 (개발용)
 *   - {bcrypt}$2a$10$.. → BCrypt (운영용)
 */
@Configuration
@ConditionalOnProperty(name = "app.auth.mode", havingValue = "local")
@EnableConfigurationProperties(LocalAuthProperties.class)
public class LocalSecurityConfig {

    private static final String[] PUBLIC_PATHS = {
            "/actuator/health", "/actuator/info", "/actuator/prometheus",
            "/auth/token"
    };

    /**
     * HMAC-SHA256 키로 자체 발급 JWT를 검증하는 디코더.
     * Spring Boot 자동구성의 Keycloak JwtDecoder보다 먼저 등록되어
     * @ConditionalOnMissingBean 조건에 의해 Keycloak 디코더 생성이 억제된다.
     */
    @Bean
    public NimbusJwtDecoder localJwtDecoder(LocalAuthProperties props) {
        SecretKeySpec key = new SecretKeySpec(
                props.getJwtSecret().getBytes(StandardCharsets.UTF_8), "HmacSHA256");
        return NimbusJwtDecoder.withSecretKey(key).build();
    }

    @Bean
    public LocalJwtProvider localJwtProvider(LocalAuthProperties props) {
        return new LocalJwtProvider(props.getJwtSecret(), props.getJwtExpirationSeconds());
    }

    @Bean
    public LocalJwtAuthConverter localJwtAuthConverter() {
        return new LocalJwtAuthConverter();
    }

    /** {noop}plain / {bcrypt}hash 모두 지원 */
    @Bean
    public PasswordEncoder passwordEncoder() {
        return PasswordEncoderFactories.createDelegatingPasswordEncoder();
    }

    @Bean
    public SecurityFilterChain localFilterChain(HttpSecurity http,
                                                 LocalJwtAuthConverter localJwtAuthConverter,
                                                 NimbusJwtDecoder localJwtDecoder) throws Exception {
        http
                .csrf(csrf -> csrf.disable())
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(PUBLIC_PATHS).permitAll()
                        .anyRequest().authenticated()
                )
                .oauth2ResourceServer(oauth2 -> oauth2
                        .jwt(jwt -> jwt
                                .decoder(localJwtDecoder)
                                .jwtAuthenticationConverter(localJwtAuthConverter))
                        .authenticationEntryPoint((req, res, ex) -> {
                            res.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                            res.setContentType("application/json;charset=UTF-8");
                            res.getWriter().write("{\"error\":\"Unauthorized\"}");
                        })
                );
        return http.build();
    }
}
