package com.poc.vectorsearch.service;

import com.knuddels.jtokkit.Encodings;
import com.knuddels.jtokkit.api.Encoding;
import com.knuddels.jtokkit.api.EncodingRegistry;
import com.knuddels.jtokkit.api.ModelType;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.regex.Pattern;

@Service
public class TextChunkingService {

    // text-embedding-3-small / ada-002 모두 cl100k_base 인코딩 사용
    private static final int DEFAULT_CHUNK_SIZE = 512;  // 토큰 기준
    private static final int DEFAULT_OVERLAP    = 100;  // 토큰 기준

    private static final String[] SEPARATORS = {"\n\n", "\n", "다. ", "요. ", "음. ", ". ", " "};

    private final Encoding encoding;

    public TextChunkingService() {
        EncodingRegistry registry = Encodings.newDefaultEncodingRegistry();
        this.encoding = registry.getEncodingForModel(ModelType.TEXT_EMBEDDING_ADA_002);
    }

    public List<String> chunk(String text) {
        return chunk(text, DEFAULT_CHUNK_SIZE, DEFAULT_OVERLAP);
    }

    public List<String> chunk(String text, int chunkSize, int overlap) {
        if (text == null || text.trim().isEmpty()) return Collections.emptyList();
        text = text.trim();
        if (countTokens(text) <= chunkSize) return Collections.singletonList(text);

        List<String> splits = getSplits(text, chunkSize);
        return mergeWithOverlap(splits, chunkSize, overlap);
    }

    private List<String> getSplits(String text, int chunkSize) {
        for (String sep : SEPARATORS) {
            if (!text.contains(sep)) continue;

            String[] rawParts = text.split(Pattern.quote(sep), -1);
            List<String> parts = new ArrayList<>();
            for (int i = 0; i < rawParts.length; i++) {
                String part = rawParts[i];
                if (part.isEmpty()) continue;
                parts.add(i < rawParts.length - 1 ? part + sep : part);
            }

            List<String> result = new ArrayList<>();
            for (String part : parts) {
                if (countTokens(part) > chunkSize) {
                    result.addAll(getSplits(part, chunkSize));
                } else {
                    result.add(part);
                }
            }
            return result;
        }

        // 구분자 분할 불가 시 이진 탐색으로 토큰 한도 내 최대 구간 탐색
        List<String> result = new ArrayList<>();
        int start = 0;
        while (start < text.length()) {
            int lo = start + 1, hi = text.length();
            while (lo < hi) {
                int mid = (lo + hi + 1) / 2;
                if (countTokens(text.substring(start, mid)) <= chunkSize) {
                    lo = mid;
                } else {
                    hi = mid - 1;
                }
            }
            result.add(text.substring(start, lo));
            start = lo;
        }
        return result;
    }

    private List<String> mergeWithOverlap(List<String> splits, int chunkSize, int overlap) {
        List<String> chunks = new ArrayList<>();
        StringBuilder current = new StringBuilder();

        for (String split : splits) {
            if (current.length() > 0 && countTokens(current.toString() + split) > chunkSize) {
                String chunk = current.toString().trim();
                if (!chunk.isEmpty()) chunks.add(chunk);

                current = new StringBuilder(getOverlapText(current.toString(), overlap));
            }
            current.append(split);
        }

        if (current.length() > 0) {
            String chunk = current.toString().trim();
            if (!chunk.isEmpty()) chunks.add(chunk);
        }

        return chunks;
    }

    /**
     * 현재 청크 끝에서 targetTokens 토큰에 해당하는 텍스트를 추출한다.
     * 이진 탐색으로 시작 위치를 찾고, \n 경계로 스냅하여 문장 중간 시작을 방지한다.
     */
    private String getOverlapText(String text, int targetTokens) {
        if (countTokens(text) <= targetTokens) return text;

        // 이진 탐색: text.substring(mid) 토큰 수 >= targetTokens 인 최대 mid (가장 뒤쪽 시작점)
        int lo = 0, hi = text.length();
        while (lo < hi) {
            int mid = (lo + hi + 1) / 2;
            if (countTokens(text.substring(mid)) >= targetTokens) {
                lo = mid;
            } else {
                hi = mid - 1;
            }
        }
        int start = lo;

        // \n 경계 스냅: 오버랩 전반부에 \n이 있으면 그 다음 줄부터 시작
        int newlinePos = text.indexOf('\n', start);
        if (newlinePos != -1 && newlinePos < start + (text.length() - start) / 2) {
            start = newlinePos + 1;
        }

        return text.substring(start);
    }

    private int countTokens(String text) {
        return encoding.countTokens(text);
    }
}
