package com.poc.vectorsearch.service;

import com.poc.vectorsearch.domain.EmbeddingVector;
import com.poc.vectorsearch.dto.SearchRequest;
import com.poc.vectorsearch.dto.SearchResult;
import com.poc.vectorsearch.mapper.DocumentMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.List;

@Slf4j
@Service
@RequiredArgsConstructor
public class SearchService {

    private final DocumentMapper documentMapper;
    private final OpenAiEmbeddingService openAiEmbeddingService;

    public List<SearchResult> search(SearchRequest request) {
        log.info("벡터 검색 시작 - 쿼리: '{}', TopK: {}", request.getQuery(), request.getTopK());

        EmbeddingVector queryVector = openAiEmbeddingService.embed(request.getQuery());
        List<SearchResult> results = documentMapper.searchByVector(queryVector, request.getTopK(), request.getThreshold());

        log.info("검색 완료 - 결과 수: {} (threshold: {})", results.size(), request.getThreshold());
        return results;
    }
}
