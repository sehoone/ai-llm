package com.example.mcpserver.global.security;

import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

import java.util.List;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    private static final List<String> PUBLIC_PATHS = List.of(
            "/actuator/health", "/actuator/info", "/actuator/prometheus"
    );

    @Value("${app.security.api-key}")
    private String apiKey;

    @PostConstruct
    void validateApiKey() {
        if (apiKey == null || apiKey.isBlank() || "change-me-in-production".equals(apiKey)) {
            throw new IllegalStateException(
                    "app.security.api-key is set to the default placeholder value. " +
                    "Set a secure API key via the API_KEY environment variable or profile config."
            );
        }
    }

    @Bean
    public SecurityFilterChain filterChain(HttpSecurity http) throws Exception {
        http
                .csrf(csrf -> csrf.disable())
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .addFilterBefore(new ApiKeyFilter(apiKey, PUBLIC_PATHS), UsernamePasswordAuthenticationFilter.class)
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(PUBLIC_PATHS.toArray(new String[0])).permitAll()
                        .anyRequest().authenticated()
                );
        return http.build();
    }
}
