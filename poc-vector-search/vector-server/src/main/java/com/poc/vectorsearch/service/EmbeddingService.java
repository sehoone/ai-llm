package com.poc.vectorsearch.service;

import com.poc.vectorsearch.domain.Document;
import com.poc.vectorsearch.domain.DocumentStatus;
import com.poc.vectorsearch.dto.BulkEmbeddingItem;
import com.poc.vectorsearch.dto.BulkEmbeddingResponse;
import com.poc.vectorsearch.dto.BulkEmbeddingResultItem;
import com.poc.vectorsearch.dto.EmbeddingRequest;
import com.poc.vectorsearch.dto.EmbeddingResponse;
import com.poc.vectorsearch.dto.PageResponse;
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
    private final IndexingService indexingService;

    public EmbeddingResponse create(EmbeddingRequest request) {
        Document document = new Document();
        document.setTitle(request.getTitle());
        document.setFullContent(request.getContent());
        document.setSourceType("manual");
        document.setStatus(DocumentStatus.PENDING);

        documentMapper.insert(document);

        Document saved = documentMapper.findById(document.getId());
        log.info("문서 등록 완료 - ID: {}, 제목: {} (즉시 인덱싱 시작)", saved.getId(), saved.getTitle());

        indexingService.index(saved);

        return toResponse(documentMapper.findById(document.getId()));
    }

    public EmbeddingResponse retry(Long id) {
        Document document = documentMapper.findById(id);
        if (document == null) {
            throw new RuntimeException("문서를 찾을 수 없습니다: " + id);
        }
        if (!DocumentStatus.FAILED.equals(document.getStatus())) {
            throw new RuntimeException("failed 상태 문서만 재시도할 수 있습니다. 현재 상태: " + document.getStatus());
        }
        indexingService.index(document);
        Document saved = documentMapper.findById(id);
        log.info("문서 재시도 완료 - ID: {}", id);
        return toResponse(saved);
    }

    public PageResponse<EmbeddingResponse> findPaged(int page, int size) {
        long totalElements = documentMapper.countAll();
        int offset = page * size;
        List<EmbeddingResponse> content = documentMapper.findPaged(offset, size).stream()
                .map(this::toResponse)
                .collect(Collectors.toList());
        int totalPages = (int) Math.ceil((double) totalElements / size);
        return PageResponse.<EmbeddingResponse>builder()
                .content(content)
                .page(page)
                .size(size)
                .totalElements(totalElements)
                .totalPages(totalPages)
                .build();
    }

    public void delete(Long id) {
        documentMapper.deleteById(id);
        log.info("문서 삭제 완료 - ID: {} (청크 CASCADE 삭제)", id);
    }

    public void deleteAll() {
        documentMapper.deleteAll();
        log.info("전체 문서 삭제 완료");
    }

    public BulkEmbeddingResponse bulkCreate(List<BulkEmbeddingItem> items) {
        log.info("일괄 문서 등록 시작 - 총 {}건", items.size());

        List<BulkEmbeddingResultItem> results = new ArrayList<>();
        int successCount = 0;

        for (BulkEmbeddingItem item : items) {
            try {
                EmbeddingRequest req = new EmbeddingRequest();
                req.setTitle(item.getTitle());
                req.setContent(item.getDesc());
                EmbeddingResponse created = create(req);
                successCount++;

                results.add(BulkEmbeddingResultItem.builder()
                        .id(item.getId())
                        .title(item.getTitle())
                        .success(true)
                        .documentId(created.getId())
                        .build());
            } catch (Exception e) {
                log.error("문서 등록 실패 - 입력 ID: {}, 오류: {}", item.getId(), e.getMessage());
                results.add(BulkEmbeddingResultItem.builder()
                        .id(item.getId())
                        .title(item.getTitle())
                        .success(false)
                        .error(e.getMessage())
                        .build());
            }
        }

        log.info("일괄 문서 등록 완료 - 성공: {}, 실패: {}", successCount, items.size() - successCount);
        return BulkEmbeddingResponse.builder()
                .total(items.size())
                .successCount(successCount)
                .failedCount(items.size() - successCount)
                .results(results)
                .build();
    }

    private EmbeddingResponse toResponse(Document doc) {
        return EmbeddingResponse.builder()
                .id(doc.getId())
                .title(doc.getTitle())
                .content(doc.getFullContent())
                .sourceType(doc.getSourceType())
                .status(doc.getStatus())
                .model(doc.getModel())
                .errorMessage(doc.getErrorMessage())
                .createdAt(doc.getCreatedAt())
                .updatedAt(doc.getUpdatedAt())
                .build();
    }
}
