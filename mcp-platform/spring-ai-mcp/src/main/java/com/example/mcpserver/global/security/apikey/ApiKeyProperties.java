package com.example.mcpserver.global.security.apikey;

import org.springframework.boot.context.properties.ConfigurationProperties;

@ConfigurationProperties(prefix = "app.auth")
public class ApiKeyProperties {

    private String platformUrl;

    public String getPlatformUrl() { return platformUrl; }
    public void setPlatformUrl(String platformUrl) { this.platformUrl = platformUrl; }
}
