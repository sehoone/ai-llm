package com.sehoon.platform.common.exception;

import org.springframework.http.HttpStatus;

public enum ErrorCode {

    // Auth
    INVALID_CREDENTIALS(HttpStatus.UNAUTHORIZED, "이메일 또는 비밀번호가 올바르지 않습니다."),
    TOKEN_EXPIRED(HttpStatus.UNAUTHORIZED, "토큰이 만료되었습니다."),
    TOKEN_INVALID(HttpStatus.UNAUTHORIZED, "유효하지 않은 토큰입니다."),
    UNAUTHORIZED(HttpStatus.UNAUTHORIZED, "인증이 필요합니다."),
    FORBIDDEN(HttpStatus.FORBIDDEN, "접근 권한이 없습니다."),

    // User
    USER_NOT_FOUND(HttpStatus.NOT_FOUND, "사용자를 찾을 수 없습니다."),
    EMAIL_ALREADY_EXISTS(HttpStatus.CONFLICT, "이미 사용 중인 이메일입니다."),
    USERNAME_ALREADY_EXISTS(HttpStatus.CONFLICT, "이미 사용 중인 사용자명입니다."),

    // ApiKey
    API_KEY_NOT_FOUND(HttpStatus.NOT_FOUND, "API 키를 찾을 수 없습니다."),
    API_KEY_EXPIRED(HttpStatus.UNAUTHORIZED, "API 키가 만료되었습니다."),
    API_KEY_INACTIVE(HttpStatus.UNAUTHORIZED, "비활성화된 API 키입니다."),

    // Common
    INTERNAL_SERVER_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, "서버 내부 오류가 발생했습니다.");

    private final HttpStatus status;
    private final String message;

    ErrorCode(HttpStatus status, String message) {
        this.status = status;
        this.message = message;
    }

    public HttpStatus getStatus() { return status; }
    public String getMessage() { return message; }
}
