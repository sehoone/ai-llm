package com.multicampus.llmbackend.domain.user.dto;

import lombok.Builder;
import lombok.Getter;

/**
 * MyBatis 동적 쿼리용 사용자 검색 파라미터
 */
@Getter
@Builder
public class UserSearchRequest {

    private String email;       // LIKE 검색
    private String name;        // LIKE 검색
    private String role;        // 정확히 일치 (USER | ADMIN)

    @Builder.Default
    private int page = 0;

    @Builder.Default
    private int size = 20;

    public int getOffset() {
        return page * size;
    }
}
