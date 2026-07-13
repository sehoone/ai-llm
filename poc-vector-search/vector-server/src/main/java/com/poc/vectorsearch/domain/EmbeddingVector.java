package com.poc.vectorsearch.domain;

import java.util.Arrays;
import java.util.List;

/**
 * pgvector 임베딩 벡터 값 객체.
 * float[] 대신 이 타입을 사용해 직렬화/역직렬화 로직을 한 곳에 집중시킨다.
 */
public class EmbeddingVector {

    private final float[] values;

    public EmbeddingVector(float[] values) {
        this.values = Arrays.copyOf(values, values.length);
    }

    /** OpenAI API 응답 data[0].embedding (List<Double>) → EmbeddingVector */
    public static EmbeddingVector from(List<Double> list) {
        float[] arr = new float[list.size()];
        for (int i = 0; i < list.size(); i++) {
            arr[i] = list.get(i).floatValue();
        }
        return new EmbeddingVector(arr);
    }

    /** pgvector 반환 문자열 "[0.1,-0.2,...]" → EmbeddingVector */
    public static EmbeddingVector parse(String pgString) {
        if (pgString == null || pgString.isEmpty()) {
            return null;
        }
        String trimmed = pgString.trim();
        if (trimmed.startsWith("[")) trimmed = trimmed.substring(1);
        if (trimmed.endsWith("]"))   trimmed = trimmed.substring(0, trimmed.length() - 1);

        String[] parts = trimmed.split(",");
        float[] arr = new float[parts.length];
        for (int i = 0; i < parts.length; i++) {
            arr[i] = Float.parseFloat(parts[i].trim());
        }
        return new EmbeddingVector(arr);
    }

    /** pgvector INSERT / 검색 파라미터용 문자열 "[0.1,-0.2,...]" */
    public String toPgVectorString() {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < values.length; i++) {
            sb.append(values[i]);
            if (i < values.length - 1) sb.append(",");
        }
        return sb.append("]").toString();
    }

    public int getDimension() {
        return values.length;
    }

    /** 내부 배열이 필요한 경우 방어적 복사본 반환 */
    public float[] getValues() {
        return Arrays.copyOf(values, values.length);
    }

    @Override
    public String toString() {
        return "EmbeddingVector{dimension=" + values.length + "}";
    }
}
