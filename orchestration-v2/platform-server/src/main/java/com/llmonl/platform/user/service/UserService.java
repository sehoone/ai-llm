package com.llmonl.platform.user.service;

import com.llmonl.platform.common.exception.BusinessException;
import com.llmonl.platform.common.exception.ErrorCode;
import com.llmonl.platform.user.domain.User;
import com.llmonl.platform.user.dto.AdminUserCreateRequest;
import com.llmonl.platform.user.dto.AdminUserUpdateRequest;
import com.llmonl.platform.user.dto.UserResponse;
import com.llmonl.platform.user.dto.UserUpdateRequest;
import com.llmonl.platform.user.repository.UserRepository;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
@Transactional(readOnly = true)
public class UserService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    public UserService(UserRepository userRepository, PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
    }

    public UserResponse getUser(Long id) {
        return UserResponse.from(findUser(id));
    }

    public Page<UserResponse> getUsers(Pageable pageable) {
        return userRepository.findAll(pageable).map(UserResponse::from);
    }

    @Transactional
    public UserResponse updateUser(Long id, UserUpdateRequest request) {
        User user = findUser(id);

        if (request.email() != null && !request.email().equals(user.getEmail())) {
            if (userRepository.existsByEmail(request.email())) {
                throw new BusinessException(ErrorCode.EMAIL_ALREADY_EXISTS);
            }
        }
        if (request.username() != null && !request.username().equals(user.getUsername())) {
            if (userRepository.existsByUsername(request.username())) {
                throw new BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS);
            }
        }

        user.updateProfile(request.username(), request.email());
        return UserResponse.from(user);
    }

    @Transactional
    public void deactivateUser(Long id) {
        User user = findUser(id);
        user.deactivate();
    }

    @Transactional
    public UserResponse createUserByAdmin(AdminUserCreateRequest request) {
        if (userRepository.existsByEmail(request.email())) {
            throw new BusinessException(ErrorCode.EMAIL_ALREADY_EXISTS);
        }
        if (userRepository.existsByUsername(request.username())) {
            throw new BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS);
        }
        User user = new User(request.username(), request.email(),
                passwordEncoder.encode(request.password()));
        user.changeRole(request.role());
        return UserResponse.from(userRepository.save(user));
    }

    @Transactional
    public UserResponse updateUserByAdmin(Long id, AdminUserUpdateRequest request) {
        User user = findUser(id);

        if (request.email() != null && !request.email().equals(user.getEmail())) {
            if (userRepository.existsByEmail(request.email())) {
                throw new BusinessException(ErrorCode.EMAIL_ALREADY_EXISTS);
            }
        }
        if (request.username() != null && !request.username().equals(user.getUsername())) {
            if (userRepository.existsByUsername(request.username())) {
                throw new BusinessException(ErrorCode.USERNAME_ALREADY_EXISTS);
            }
        }

        user.updateProfile(request.username(), request.email());
        if (request.role() != null) user.changeRole(request.role());
        if (request.status() != null && request.status().equals("inactive")) user.deactivate();
        if (request.password() != null && !request.password().isBlank()) {
            user.changePassword(passwordEncoder.encode(request.password()));
        }
        return UserResponse.from(user);
    }

    private User findUser(Long id) {
        return userRepository.findById(id)
                .orElseThrow(() -> new BusinessException(ErrorCode.USER_NOT_FOUND));
    }
}
