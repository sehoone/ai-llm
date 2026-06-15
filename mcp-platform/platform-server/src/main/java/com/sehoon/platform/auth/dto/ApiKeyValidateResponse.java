package com.sehoon.platform.auth.dto;

public record ApiKeyValidateResponse(
        Long keyId,
        Long userId,
        String username,
        String role
) {}
