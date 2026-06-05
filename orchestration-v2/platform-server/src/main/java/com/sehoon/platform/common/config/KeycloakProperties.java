package com.sehoon.platform.common.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "keycloak")
public class KeycloakProperties {

    private String serverUrl = "http://keycloak:8080";
    private String realm = "llm-platform";
    private String clientId = "orchestrator-app";
    private String clientSecret = "";
    private String adminUser = "admin";
    private String adminPassword = "admin";

    public String getServerUrl() { return serverUrl; }
    public void setServerUrl(String serverUrl) { this.serverUrl = serverUrl; }

    public String getRealm() { return realm; }
    public void setRealm(String realm) { this.realm = realm; }

    public String getClientId() { return clientId; }
    public void setClientId(String clientId) { this.clientId = clientId; }

    public String getClientSecret() { return clientSecret; }
    public void setClientSecret(String clientSecret) { this.clientSecret = clientSecret; }

    public String getAdminUser() { return adminUser; }
    public void setAdminUser(String adminUser) { this.adminUser = adminUser; }

    public String getAdminPassword() { return adminPassword; }
    public void setAdminPassword(String adminPassword) { this.adminPassword = adminPassword; }

    public String getTokenEndpoint() {
        return serverUrl + "/realms/" + realm + "/protocol/openid-connect/token";
    }

    public String getJwksUri() {
        return serverUrl + "/realms/" + realm + "/protocol/openid-connect/certs";
    }

    public String getIssuerUri() {
        return serverUrl + "/realms/" + realm;
    }
}
