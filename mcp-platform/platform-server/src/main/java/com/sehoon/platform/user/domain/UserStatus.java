package com.sehoon.platform.user.domain;

import com.fasterxml.jackson.annotation.JsonValue;

public enum UserStatus {
    ACTIVE, INACTIVE;

    @JsonValue
    public String toJson() {
        return name().toLowerCase();
    }
}
