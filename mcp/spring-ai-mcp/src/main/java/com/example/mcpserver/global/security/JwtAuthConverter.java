package com.example.mcpserver.global.security;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.convert.converter.Converter;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;
import org.springframework.stereotype.Component;

import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;
import java.util.stream.Stream;

/**
 * Keycloak JWT → Spring Security GrantedAuthority 변환.
 *
 * Keycloak은 roles를 두 위치에 담는다:
 *   realm_access.roles          → 모든 클라이언트에 공통적인 Realm 역할
 *   resource_access.<id>.roles  → 특정 클라이언트 전용 역할
 *
 * 두 위치를 모두 수집하여 ROLE_MCP_USER 형태로 변환한다.
 */
@Component
@org.springframework.boot.autoconfigure.condition.ConditionalOnProperty(
        name = "app.auth.mode", havingValue = "keycloak", matchIfMissing = true)
public class JwtAuthConverter implements Converter<Jwt, AbstractAuthenticationToken> {

    @Value("${app.security.jwt.resource-id:mcp-client}")
    private String resourceId;

    @Override
    public AbstractAuthenticationToken convert(Jwt jwt) {
        Collection<GrantedAuthority> authorities = Stream.concat(
                extractRealmRoles(jwt),
                extractResourceRoles(jwt)
        ).collect(Collectors.toSet());
        return new JwtAuthenticationToken(jwt, authorities, jwt.getSubject());
    }

    @SuppressWarnings("unchecked")
    private Stream<GrantedAuthority> extractRealmRoles(Jwt jwt) {
        Map<String, Object> realmAccess = jwt.getClaimAsMap("realm_access");
        if (realmAccess == null) return Stream.empty();
        List<String> roles = (List<String>) realmAccess.getOrDefault("roles", Collections.emptyList());
        return roles.stream()
                .map(r -> new SimpleGrantedAuthority("ROLE_" + r.toUpperCase().replace("-", "_")));
    }

    @SuppressWarnings("unchecked")
    private Stream<GrantedAuthority> extractResourceRoles(Jwt jwt) {
        Map<String, Object> resourceAccess = jwt.getClaimAsMap("resource_access");
        if (resourceAccess == null) return Stream.empty();
        Map<String, Object> client = (Map<String, Object>) resourceAccess.get(resourceId);
        if (client == null) return Stream.empty();
        List<String> roles = (List<String>) client.getOrDefault("roles", Collections.emptyList());
        return roles.stream()
                .map(r -> new SimpleGrantedAuthority("ROLE_" + r.toUpperCase().replace("-", "_")));
    }
}
