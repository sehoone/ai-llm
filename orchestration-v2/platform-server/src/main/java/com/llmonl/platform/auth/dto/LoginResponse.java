package com.llmonl.platform.auth.dto;

import com.llmonl.platform.user.dto.UserResponse;

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
