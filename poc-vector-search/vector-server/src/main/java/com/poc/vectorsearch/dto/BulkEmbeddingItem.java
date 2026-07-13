package com.poc.vectorsearch.dto;

import lombok.Data;

import javax.validation.constraints.NotBlank;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Size;

@Data
public class BulkEmbeddingItem {
    @NotNull
    private Object id;  // 파일 내 참조용 ID (문자열/숫자 모두 허용)

    @NotBlank
    @Size(max = 500)
    private String title;

    @NotBlank
    private String desc;
}
