package com.example.mcpserver.global.security.jwt;

import java.io.IOException;
import java.util.Base64;
import java.util.List;

import javax.crypto.SecretKey;

import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.JwtException;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.extern.slf4j.Slf4j;

@Slf4j
public class JwtAuthFilter extends OncePerRequestFilter {

    private static final String BEARER_PREFIX = "Bearer ";

    private final SecretKey signingKey;

    public JwtAuthFilter(JwtProperties props) {
        this.signingKey = Keys.hmacShaKeyFor(Base64.getDecoder().decode(props.getSecret()));
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
                                    FilterChain chain) throws ServletException, IOException {
        String authHeader = request.getHeader("Authorization");
        if (authHeader == null || !authHeader.startsWith(BEARER_PREFIX)) {
            chain.doFilter(request, response);
            return;
        }

        String token = authHeader.substring(BEARER_PREFIX.length()).trim();
        try {
            Claims claims = Jwts.parser()
                    .verifyWith(signingKey)
                    .build()
                    .parseSignedClaims(token)
                    .getPayload();

            String clientName = claims.getSubject();
            Object rawRoles = claims.get("roles");
            List<String> roles = (rawRoles instanceof List<?> list)
                    ? list.stream().map(Object::toString).toList()
                    : List.of();

            var authorities = roles.stream()
                    .map(r -> new SimpleGrantedAuthority("ROLE_" + r.toUpperCase().replace("-", "_")))
                    .map(a -> (org.springframework.security.core.GrantedAuthority) a)
                    .toList();

            var auth = new UsernamePasswordAuthenticationToken(clientName, null, authorities);
            SecurityContextHolder.getContext().setAuthentication(auth);
            log.debug("[JWT] authenticated: client={}, roles={}", clientName, roles);

        } catch (JwtException e) {
            log.warn("[JWT] invalid token: {}", e.getMessage());
            response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
            response.setContentType("application/json;charset=UTF-8");
            response.getWriter().write("{\"error\":\"Unauthorized\"}");
            return;
        }

        chain.doFilter(request, response);
    }
}
