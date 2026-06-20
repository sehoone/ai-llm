package com.sehoon.platform.common.audit;

import java.lang.annotation.ElementType;
import java.lang.annotation.Retention;
import java.lang.annotation.RetentionPolicy;
import java.lang.annotation.Target;

@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
public @interface Auditable {

    AuditAction action();

    String resourceType();

    /** 첫 번째 Long/String 인수를 resource_id로 사용할지 여부 */
    boolean captureFirstArgAsResourceId() default false;

    /** UPDATE/DELETE 시 변경 전 상태를 캡처할지 여부 */
    boolean captureOldValue() default false;
}
