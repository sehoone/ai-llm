package com.sehoon.platform.common.audit;

import jakarta.servlet.http.HttpServletRequest;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.context.request.RequestContextHolder;
import org.springframework.web.context.request.ServletRequestAttributes;

@Aspect
@Component
public class AuditAspect {

    private final AuditService auditService;

    public AuditAspect(AuditService auditService) {
        this.auditService = auditService;
    }

    @Around("@annotation(auditable)")
    public Object audit(ProceedingJoinPoint pjp, Auditable auditable) throws Throwable {
        Long userId = resolveUserId();
        HttpServletRequest request = resolveRequest();

        AuditLog.Builder builder = AuditLog.builder()
                .action(auditable.action())
                .resourceType(auditable.resourceType())
                .userId(userId)
                .userIp(request != null ? getClientIp(request) : null)
                .requestId(request != null ? request.getHeader("X-Request-ID") : null)
                .userAgent(request != null ? truncate(request.getHeader("User-Agent"), 512) : null);

        if (auditable.captureFirstArgAsResourceId()) {
            Object[] args = pjp.getArgs();
            if (args != null && args.length > 0 && args[0] != null) {
                builder.resourceId(args[0].toString());
            }
        }

        try {
            Object result = pjp.proceed();
            builder.newValue(AuditSerializer.toJson(result));
            resolveResourceId(builder, result);
            auditService.save(builder.build());
            return result;
        } catch (Throwable ex) {
            builder.failure(truncate(ex.getMessage(), 1000));
            auditService.save(builder.build());
            throw ex;
        }
    }

    private Long resolveUserId() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !auth.isAuthenticated()) return null;
        try {
            return Long.parseLong(auth.getPrincipal().toString());
        } catch (NumberFormatException e) {
            return null;
        }
    }

    private HttpServletRequest resolveRequest() {
        var attrs = RequestContextHolder.getRequestAttributes();
        if (attrs instanceof ServletRequestAttributes sra) {
            return sra.getRequest();
        }
        return null;
    }

    private String getClientIp(HttpServletRequest request) {
        String xff = request.getHeader("X-Forwarded-For");
        if (xff != null && !xff.isBlank()) {
            return xff.split(",")[0].trim();
        }
        return request.getRemoteAddr();
    }

    private void resolveResourceId(AuditLog.Builder builder, Object result) {
        if (result == null) return;
        for (String methodName : new String[]{"getId", "id"}) {
            try {
                var method = result.getClass().getMethod(methodName);
                Object id = method.invoke(result);
                if (id != null) {
                    builder.resourceId(id.toString());
                    return;
                }
            } catch (Exception ignored) {}
        }
    }

    private String truncate(String value, int maxLen) {
        if (value == null) return null;
        return value.length() > maxLen ? value.substring(0, maxLen) : value;
    }
}
