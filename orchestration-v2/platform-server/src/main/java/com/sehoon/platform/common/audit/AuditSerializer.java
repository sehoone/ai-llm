package com.sehoon.platform.common.audit;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;

import java.util.Map;
import java.util.Set;

public class AuditSerializer {

    private static final ObjectMapper MAPPER = new ObjectMapper();

    private static final Set<String> MASKED_FIELDS = Set.of(
            "hashedPassword", "hashed_password", "password",
            "token", "refreshToken", "refresh_token"
    );

    private AuditSerializer() {}

    public static String toJson(Object obj) {
        if (obj == null) return null;
        try {
            String json = MAPPER.writeValueAsString(obj);
            ObjectNode node = (ObjectNode) MAPPER.readTree(json);
            maskSensitiveFields(node);
            maskApiKey(node);
            return MAPPER.writeValueAsString(node);
        } catch (Exception e) {
            return "{\"error\":\"serialization_failed\"}";
        }
    }

    public static String toJson(Map<String, Object> map) {
        if (map == null) return null;
        try {
            ObjectNode node = MAPPER.valueToTree(map);
            maskSensitiveFields(node);
            maskApiKey(node);
            return MAPPER.writeValueAsString(node);
        } catch (Exception e) {
            return "{\"error\":\"serialization_failed\"}";
        }
    }

    private static void maskSensitiveFields(ObjectNode node) {
        MASKED_FIELDS.forEach(field -> {
            if (node.has(field)) {
                node.put(field, "[MASKED]");
            }
        });
    }

    private static void maskApiKey(ObjectNode node) {
        // api_key, apiKey 필드: 앞 7자 + **** 형태로 마스킹
        for (String field : new String[]{"key", "apiKey", "api_key"}) {
            if (node.has(field)) {
                String raw = node.get(field).asText();
                node.put(field, maskKey(raw));
            }
        }
    }

    private static String maskKey(String key) {
        if (key == null || key.length() <= 7) return "[MASKED]";
        return key.substring(0, 7) + "****";
    }
}
