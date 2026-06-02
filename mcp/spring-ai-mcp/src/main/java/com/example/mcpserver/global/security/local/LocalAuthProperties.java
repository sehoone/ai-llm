package com.example.mcpserver.global.security.local;

import jakarta.annotation.PostConstruct;
import org.springframework.boot.context.properties.ConfigurationProperties;

import java.util.ArrayList;
import java.util.List;

/**
 * AUTH_MODE=local 일 때 바인딩되는 인증 설정.
 * LocalSecurityConfig 의 @EnableConfigurationProperties 로만 활성화된다.
 */
@ConfigurationProperties(prefix = "app.auth.local")
public class LocalAuthProperties {

    /** HMAC-SHA256 서명 키 — 최소 32자, LOCAL_JWT_SECRET 환경변수로 주입 */
    private String jwtSecret;

    /** 발급 토큰 유효시간 (초), 기본 3600 */
    private long jwtExpirationSeconds = 3600;

    /** 인증 가능한 사용자 목록 */
    private List<UserConfig> users = new ArrayList<>();

    @PostConstruct
    void validate() {
        if (jwtSecret == null || jwtSecret.isBlank() || jwtSecret.length() < 32) {
            throw new IllegalStateException(
                    "app.auth.local.jwt-secret (LOCAL_JWT_SECRET) must be at least 32 characters.");
        }
        if (users.isEmpty()) {
            throw new IllegalStateException(
                    "app.auth.local.users must contain at least one user.");
        }
        users.forEach(u -> {
            if (u.password() == null || u.password().isBlank()
                    || "change-me-in-production".equals(u.password())) {
                throw new IllegalStateException(
                        "Password for local user '" + u.username() + "' is not set or uses the default placeholder.");
            }
        });
    }

    public String getJwtSecret() { return jwtSecret; }
    public void setJwtSecret(String jwtSecret) { this.jwtSecret = jwtSecret; }

    public long getJwtExpirationSeconds() { return jwtExpirationSeconds; }
    public void setJwtExpirationSeconds(long jwtExpirationSeconds) { this.jwtExpirationSeconds = jwtExpirationSeconds; }

    public List<UserConfig> getUsers() { return users; }
    public void setUsers(List<UserConfig> users) { this.users = users; }

    public record UserConfig(String username, String password, List<String> roles) {}
}
