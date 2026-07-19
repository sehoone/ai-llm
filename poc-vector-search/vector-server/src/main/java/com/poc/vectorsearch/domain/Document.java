package com.poc.vectorsearch.domain;

import lombok.Data;

import java.time.LocalDateTime;

@Data
public class Document {
    private Long id;
    private String title;
    private String fullContent;
    private String sourceType;
    private String status;        // pending | processing | indexed | failed
    private String model;
    private String errorMessage;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
