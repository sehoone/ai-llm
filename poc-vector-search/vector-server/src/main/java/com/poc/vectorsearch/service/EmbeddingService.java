package com.poc.vectorsearch.service;

import com.poc.vectorsearch.domain.Document;
import com.poc.vectorsearch.domain.EmbeddingVector;
import com.poc.vectorsearch.dto.BulkEmbeddingItem;
import com.poc.vectorsearch.dto.BulkEmbeddingResponse;
import com.poc.vectorsearch.dto.BulkEmbeddingResultItem;
import com.poc.vectorsearch.dto.EmbeddingRequest;
import com.poc.vectorsearch.dto.EmbeddingResponse;
import com.poc.vectorsearch.mapper.DocumentMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class EmbeddingService {

    private final DocumentMapper documentMapper;
    private final OpenAiEmbeddingService openAiEmbeddingService;

    public EmbeddingResponse create(EmbeddingRequest request) {
        log.info("임베딩 생성 시작 - 제목: {}", request.getTitle());

        EmbeddingVector embedding = openAiEmbeddingService.embed(request.getContent());

        Document document = new Document();
        document.setTitle(request.getTitle());
        document.setContent(request.getContent());
        document.setEmbedding(embedding);
        document.setModel(openAiEmbeddingService.getModelName());

        documentMapper.insert(document);

        log.info("임베딩 저장 완료 - ID: {}", document.getId());

        return EmbeddingResponse.builder()
                .id(document.getId())
                .title(document.getTitle())
                .content(document.getContent())
                .model(document.getModel())
                .createdAt(document.getCreatedAt())
                .build();
    }

    public List<EmbeddingResponse> findAll() {
        return documentMapper.findAll().stream()
                .map(doc -> EmbeddingResponse.builder()
                        .id(doc.getId())
                        .title(doc.getTitle())
                        .content(doc.getContent())
                        .model(doc.getModel())
                        .createdAt(doc.getCreatedAt())
                        .build())
                .collect(Collectors.toList());
    }

    public void delete(Long id) {
        documentMapper.deleteById(id);
        log.info("문서 삭제 완료 - ID: {}", id);
    }

    public BulkEmbeddingResponse bulkCreate(List<BulkEmbeddingItem> items) {
        log.info("일괄 임베딩 시작 - 총 {}건", items.size());

        List<BulkEmbeddingResultItem> results = new ArrayList<>();
        int successCount = 0;

        for (BulkEmbeddingItem item : items) {
            try {
                EmbeddingVector embedding = openAiEmbeddingService.embed(item.getDesc());

                Document document = new Document();
                document.setTitle(item.getTitle());
                document.setContent(item.getDesc());
                document.setEmbedding(embedding);
                document.setModel(openAiEmbeddingService.getModelName());

                documentMapper.insert(document);
                successCount++;

                results.add(BulkEmbeddingResultItem.builder()
                        .id(item.getId())
                        .title(item.getTitle())
                        .success(true)
                        .documentId(document.getId())
                        .build());

                log.debug("일괄 임베딩 성공 - 입력 ID: {}, DB ID: {}", item.getId(), document.getId());
            } catch (Exception e) {
                log.error("일괄 임베딩 실패 - 입력 ID: {}, 오류: {}", item.getId(), e.getMessage());
                results.add(BulkEmbeddingResultItem.builder()
                        .id(item.getId())
                        .title(item.getTitle())
                        .success(false)
                        .error(e.getMessage())
                        .build());
            }
        }

        log.info("일괄 임베딩 완료 - 성공: {}, 실패: {}", successCount, items.size() - successCount);
        return BulkEmbeddingResponse.builder()
                .total(items.size())
                .successCount(successCount)
                .failedCount(items.size() - successCount)
                .results(results)
                .build();
    }
}
