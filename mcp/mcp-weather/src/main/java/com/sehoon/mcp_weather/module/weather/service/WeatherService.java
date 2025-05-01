package com.sehoon.mcp_weather.module.weather.service;

import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

@Service
public class WeatherService {

  private final RestClient restClient;

  public WeatherService() {
    this.restClient = RestClient.builder()
        .baseUrl("https://api.weather.gov")
        .defaultHeader("Accept", "application/geo+json")
        .defaultHeader("User-Agent", "WeatherApiClient/1.0 (your@email.com)")
        .build();
  }

  /**
   * 위도와 경도를 기반으로 날씨 정보 조회회
   * 
   * @param latitude
   * @param longitude
   * @return
   */
  @Tool(description = "Get weather forecast for a specific latitude/longitude. The precision of latitude/longitude points is limited to 4 decimal digits for efficiency.")
  public String getWeatherForecastByLocation(
      String latitude, // Latitude coordinate
      String longitude // Longitude coordinate
  ) {
    String endpoint = String.format("/points/%s,%s", latitude, longitude);
    try {
      String response = restClient.get()
          .uri(endpoint)
          .retrieve()
          .body(String.class);
      // You can use a library like Jackson or Gson for detailed parsing
      return response; // Return raw JSON or format it as needed
    } catch (Exception e) {
      // Handle exceptions (e.g., network issues, invalid responses)
      return "Error fetching weather forecast: " + e.getMessage();
    }
  }

  /**
   * 미국 주(state) 코드에 따라 날씨 경보 정보 조회
   * 
   * @param state
   * @return
   */
  @Tool(description = "Get weather alerts for a US state")
  public String getAlerts(
      @ToolParam(description = "Two-letter US state code (e.g. CA, NY)") String state) {
    String endpoint = String.format("/alerts/active?area=%s", state);
    try {
      // System.out.println("Fetching weather alerts for state: " + state);
      String response = restClient.get()
          .uri(endpoint)
          .retrieve()
          .body(String.class);
      // System.out.println("Response: " + response);
      // Parse the JSON response (simplified example)
      // You can use a library like Jackson or Gson for detailed parsing
      return response; // Return raw JSON or format it as needed
    } catch (Exception e) {
      // Handle exceptions (e.g., network issues, invalid responses)
      return "Error fetching weather alerts: " + e.getMessage();
    }
  }

}