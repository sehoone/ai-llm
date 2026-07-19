package com.poc.vectorsearch.dto;

import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Data;
import lombok.NoArgsConstructor;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class ChunkMatch {
    private Long id;
    private Integer chunkIndex;
    private Integer chunkTotal;
    private String content;
    private double score;
}
