package com.sehoon.platform.common.audit;

import jakarta.persistence.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

import java.time.OffsetDateTime;

@Entity
@Table(name = "audit_log", schema = "llmonl")
public class AuditLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "occurred_at", nullable = false, updatable = false)
    private OffsetDateTime occurredAt;

    @Column(name = "user_id")
    private Long userId;

    @Column(name = "user_ip", length = 45)
    private String userIp;

    @Column(name = "request_id", length = 36)
    private String requestId;

    @Column(name = "user_agent", length = 512)
    private String userAgent;

    @Column(name = "service", nullable = false, length = 20)
    private String service = "platform";

    @Enumerated(EnumType.STRING)
    @Column(name = "action", nullable = false, length = 30)
    private AuditAction action;

    @Column(name = "resource_type", nullable = false, length = 50)
    private String resourceType;

    @Column(name = "resource_id", length = 255)
    private String resourceId;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "old_value")
    private String oldValue;

    @JdbcTypeCode(SqlTypes.JSON)
    @Column(name = "new_value")
    private String newValue;

    @Column(name = "description", length = 500)
    private String description;

    @Column(name = "status", nullable = false, length = 10)
    private String status = "SUCCESS";

    @Column(name = "error_message", columnDefinition = "text")
    private String errorMessage;

    protected AuditLog() {}

    private AuditLog(Builder builder) {
        this.occurredAt = OffsetDateTime.now();
        this.userId = builder.userId;
        this.userIp = builder.userIp;
        this.requestId = builder.requestId;
        this.userAgent = builder.userAgent;
        this.action = builder.action;
        this.resourceType = builder.resourceType;
        this.resourceId = builder.resourceId;
        this.oldValue = builder.oldValue;
        this.newValue = builder.newValue;
        this.description = builder.description;
        this.status = builder.status;
        this.errorMessage = builder.errorMessage;
    }

    public static Builder builder() { return new Builder(); }

    public static class Builder {
        private Long userId;
        private String userIp;
        private String requestId;
        private String userAgent;
        private AuditAction action;
        private String resourceType;
        private String resourceId;
        private String oldValue;
        private String newValue;
        private String description;
        private String status = "SUCCESS";
        private String errorMessage;

        public Builder userId(Long v)       { this.userId = v; return this; }
        public Builder userIp(String v)     { this.userIp = v; return this; }
        public Builder requestId(String v)  { this.requestId = v; return this; }
        public Builder userAgent(String v)  { this.userAgent = v; return this; }
        public Builder action(AuditAction v){ this.action = v; return this; }
        public Builder resourceType(String v){ this.resourceType = v; return this; }
        public Builder resourceId(String v) { this.resourceId = v; return this; }
        public Builder oldValue(String v)   { this.oldValue = v; return this; }
        public Builder newValue(String v)   { this.newValue = v; return this; }
        public Builder description(String v){ this.description = v; return this; }
        public Builder failure(String msg)  { this.status = "FAILURE"; this.errorMessage = msg; return this; }
        public AuditLog build()             { return new AuditLog(this); }
    }

    // getters
    public Long getId() { return id; }
    public AuditAction getAction() { return action; }
    public String getResourceType() { return resourceType; }
    public String getResourceId() { return resourceId; }
    public Long getUserId() { return userId; }
    public String getUserIp() { return userIp; }
    public String getRequestId() { return requestId; }
    public String getStatus() { return status; }
    public String getErrorMessage() { return errorMessage; }
    public String getNewValue() { return newValue; }
    public String getOldValue() { return oldValue; }
}
