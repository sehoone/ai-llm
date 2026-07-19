package com.poc.vectorsearch.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class SearchResult {
    private Long documentId;
    private String title;
    private String fullContent;
    private double score;                    // 매칭 청크 중 최고 유사도
    private LocalDateTime createdAt;
    private List<ChunkMatch> matchingChunks; // 임계값 통과한 청크 목록 (LLM 컨텍스트용)
}
