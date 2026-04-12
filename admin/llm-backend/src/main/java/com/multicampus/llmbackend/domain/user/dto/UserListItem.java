package com.multicampus.llmbackend.domain.user.dto;

import lombok.Getter;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;

/**
 * MyBatis ResultMap 매핑용 사용자 목록 조회 결과
 */
@Getter
@NoArgsConstructor
public class UserListItem {

    private Long id;
    private String email;
    private String name;
    private String role;
    private LocalDateTime createdAt;
}
