package com.example.mcpserver.global.security.jwt;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "app.auth.jwt")
public class JwtProperties {

    /** HMAC-SHA256 서명 검증용 시크릿키 (Base64 인코딩) */
    private String secret;

    public String getSecret() { return secret; }
    public void setSecret(String secret) { this.secret = secret; }
}
