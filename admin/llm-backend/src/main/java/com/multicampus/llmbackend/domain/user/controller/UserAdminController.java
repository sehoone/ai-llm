package com.multicampus.llmbackend.domain.user.controller;

import com.multicampus.llmbackend.domain.user.dto.UserSearchRequest;
import com.multicampus.llmbackend.domain.user.dto.UserSearchResponse;
import com.multicampus.llmbackend.domain.user.service.UserService;
import com.multicampus.llmbackend.global.response.ApiResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "User Admin", description = "사용자 관리 API (인증 필요)")
@RestController
@RequestMapping("/api/v1/users")
@RequiredArgsConstructor
public class UserAdminController {

    private final UserService userService;

    @Operation(summary = "사용자 목록 조회", description = "동적 조건 검색 및 페이징 (MyBatis)")
    @GetMapping
    public ApiResponse<UserSearchResponse> searchUsers(
            @RequestParam(required = false) String email,
            @RequestParam(required = false) String name,
            @RequestParam(required = false) String role,
            @RequestParam(defaultValue = "0") int page,
            @RequestParam(defaultValue = "20") int size) {

        UserSearchRequest req = UserSearchRequest.builder()
                .email(email)
                .name(name)
                .role(role)
                .page(page)
                .size(size)
                .build();

        return ApiResponse.success(userService.searchUsers(req));
    }
}
