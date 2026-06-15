package com.example.mcpserver.global.security;

import com.example.mcpserver.global.security.apikey.ApiKeyAuthFilter;
import com.example.mcpserver.global.security.apikey.ApiKeyProperties;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.servlet.http.HttpServletResponse;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.config.annotation.method.configuration.EnableMethodSecurity;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;

import java.util.Map;

@Configuration
@EnableWebSecurity
@EnableMethodSecurity
@EnableConfigurationProperties(ApiKeyProperties.class)
public class SecurityConfig {

    private static final String[] PUBLIC_PATHS = {
            "/actuator/health", "/actuator/info", "/actuator/prometheus"
    };

    @Bean
    public ApiKeyAuthFilter apiKeyAuthFilter(ApiKeyProperties props, ObjectMapper objectMapper) {
        return new ApiKeyAuthFilter(props, objectMapper);
    }

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http,
                                                    ApiKeyAuthFilter apiKeyAuthFilter,
                                                    ObjectMapper objectMapper) throws Exception {
        http
                .csrf(csrf -> csrf.disable())
                .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .addFilterBefore(apiKeyAuthFilter, UsernamePasswordAuthenticationFilter.class)
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(PUBLIC_PATHS).permitAll()
                        .anyRequest().authenticated()
                )
                .exceptionHandling(ex -> ex
                        .authenticationEntryPoint((req, res, e) -> {
                            res.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                            res.setContentType("application/json;charset=UTF-8");
                            objectMapper.writeValue(res.getWriter(), Map.of("error", "Unauthorized"));
                        })
                        .accessDeniedHandler((req, res, e) -> {
                            res.setStatus(HttpServletResponse.SC_FORBIDDEN);
                            res.setContentType("application/json;charset=UTF-8");
                            objectMapper.writeValue(res.getWriter(), Map.of("error", "Forbidden"));
                        })
                );
        return http.build();
    }
}
