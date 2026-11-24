package com.example.productapp.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Digits;
import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;

/**
 * Request body for creating and updating a product.
 * A Java record is immutable and needs no getters/setters.
 * Validation annotations are checked automatically because the controller uses {@code @Valid}.
 */
@Schema(description = "Product data sent by the client")
public record ProductRequest(

        @Schema(description = "Product name", example = "Wireless Mouse", maxLength = 100)
        @NotBlank(message = "Name is required")
        @Size(max = 100, message = "Name must be at most 100 characters")
        String name,

        @Schema(description = "Optional product description", example = "Ergonomic 2.4 GHz wireless mouse", maxLength = 500)
        @Size(max = 500, message = "Description must be at most 500 characters")
        String description,

        @Schema(description = "Unit price (max 8 integer digits, 2 decimals)", example = "29.99")
        @NotNull(message = "Price is required")
        @DecimalMin(value = "0.00", message = "Price must be zero or positive")
        @Digits(integer = 8, fraction = 2, message = "Price must have at most 8 integer digits and 2 decimals")
        BigDecimal price,

        @Schema(description = "Units in stock", example = "150")
        @NotNull(message = "Quantity is required")
        @Min(value = 0, message = "Quantity must be zero or positive")
        Integer quantity
) {
}
