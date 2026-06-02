package com.example.mcpserver.global.security.local;

import org.springframework.core.convert.converter.Converter;
import org.springframework.security.authentication.AbstractAuthenticationToken;
import org.springframework.security.core.GrantedAuthority;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.jwt.Jwt;
import org.springframework.security.oauth2.server.resource.authentication.JwtAuthenticationToken;

import java.util.Collection;
import java.util.Collections;
import java.util.List;
import java.util.stream.Collectors;

/**
 * Local 모드 JWT → Spring Security GrantedAuthority 변환.
 * Local JWT 클레임 구조: { "roles": ["mcp-user"] }
 * Keycloak의 realm_access 구조와 다르므로 별도 컨버터를 사용한다.
 */
public class LocalJwtAuthConverter implements Converter<Jwt, AbstractAuthenticationToken> {

    @Override
    public AbstractAuthenticationToken convert(Jwt jwt) {
        List<String> roles = jwt.getClaimAsStringList("roles");
        if (roles == null) roles = Collections.emptyList();

        Collection<GrantedAuthority> authorities = roles.stream()
                .map(r -> new SimpleGrantedAuthority("ROLE_" + r.toUpperCase().replace("-", "_")))
                .collect(Collectors.toList());

        return new JwtAuthenticationToken(jwt, authorities, jwt.getSubject());
    }
}
