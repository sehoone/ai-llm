package com.poc.vectorsearch.dto;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class BulkEmbeddingResultItem {
    private Object id;        // 입력 파일의 원래 id
    private String title;
    private boolean success;
    private Long documentId;  // 생성된 DB id (성공 시)
    private String error;     // 실패 메시지 (실패 시)
}
