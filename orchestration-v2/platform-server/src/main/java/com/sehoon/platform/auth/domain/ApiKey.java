package com.sehoon.platform.auth.domain;

import com.sehoon.platform.common.domain.BaseEntity;
import jakarta.persistence.*;

import java.time.LocalDateTime;

@Entity
@Table(name = "api_key", schema = "llmonl")
public class ApiKey extends BaseEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "user_id", nullable = false)
    private Long userId;

    @Column(nullable = false, unique = true)
    private String key;

    @Column(nullable = false)
    private String name = "API Key";

    @Column(name = "expires_at")
    private LocalDateTime expiresAt;

    @Column(name = "is_active", nullable = false)
    private boolean isActive = true;

    protected ApiKey() {}

    public ApiKey(Long userId, String key, String name, LocalDateTime expiresAt) {
        this.userId = userId;
        this.key = key;
        this.name = name;
        this.expiresAt = expiresAt;
    }

    public Long getId() { return id; }
    public Long getUserId() { return userId; }
    public String getKey() { return key; }
    public String getName() { return name; }
    public LocalDateTime getExpiresAt() { return expiresAt; }
    public boolean isActive() { return isActive; }

    public boolean isExpired() {
        return expiresAt != null && expiresAt.isBefore(LocalDateTime.now());
    }

    public void deactivate() { this.isActive = false; }
}
