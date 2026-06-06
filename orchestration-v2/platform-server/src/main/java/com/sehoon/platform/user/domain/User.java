package com.sehoon.platform.user.domain;

import com.sehoon.platform.common.domain.BaseEntity;
import jakarta.persistence.*;

@Entity
@Table(
        name = "users",
        schema = "llmonl",
        uniqueConstraints = {
                @UniqueConstraint(columnNames = "username"),
                @UniqueConstraint(columnNames = "email")
        }
)
public class User extends BaseEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false, unique = true)
    private String username;

    @Column(nullable = false, unique = true)
    private String email;

    @Column(name = "hashed_password", nullable = false)
    private String hashedPassword;

    @Enumerated(EnumType.STRING)
    @Column(nullable = false)
    private UserRole role = UserRole.USER;

    @Column(nullable = false)
    private String status = "active";

    protected User() {}

    public User(String username, String email, String hashedPassword) {
        this.username = username;
        this.email = email;
        this.hashedPassword = hashedPassword;
    }

    public Long getId() { return id; }
    public String getUsername() { return username; }
    public String getEmail() { return email; }
    public String getHashedPassword() { return hashedPassword; }
    public UserRole getRole() { return role; }
    public String getStatus() { return status; }

    public void updateProfile(String username, String email) {
        if (username != null) this.username = username;
        if (email != null) this.email = email;
    }

    public void changePassword(String hashedPassword) {
        this.hashedPassword = hashedPassword;
    }

    public void changeRole(UserRole role) {
        this.role = role;
    }

    public void deactivate() {
        this.status = "inactive";
    }

    public boolean isActive() {
        return "active".equals(this.status);
    }
}
