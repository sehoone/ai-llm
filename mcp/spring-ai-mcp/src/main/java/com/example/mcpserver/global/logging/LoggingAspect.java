package com.example.mcpserver.global.logging;

import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.springframework.stereotype.Component;

@Slf4j
@Aspect
@Component
public class LoggingAspect {

    @Pointcut("@annotation(org.springframework.ai.tool.annotation.Tool)")
    private void toolMethods() {}

    @Around("toolMethods()")
    public Object logToolExecution(ProceedingJoinPoint pjp) throws Throwable {
        String name = pjp.getSignature().toShortString();
        int argCount = pjp.getArgs().length;
        long start = System.currentTimeMillis();

        // 파라미터 값은 로깅하지 않음 — PII/민감 데이터 유출 방지
        log.info("[TOOL] START {} | args.count={}", name, argCount);
        try {
            Object result = pjp.proceed();
            log.info("[TOOL] END   {} | elapsed={}ms", name, elapsed(start));
            return result;
        } catch (Exception e) {
            log.error("[TOOL] ERROR {} | elapsed={}ms | error={}", name, elapsed(start), e.getMessage(), e);
            throw e;
        }
    }

    private long elapsed(long start) {
        return System.currentTimeMillis() - start;
    }
}
