package com.example.productapp.dto;

import io.swagger.v3.oas.annotations.media.Schema;

import java.math.BigDecimal;
import java.time.Instant;

/**
 * Response body returned to the client. We never expose the JPA entity directly,
 * so the API contract stays stable even if the database mapping changes.
 */
@Schema(description = "Product returned by the API")
public record ProductResponse(

        @Schema(description = "Generated product ID", example = "1")
        Long id,

        @Schema(description = "Product name", example = "Wireless Mouse")
        String name,

        @Schema(description = "Product description", example = "Ergonomic 2.4 GHz wireless mouse")
        String description,

        @Schema(description = "Unit price", example = "29.99")
        BigDecimal price,

        @Schema(description = "Units in stock", example = "150")
        Integer quantity,

        @Schema(description = "Creation timestamp (UTC)", example = "2026-01-15T10:30:00Z")
        Instant createdAt,

        @Schema(description = "Last update timestamp (UTC)", example = "2026-01-15T10:30:00Z")
        Instant updatedAt
) {
}
