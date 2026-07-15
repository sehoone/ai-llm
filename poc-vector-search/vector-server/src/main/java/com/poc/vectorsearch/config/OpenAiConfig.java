package com.poc.vectorsearch.config;

import lombok.Getter;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestTemplate;

@Getter
@Configuration
public class OpenAiConfig {

    @Value("${azure.openai.api-key}")
    private String apiKey;

    /** https://{resource}.openai.azure.com */
    @Value("${azure.openai.endpoint}")
    private String endpoint;

    /** Azure에서 생성한 배포 이름 (예: text-embedding-3-small) */
    @Value("${azure.openai.deployment-name}")
    private String deploymentName;

    /** Azure OpenAI REST API 버전 (예: 2024-02-01) */
    @Value("${azure.openai.api-version}")
    private String apiVersion;

    /** 실제 호출 URL을 조합해서 반환 */
    public String getEmbeddingUrl() {
        return endpoint
                + "/openai/deployments/" + deploymentName
                + "/embeddings?api-version=" + apiVersion;
    }

    @Bean
    public RestTemplate restTemplate() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(3_000);
        factory.setReadTimeout(30_000);
        return new RestTemplate(factory);
    }
}
