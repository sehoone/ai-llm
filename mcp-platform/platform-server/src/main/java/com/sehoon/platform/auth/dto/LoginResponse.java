package com.sehoon.platform.auth.dto;

import com.sehoon.platform.user.dto.UserResponse;

public record LoginResponse(
        String accessToken,
        String refreshToken,
        String tokenType,
        long expiresIn,
        UserResponse user
) {
    public LoginResponse(String accessToken, String refreshToken, long expiresInSeconds, UserResponse user) {
        this(accessToken, refreshToken, "Bearer", expiresInSeconds, user);
    }
}
