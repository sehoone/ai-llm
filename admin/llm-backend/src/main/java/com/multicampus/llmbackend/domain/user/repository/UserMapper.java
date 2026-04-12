package com.multicampus.llmbackend.domain.user.repository;

import com.multicampus.llmbackend.domain.user.dto.UserListItem;
import com.multicampus.llmbackend.domain.user.dto.UserSearchRequest;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

/**
 * 복잡한 동적 쿼리 / 페이징 조회에 MyBatis를 사용합니다.
 * 단순 CRUD는 JPA ({@link UserRepository})를 사용하세요.
 */
@Mapper
public interface UserMapper {

    /**
     * 동적 조건 검색 + 페이징
     */
    List<UserListItem> searchUsers(@Param("req") UserSearchRequest req);

    /**
     * 동적 조건 카운트 (페이징 total 계산용)
     */
    int countUsers(@Param("req") UserSearchRequest req);
}
