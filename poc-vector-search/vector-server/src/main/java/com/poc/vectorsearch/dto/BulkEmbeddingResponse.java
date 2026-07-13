package com.poc.vectorsearch.dto;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class BulkEmbeddingResponse {
    private int total;
    private int successCount;
    private int failedCount;
    private List<BulkEmbeddingResultItem> results;
}
