package com.poc.vectorsearch.mapper;

import com.poc.vectorsearch.domain.User;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface UserMapper {
    User findByEmail(String email);
}
