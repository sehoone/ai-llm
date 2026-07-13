package com.poc.vectorsearch.service;

import com.poc.vectorsearch.config.JwtConfig;
import com.poc.vectorsearch.domain.User;
import com.poc.vectorsearch.dto.LoginRequest;
import com.poc.vectorsearch.dto.LoginResponse;
import com.poc.vectorsearch.mapper.UserMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserMapper userMapper;
    private final JwtConfig jwtConfig;
    private final PasswordEncoder passwordEncoder;

    public LoginResponse login(LoginRequest request) {
        User user = userMapper.findByEmail(request.getEmail());
        if (user == null || !passwordEncoder.matches(request.getPassword(), user.getPassword())) {
            throw new IllegalArgumentException("이메일 또는 비밀번호가 올바르지 않습니다.");
        }

        String accessToken = jwtConfig.generateToken(user.getEmail(), user.getRole());
        // POC이므로 refreshToken은 accessToken과 동일하게 발급
        String refreshToken = jwtConfig.generateToken(user.getEmail(), user.getRole());

        return LoginResponse.builder()
                .accessToken(accessToken)
                .refreshToken(refreshToken)
                .tokenType("Bearer")
                .expiresIn(jwtConfig.getExpiration() / 1000)
                .user(LoginResponse.UserInfo.builder()
                        .id(user.getId())
                        .username(user.getUsername())
                        .email(user.getEmail())
                        .role(user.getRole())
                        .build())
                .build();
    }
}
