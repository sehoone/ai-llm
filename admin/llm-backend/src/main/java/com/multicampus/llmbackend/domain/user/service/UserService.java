package com.multicampus.llmbackend.domain.user.service;

import com.multicampus.llmbackend.domain.user.dto.LoginRequest;
import com.multicampus.llmbackend.domain.user.dto.LoginResponse;
import com.multicampus.llmbackend.domain.user.dto.SignUpRequest;
import com.multicampus.llmbackend.domain.user.dto.SignUpResponse;
import com.multicampus.llmbackend.domain.user.dto.UserSearchRequest;
import com.multicampus.llmbackend.domain.user.dto.UserSearchResponse;
import com.multicampus.llmbackend.domain.user.entity.User;
import com.multicampus.llmbackend.domain.user.repository.UserMapper;
import com.multicampus.llmbackend.domain.user.repository.UserRepository;
import com.multicampus.llmbackend.global.exception.CustomException;
import com.multicampus.llmbackend.global.exception.ErrorCode;
import com.multicampus.llmbackend.global.jwt.JwtProvider;
import lombok.RequiredArgsConstructor;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class UserService {

    private final UserRepository userRepository;
    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;
    private final JwtProvider jwtProvider;

    @Transactional
    public SignUpResponse signUp(SignUpRequest request) {
        if (userRepository.existsByEmail(request.email())) {
            throw new CustomException(ErrorCode.DUPLICATE_EMAIL);
        }

        User user = User.builder()
                .email(request.email())
                .password(passwordEncoder.encode(request.password()))
                .name(request.name())
                .role(User.Role.USER)
                .build();

        return SignUpResponse.from(userRepository.save(user));
    }

    public LoginResponse login(LoginRequest request) {
        User user = userRepository.findByEmail(request.email())
                .orElseThrow(() -> new CustomException(ErrorCode.USER_NOT_FOUND));

        if (!passwordEncoder.matches(request.password(), user.getPassword())) {
            throw new CustomException(ErrorCode.INVALID_PASSWORD);
        }

        String accessToken = jwtProvider.generateAccessToken(user.getEmail(), user.getRole().name());
        String refreshToken = jwtProvider.generateRefreshToken(user.getEmail());

        return LoginResponse.of(accessToken, refreshToken);
    }

    public UserSearchResponse searchUsers(UserSearchRequest request) {
        var items = userMapper.searchUsers(request);
        int total = userMapper.countUsers(request);
        return UserSearchResponse.of(items, total, request);
    }
}
