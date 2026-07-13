package com.poc.vectorsearch.service;

import com.poc.vectorsearch.config.OpenAiConfig;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Slf4j
@Service
@RequiredArgsConstructor
public class OpenAiEmbeddingService {

    private final RestTemplate restTemplate;
    private final OpenAiConfig openAiConfig;

    @SuppressWarnings("unchecked")
    public float[] embed(String text) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        // Azure OpenAI는 Bearer 대신 api-key 헤더 사용
        headers.set("api-key", openAiConfig.getApiKey());

        Map<String, Object> body = new HashMap<>();
        body.put("input", text);
        // Azure는 모델이 URL 경로(deployment)에 포함되므로 body에 불필요

        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);

        Map<String, Object> response = restTemplate.postForObject(
                openAiConfig.getEmbeddingUrl(), entity, Map.class);

        if (response == null) {
            throw new RuntimeException("Azure OpenAI API 응답이 없습니다.");
        }

        List<Map<String, Object>> data = (List<Map<String, Object>>) response.get("data");
        if (data == null || data.isEmpty()) {
            throw new RuntimeException("임베딩 데이터가 없습니다.");
        }

        List<Double> embeddingList = (List<Double>) data.get(0).get("embedding");
        float[] embedding = new float[embeddingList.size()];
        for (int i = 0; i < embeddingList.size(); i++) {
            embedding[i] = embeddingList.get(i).floatValue();
        }

        log.info("임베딩 생성 완료 - deployment: {}, 차원: {}",
                openAiConfig.getDeploymentName(), embedding.length);
        return embedding;
    }

    public String getModelName() {
        return openAiConfig.getDeploymentName();
    }
}
