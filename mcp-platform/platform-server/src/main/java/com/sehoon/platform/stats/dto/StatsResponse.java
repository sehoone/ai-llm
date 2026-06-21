package com.sehoon.platform.stats.dto;

public record StatsResponse(
        long totalUsers,
        long activeUsers,
        long totalApiKeys,
        long activeApiKeys
) {}
