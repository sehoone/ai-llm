package com.sehoon.platform.common.config;

import com.sehoon.platform.common.security.JwtAuthenticationFilter;
import com.sehoon.platform.common.security.KeycloakJwtAuthenticationConverter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configuration.WebSecurityCustomizer;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

@Configuration
@EnableWebSecurity
@EnableMethodSecurity
public class SecurityConfig {

    private final JwtAuthenticationFilter jwtAuthenticationFilter;
    private final KeycloakProperties keycloakProperties;

    @Value("${auth.mode:jwt}")
    private String authMode;

    public SecurityConfig(JwtAuthenticationFilter jwtAuthenticationFilter,
                          KeycloakProperties keycloakProperties) {
        this.jwtAuthenticationFilter = jwtAuthenticationFilter;
        this.keycloakProperties = keycloakProperties;
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
            .csrf(AbstractHttpConfigurer::disable)
            .sessionManagement(sm -> sm.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(auth -> auth
                    // 공개 엔드포인트
                    .requestMatchers(HttpMethod.POST,
                            "/api/v1/auth/register",
                            "/api/v1/auth/login",
                            "/api/v1/auth/refresh",
                            "/api/v1/auth/logout").permitAll()
                    .requestMatchers("/actuator/health", "/actuator/info").permitAll()
                    .requestMatchers("/swagger-ui.html", "/swagger-ui/**",
                            "/v3/api-docs", "/v3/api-docs/**").permitAll()
                    // 채팅 모델 목록 조회: 모든 인증 사용자
                    .requestMatchers(HttpMethod.GET, "/api/v1/llm-resources/chat-models").authenticated()
                    // LLM 리소스 관리: ADMIN 이상
                    .requestMatchers("/api/v1/llm-resources/**").hasAnyRole("ADMIN", "SUPERADMIN")
                    // 그 외 모두 인증 필요
                    .anyRequest().authenticated()
            );

        if ("keycloak".equals(authMode)) {
            // Keycloak RS256 토큰 검증 — JWKS 엔드포인트에서 공개키 자동 갱신
            http.oauth2ResourceServer(oauth2 -> oauth2
                    .jwt(jwt -> jwt
                            .jwkSetUri(keycloakProperties.getJwksUri())
                            .jwtAuthenticationConverter(new KeycloakJwtAuthenticationConverter())
                    )
            );
        } else {
            // 기존 HS256 JWT 필터
            http.addFilterBefore(jwtAuthenticationFilter, UsernamePasswordAuthenticationFilter.class);
        }

        return http.build();
    }

    @Bean
    public WebSecurityCustomizer webSecurityCustomizer() {
        return web -> web.ignoring()
                .requestMatchers("/swagger-ui.html", "/swagger-ui/**",
                        "/v3/api-docs", "/v3/api-docs/**");
    }

    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }
}
