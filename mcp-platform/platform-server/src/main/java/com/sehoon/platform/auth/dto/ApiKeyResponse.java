package com.sehoon.platform.auth.dto;

import com.sehoon.platform.auth.domain.ApiKey;

import java.time.LocalDateTime;

public record ApiKeyResponse(
        Long id,
        String name,
        String key,
        boolean isActive,
        LocalDateTime expiresAt,
        LocalDateTime createdAt,
        LocalDateTime lastUsedAt,
        long usageCount
) {
    public static ApiKeyResponse from(ApiKey apiKey) {
        return new ApiKeyResponse(
                apiKey.getId(),
                apiKey.getName(),
                apiKey.getKey(),
                apiKey.isActive(),
                apiKey.getExpiresAt(),
                apiKey.getCreatedAt(),
                apiKey.getLastUsedAt(),
                apiKey.getUsageCount()
        );
    }

    /** 목록 조회용 — key 마스킹 */
    public static ApiKeyResponse masked(ApiKey apiKey) {
        String masked = apiKey.getKey().substring(0, 8) + "****";
        return new ApiKeyResponse(
                apiKey.getId(),
                apiKey.getName(),
                masked,
                apiKey.isActive(),
                apiKey.getExpiresAt(),
                apiKey.getCreatedAt(),
                apiKey.getLastUsedAt(),
                apiKey.getUsageCount()
        );
    }
}
