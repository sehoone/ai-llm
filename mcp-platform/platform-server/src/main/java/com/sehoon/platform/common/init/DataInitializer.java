package com.sehoon.platform.common.init;

import com.sehoon.platform.user.domain.User;
import com.sehoon.platform.user.domain.UserRole;
import com.sehoon.platform.user.repository.UserRepository;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.CommandLineRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

@Component
public class DataInitializer implements CommandLineRunner {

    private static final Logger log = LoggerFactory.getLogger(DataInitializer.class);

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;

    @Value("${app.init.superadmin.email:}")
    private String superadminEmail;

    @Value("${app.init.superadmin.username:superadmin}")
    private String superadminUsername;

    @Value("${app.init.superadmin.password:}")
    private String superadminPassword;

    public DataInitializer(UserRepository userRepository, PasswordEncoder passwordEncoder) {
        this.userRepository = userRepository;
        this.passwordEncoder = passwordEncoder;
    }

    @Override
    @Transactional
    public void run(String... args) {
        if (superadminEmail == null || superadminEmail.isBlank()) return;
        if (superadminPassword == null || superadminPassword.isBlank()) return;

        if (userRepository.existsByEmail(superadminEmail)) {
            log.debug("Superadmin already exists: {}", superadminEmail);
            return;
        }

        String username = (superadminUsername == null || superadminUsername.isBlank())
                ? "superadmin" : superadminUsername;

        User superadmin = new User(username, superadminEmail,
                passwordEncoder.encode(superadminPassword));
        superadmin.changeRole(UserRole.SUPERADMIN);
        userRepository.save(superadmin);
        log.info("Created initial SUPERADMIN: {}", superadminEmail);
    }
}
