package com.example.mcpserver.global.security;

import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;

/**
 * Spring Security 활성화 진입점.
 * 실제 SecurityFilterChain은 AUTH_MODE에 따라 조건부로 구성된다:
 *   AUTH_MODE=keycloak (기본) → KeycloakSecurityConfig
 *   AUTH_MODE=local           → local.LocalSecurityConfig
 */
@Configuration
@EnableWebSecurity
public class SecurityConfig {
}
