package com.example.mcpserver.global.security;

import jakarta.servlet.http.HttpServletResponse;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;

/**
 * AUTH_MODE=keycloak (기본값) 일 때 활성화.
 * Keycloak JWKS로 Bearer JWT를 검증하며 realm_access.roles → ROLE_MCP_USER 로 변환한다.
 */
@Configuration
@ConditionalOnProperty(name = "app.auth.mode", havingValue = "keycloak", matchIfMissing = true)
public class KeycloakSecurityConfig {

    private static final String[] PUBLIC_PATHS = {
            "/actuator/health", "/actuator/info", "/actuator/prometheus"
    };

    @Bean
    public SecurityFilterChain keycloakFilterChain(HttpSecurity http,
                                                    JwtAuthConverter jwtAuthConverter) throws Exception {
        http
                .csrf(csrf -> csrf.disable())
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(PUBLIC_PATHS).permitAll()
                        .anyRequest().authenticated()
                )
                .oauth2ResourceServer(oauth2 -> oauth2
                        .jwt(jwt -> jwt.jwtAuthenticationConverter(jwtAuthConverter))
                        .authenticationEntryPoint((req, res, ex) -> {
                            res.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                            res.setContentType("application/json;charset=UTF-8");
                            res.getWriter().write("{\"error\":\"Unauthorized\"}");
                        })
                );
        return http.build();
    }
}
