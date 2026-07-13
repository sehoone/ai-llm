package com.poc.vectorsearch.service;

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

        float[] queryEmbedding = openAiEmbeddingService.embed(request.getQuery());
        String vectorString = buildVectorString(queryEmbedding);

        List<SearchResult> results = documentMapper.searchByVector(vectorString, request.getTopK());

        log.info("검색 완료 - 결과 수: {}", results.size());
        return results;
    }

    private String buildVectorString(float[] vector) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < vector.length; i++) {
            sb.append(vector[i]);
            if (i < vector.length - 1) {
                sb.append(",");
            }
        }
        sb.append("]");
        return sb.toString();
    }
}
