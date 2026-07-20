package com.poc.vectorsearch.service;

import com.knuddels.jtokkit.Encodings;
import com.knuddels.jtokkit.api.Encoding;
import com.knuddels.jtokkit.api.EncodingRegistry;
import com.knuddels.jtokkit.api.ModelType;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * 텍스트를 토큰 한도 기준으로 청크로 분할한다.
 * 전략: . 또는 \n 단위로 세그먼트를 나눈 뒤, 토큰 합산이 maxTokens를 넘기 직전에 청크를 확정한다.
 */
@Service
public class TextChunkingService {

    private static final int DEFAULT_MAX_TOKENS = 1000;

    private final Encoding encoding;

    public TextChunkingService() {
        EncodingRegistry registry = Encodings.newDefaultEncodingRegistry();
        this.encoding = registry.getEncodingForModel(ModelType.TEXT_EMBEDDING_ADA_002);
    }

    public List<String> chunk(String text) {
        return chunk(text, DEFAULT_MAX_TOKENS);
    }

    public List<String> chunk(String text, int maxTokens) {
        if (text == null || text.trim().isEmpty()) return Collections.emptyList();
        text = text.trim();
        if (countTokens(text) <= maxTokens) return Collections.singletonList(text);

        List<String> segments = splitIntoSegments(text);
        List<String> chunks = new ArrayList<>();
        StringBuilder current = new StringBuilder();

        for (String segment : segments) {
            if (current.length() > 0 && countTokens(current.toString() + segment) > maxTokens) {
                chunks.add(current.toString().trim());
                current = new StringBuilder(segment);
            } else {
                current.append(segment);
            }
        }

        if (current.length() > 0) {
            String last = current.toString().trim();
            if (!last.isEmpty()) chunks.add(last);
        }

        return chunks;
    }

    // . 또는 \n 뒤에서 잘라 세그먼트 목록을 만든다. 구분자는 앞 세그먼트에 포함된다.
    private List<String> splitIntoSegments(String text) {
        List<String> segments = new ArrayList<>();
        int start = 0;
        for (int i = 0; i < text.length(); i++) {
            char c = text.charAt(i);
            if (c == '.' || c == '\n') {
                segments.add(text.substring(start, i + 1));
                start = i + 1;
            }
        }
        if (start < text.length()) {
            segments.add(text.substring(start));
        }
        return segments;
    }

    private int countTokens(String text) {
        return encoding.countTokens(text);
    }
}
