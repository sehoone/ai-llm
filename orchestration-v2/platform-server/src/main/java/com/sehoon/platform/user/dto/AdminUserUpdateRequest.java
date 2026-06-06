package com.sehoon.platform.user.dto;

import com.sehoon.platform.user.domain.UserRole;
import jakarta.validation.constraints.Email;
import jakarta.validation.constraints.Size;

public record AdminUserUpdateRequest(
        @Size(min = 2, max = 50)
        String username,

        @Email
        String email,

        UserRole role,

        String status,

        @Size(min = 8, max = 64)
        String password
) {}
