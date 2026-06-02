package com.example.mcpserver.global.security.local;

import com.nimbusds.jose.JWSAlgorithm;
import com.nimbusds.jose.JWSHeader;
import com.nimbusds.jose.crypto.MACSigner;
import com.nimbusds.jwt.JWTClaimsSet;
import com.nimbusds.jwt.SignedJWT;
import lombok.extern.slf4j.Slf4j;

import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.List;

/**
 * Local 모드 JWT 생성기.
 * 토큰 클레임 구조: { "sub": username, "roles": [...], "iss": "spring-ai-mcp-local" }
 */
@Slf4j
public class LocalJwtProvider {

    private final MACSigner signer;
    private final long expirationSeconds;

    public LocalJwtProvider(String secret, long expirationSeconds) {
        try {
            this.signer = new MACSigner(secret.getBytes(StandardCharsets.UTF_8));
        } catch (Exception e) {
            throw new IllegalStateException("Failed to initialize local JWT signer: " + e.getMessage(), e);
        }
        this.expirationSeconds = expirationSeconds;
    }

    public String generateToken(String username, List<String> roles) {
        try {
            JWTClaimsSet claims = new JWTClaimsSet.Builder()
                    .issuer("spring-ai-mcp-local")
                    .subject(username)
                    .claim("roles", roles)
                    .issueTime(new Date())
                    .expirationTime(new Date(System.currentTimeMillis() + expirationSeconds * 1000))
                    .build();

            SignedJWT jwt = new SignedJWT(new JWSHeader(JWSAlgorithm.HS256), claims);
            jwt.sign(signer);
            return jwt.serialize();
        } catch (Exception e) {
            log.error("Failed to generate local JWT for user={}", username, e);
            throw new IllegalStateException("JWT generation failed", e);
        }
    }
}
