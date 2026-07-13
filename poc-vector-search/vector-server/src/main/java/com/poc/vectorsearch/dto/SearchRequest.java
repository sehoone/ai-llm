package com.poc.vectorsearch.dto;

import lombok.Data;

import javax.validation.constraints.Max;
import javax.validation.constraints.Min;
import javax.validation.constraints.NotBlank;

@Data
public class SearchRequest {
    @NotBlank
    private String query;

    @Min(1)
    @Max(20)
    private int topK = 5;
}
