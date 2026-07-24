package com.poc.vectorsearch.service;

import com.poc.vectorsearch.domain.EmbeddingVector;
import com.poc.vectorsearch.dto.ChunkMatch;
import com.poc.vectorsearch.dto.ChunkResult;
import com.poc.vectorsearch.dto.SearchRequest;
import com.poc.vectorsearch.dto.SearchResult;
import com.poc.vectorsearch.mapper.DocumentChunkMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class SearchService {

    private final DocumentChunkMapper documentChunkMapper;
    private final OpenAiEmbeddingService openAiEmbeddingService;

    @Transactional(readOnly = true)
    public List<SearchResult> search(SearchRequest request) {
        log.info("벡터 검색 시작 - 쿼리: '{}', TopK: {}", request.getQuery(), request.getTopK());

        EmbeddingVector queryVector = openAiEmbeddingService.embed(request.getQuery());

        // topK * 10 으로 여유 있게 조회 → Java threshold 필터 후 topK 문서 보장
        // threshold는 DB WHERE가 아닌 Java에서 필터링 (WHERE 절 사용 시 HNSW 인덱스 미사용)
        int limit = request.getTopK() * 10;
        List<ChunkResult> allChunks = documentChunkMapper.searchChunks(
                queryVector, limit);
        List<ChunkResult> chunks = allChunks.stream()
                .filter(c -> c.getScore() >= request.getThreshold())
                .collect(Collectors.toList());

        // 문서 단위 집계 (LinkedHashMap: score DESC 순서 유지)
        // chunks가 score DESC 정렬이므로 문서의 첫 등장 = 해당 문서 최고 점수
        Map<Long, SearchResult> grouped = new LinkedHashMap<>();
        for (ChunkResult chunk : chunks) {
            grouped.computeIfAbsent(chunk.getDocumentId(), id ->
                    SearchResult.builder()
                            .documentId(id)
                            .title(chunk.getTitle())
                            .fullContent(chunk.getFullContent())
                            .score(chunk.getScore())
                            .createdAt(chunk.getCreatedAt())
                            .matchingChunks(new ArrayList<>())
                            .build()
            );
            grouped.get(chunk.getDocumentId()).getMatchingChunks().add(
                    ChunkMatch.builder()
                            .id(chunk.getId())
                            .chunkIndex(chunk.getChunkIndex())
                            .chunkTotal(chunk.getChunkTotal())
                            .content(chunk.getContent())
                            .score(chunk.getScore())
                            .build()
            );
        }

        // 문서별 최고 점수 기준 정렬 후 topK 제한
        List<SearchResult> results = grouped.values().stream()
                .sorted(Comparator.comparingDouble(SearchResult::getScore).reversed())
                .limit(request.getTopK())
                .collect(Collectors.toList());

        log.info("검색 완료 - 문서: {}건, 총 매칭 청크: {}개 (threshold: {})",
                results.size(), chunks.size(), request.getThreshold());
        return results;
    }
}
