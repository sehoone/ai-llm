package com.sehoon.platform.user.repository;

import com.sehoon.platform.user.domain.User;
import com.sehoon.platform.user.domain.UserStatus;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface UserRepository extends JpaRepository<User, Long> {
    Optional<User> findByEmail(String email);
    Optional<User> findByUsername(String username);
    boolean existsByEmail(String email);
    boolean existsByUsername(String username);
    long countByStatus(UserStatus status);
}
