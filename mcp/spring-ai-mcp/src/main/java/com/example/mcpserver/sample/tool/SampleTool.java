package com.example.mcpserver.sample.tool;

import lombok.extern.slf4j.Slf4j;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.ai.tool.annotation.ToolParam;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Duration;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;

/**
 * 6가지 MCP Tool 패턴을 한 파일에서 보여주는 독립 샘플.
 * 도메인별로 분리된 실제 구현(GreetingTool, ProductTool 등)의 축약 참고본.
 *
 * Case 1: 단순 문자열 반환          → sampleGreet
 * Case 2: 객체(Record) 반환         → sampleGetProduct
 * Case 3: 다중 파라미터             → sampleCreateOrder
 * Case 4: 외부 API 호출             → sampleGetTodo
 * Case 5: 입력값 검증 (문자열 반환) → sampleValidateAge
 * Case 6: InMemory CRUD             → sampleAddMemo, sampleGetMemo
 */
@Slf4j
@Component
public class SampleTool {

    // ── Case 4용 RestClient ──────────────────────────────────────────────────────
    private final RestClient restClient;

    // ── Case 6용 InMemory 저장소 ─────────────────────────────────────────────────
    private static final int MAX_MEMO_SIZE = 1_000;
    private final ConcurrentHashMap<String, String> memoStore = new ConcurrentHashMap<>();

    public SampleTool() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(3));
        factory.setReadTimeout(Duration.ofSeconds(5));
        this.restClient = RestClient.builder()
                .requestFactory(factory)
                .baseUrl("https://jsonplaceholder.typicode.com")
                .build();
    }

    // ── Case 1: 단순 문자열 반환 ──────────────────────────────────────────────────
    @Tool(description = "Returns a personalized greeting message for the given name")
    public String sampleGreet(
            @ToolParam(description = "Name of the person to greet") String name
    ) {
        if (name == null || name.isBlank()) {
            throw new IllegalArgumentException("name must not be blank");
        }
        log.info("sampleGreet called");
        return "Hello, " + name + "! (Sample Tool)";
    }

    // ── Case 2: 객체(Record) 반환 ─────────────────────────────────────────────────
    public record SampleProduct(String id, String name, BigDecimal price, int stock) {}

    @Tool(description = "Retrieves product information by product ID")
    public SampleProduct sampleGetProduct(
            @ToolParam(description = "Unique product ID to look up") String productId
    ) {
        if (productId == null || productId.isBlank()) {
            throw new IllegalArgumentException("productId must not be blank");
        }
        log.info("sampleGetProduct called: productId={}", productId);
        return new SampleProduct(productId, "Product-" + productId, new BigDecimal("29.99"), 100);
    }

    // ── Case 3: 다중 파라미터 ─────────────────────────────────────────────────────
    public record SampleOrder(String orderId, String productId, int quantity, boolean urgent,
                              BigDecimal totalPrice, String status) {}

    private static final BigDecimal UNIT_PRICE = new BigDecimal("29.99");
    private static final BigDecimal URGENT_SURCHARGE = new BigDecimal("1.2");

    @Tool(description = "Creates an order for a product with the specified quantity and urgency")
    public SampleOrder sampleCreateOrder(
            @ToolParam(description = "Product ID to order") String productId,
            @ToolParam(description = "Number of items to order (must be greater than 0)") int quantity,
            @ToolParam(description = "Set to true for urgent delivery (20% surcharge applies)") boolean urgent
    ) {
        if (productId == null || productId.isBlank()) {
            throw new IllegalArgumentException("productId must not be blank");
        }
        if (quantity <= 0) {
            throw new IllegalArgumentException("quantity must be greater than 0, provided: " + quantity);
        }
        log.info("sampleCreateOrder called: quantity={}, urgent={}", quantity, urgent);
        String orderId = "ORD-" + UUID.randomUUID().toString().replace("-", "").substring(0, 12).toUpperCase();
        BigDecimal surcharge = urgent ? URGENT_SURCHARGE : BigDecimal.ONE;
        BigDecimal totalPrice = UNIT_PRICE
                .multiply(BigDecimal.valueOf(quantity))
                .multiply(surcharge)
                .setScale(2, RoundingMode.HALF_UP);
        return new SampleOrder(orderId, productId, quantity, urgent, totalPrice, "CONFIRMED");
    }

    // ── Case 4: 외부 API 호출 ─────────────────────────────────────────────────────
    public record SampleTodo(int userId, int id, String title, boolean completed) {}

    @Tool(description = "Fetches a todo item from JSONPlaceholder public API by its ID")
    public SampleTodo sampleGetTodo(
            @ToolParam(description = "ID of the todo item to fetch (valid range: 1 to 200)") int id
    ) {
        if (id < 1 || id > 200) {
            throw new IllegalArgumentException("id must be between 1 and 200, provided: " + id);
        }
        log.info("sampleGetTodo called: id={}", id);
        try {
            SampleTodo result = restClient.get()
                    .uri("/todos/{id}", id)
                    .retrieve()
                    .body(SampleTodo.class);
            log.info("sampleGetTodo success: id={}", id);
            return result;
        } catch (Exception e) {
            log.error("sampleGetTodo failed: id={}, errorType={}", id, e.getClass().getSimpleName());
            throw new RuntimeException("Failed to fetch todo with id=" + id);
        }
    }

    // ── Case 5: 입력값 검증 (오류를 문자열로 반환) ───────────────────────────────
    private static final int MIN_AGE = 0;
    private static final int MAX_AGE = 150;

    @Tool(description = "Validates an age value and returns a categorized result or an error message if invalid")
    public String sampleValidateAge(
            @ToolParam(description = "Age value to validate (expected range: 0 to 150)") int age
    ) {
        log.info("sampleValidateAge called: age={}", age);
        if (age < MIN_AGE) return "Error: Age cannot be negative. Provided: " + age;
        if (age > MAX_AGE) return "Error: Age exceeds maximum (" + MAX_AGE + "). Provided: " + age;
        String category = age < 18 ? "minor" : age < 65 ? "adult" : "senior";
        return String.format("Valid age: %d (category: %s)", age, category);
    }

    // ── Case 6: InMemory CRUD ─────────────────────────────────────────────────────
    // 실제 운영에서는 별도 @Service Bean을 생성자 주입으로 받아야 한다.
    public record SampleMemo(String key, String content, String status) {}

    @Tool(description = "Saves a memo with the given key and content")
    public SampleMemo sampleAddMemo(
            @ToolParam(description = "Unique key to store the memo under (max 100 characters)") String key,
            @ToolParam(description = "Content of the memo to save (max 10,000 characters)") String content
    ) {
        if (key == null || key.isBlank()) throw new IllegalArgumentException("key must not be blank");
        if (key.length() > 100) throw new IllegalArgumentException("key must not exceed 100 characters");
        if (content == null || content.isBlank()) throw new IllegalArgumentException("content must not be blank");
        if (content.length() > 10_000) throw new IllegalArgumentException("content must not exceed 10,000 characters");
        if (!memoStore.containsKey(key) && memoStore.size() >= MAX_MEMO_SIZE) {
            throw new IllegalStateException("Memo storage is full (max " + MAX_MEMO_SIZE + " entries)");
        }
        memoStore.put(key, content);
        log.info("sampleAddMemo: key.length={}", key.length());
        return new SampleMemo(key, content, "SAVED");
    }

    @Tool(description = "Retrieves a previously saved memo by its key")
    public SampleMemo sampleGetMemo(
            @ToolParam(description = "Key of the memo to retrieve") String key
    ) {
        if (key == null || key.isBlank()) throw new IllegalArgumentException("key must not be blank");
        log.info("sampleGetMemo: key.length={}", key.length());
        String content = memoStore.get(key);
        return content != null
                ? new SampleMemo(key, content, "FOUND")
                : new SampleMemo(key, null, "NOT_FOUND");
    }
}
