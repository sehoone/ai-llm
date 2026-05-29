package com.example.mcpserver.global.logging;

import lombok.extern.slf4j.Slf4j;
import org.aspectj.lang.ProceedingJoinPoint;
import org.aspectj.lang.annotation.Around;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Pointcut;
import org.springframework.stereotype.Component;

import java.util.Arrays;

@Slf4j
@Aspect
@Component
public class LoggingAspect {

    @Pointcut("@annotation(org.springframework.ai.tool.annotation.Tool)")
    private void toolMethods() {}

    @Around("toolMethods()")
    public Object logToolExecution(ProceedingJoinPoint pjp) throws Throwable {
        String name = pjp.getSignature().toShortString();
        Object[] args = pjp.getArgs();
        long start = System.currentTimeMillis();

        log.info("[TOOL] START {} | args={}", name, Arrays.toString(args));
        try {
            Object result = pjp.proceed();
            log.info("[TOOL] END   {} | elapsed={}ms | result={}", name, elapsed(start), summarize(result));
            return result;
        } catch (Exception e) {
            log.error("[TOOL] ERROR {} | elapsed={}ms | error={}", name, elapsed(start), e.getMessage(), e);
            throw e;
        }
    }

    private long elapsed(long start) {
        return System.currentTimeMillis() - start;
    }

    private String summarize(Object result) {
        if (result == null) return "null";
        String str = result.toString();
        return str.length() > 200 ? str.substring(0, 200) + "..." : str;
    }
}
