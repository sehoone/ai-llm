package com.multicampus.llmbackend.domain.user.dto;

import lombok.Getter;

import java.util.List;

@Getter
public class UserSearchResponse {

    private final List<UserListItem> items;
    private final int totalCount;
    private final int page;
    private final int size;

    private UserSearchResponse(List<UserListItem> items, int totalCount, int page, int size) {
        this.items = items;
        this.totalCount = totalCount;
        this.page = page;
        this.size = size;
    }

    public static UserSearchResponse of(List<UserListItem> items, int totalCount, UserSearchRequest req) {
        return new UserSearchResponse(items, totalCount, req.getPage(), req.getSize());
    }
}
