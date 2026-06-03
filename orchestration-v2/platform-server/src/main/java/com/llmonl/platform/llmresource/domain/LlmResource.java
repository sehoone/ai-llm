package com.llmonl.platform.llmresource.domain;

import com.llmonl.platform.common.domain.BaseEntity;
import jakarta.persistence.*;

@Entity
@Table(name = "llm_resource", schema = "llmonl")
public class LlmResource extends BaseEntity {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(nullable = false)
    private String name;

    /** "chat" | "embedding" */
    @Column(name = "resource_type", nullable = false)
    private String resourceType = "chat";

    @Column(name = "model_name")
    private String modelName;

    @Column(nullable = false)
    private String provider;

    @Column(name = "api_base", nullable = false)
    private String apiBase;

    @Column(name = "api_key", nullable = false)
    private String apiKey;

    @Column(name = "deployment_name")
    private String deploymentName;

    @Column(name = "api_version")
    private String apiVersion;

    private String region;

    @Column(nullable = false)
    private int priority = 0;

    @Column(nullable = false)
    private int weight = 1;

    @Column(name = "is_active", nullable = false)
    private boolean isActive = true;

    protected LlmResource() {}

    public LlmResource(String name, String resourceType, String modelName,
                       String provider, String apiBase, String apiKey,
                       String deploymentName, String apiVersion, String region,
                       int priority, int weight) {
        this.name = name;
        this.resourceType = resourceType;
        this.modelName = modelName;
        this.provider = provider;
        this.apiBase = apiBase;
        this.apiKey = apiKey;
        this.deploymentName = deploymentName;
        this.apiVersion = apiVersion;
        this.region = region;
        this.priority = priority;
        this.weight = weight;
    }

    public Long getId() { return id; }
    public String getName() { return name; }
    public String getResourceType() { return resourceType; }
    public String getModelName() { return modelName; }
    public String getProvider() { return provider; }
    public String getApiBase() { return apiBase; }
    public String getApiKey() { return apiKey; }
    public String getDeploymentName() { return deploymentName; }
    public String getApiVersion() { return apiVersion; }
    public String getRegion() { return region; }
    public int getPriority() { return priority; }
    public int getWeight() { return weight; }
    public boolean isActive() { return isActive; }

    public void update(String name, String modelName, String apiBase, String apiKey,
                       String deploymentName, String apiVersion, int priority, int weight) {
        if (name != null) this.name = name;
        if (modelName != null) this.modelName = modelName;
        if (apiBase != null) this.apiBase = apiBase;
        if (apiKey != null) this.apiKey = apiKey;
        if (deploymentName != null) this.deploymentName = deploymentName;
        if (apiVersion != null) this.apiVersion = apiVersion;
        this.priority = priority;
        this.weight = weight;
    }

    public void toggleActive() { this.isActive = !this.isActive; }
}
