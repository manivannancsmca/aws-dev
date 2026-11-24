package com.example.productapp.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import org.springframework.http.HttpStatus;

import java.time.Instant;
import java.util.Map;

/**
 * Standard error body returned by {@link com.example.productapp.exception.GlobalExceptionHandler}
 * for every error (400, 404, 500 ...). Having one shape for all errors makes clients simpler.
 */
@Schema(description = "Error details returned for failed requests")
public record ApiErrorResponse(

        @Schema(description = "When the error happened (UTC)", example = "2026-01-15T10:30:00Z")
        Instant timestamp,

        @Schema(description = "HTTP status code", example = "404")
        int status,

        @Schema(description = "HTTP status reason", example = "Not Found")
        String error,

        @Schema(description = "Human readable message", example = "Product not found with id: 99")
        String message,

        @Schema(description = "Request path", example = "/api/products/99")
        String path,

        @Schema(description = "Field-level validation errors (only present for 400 validation failures)",
                example = "{\"name\": \"Name is required\", \"price\": \"Price must be zero or positive\"}")
        Map<String, String> fieldErrors
) {

    public static ApiErrorResponse of(HttpStatus status, String message, String path) {
        return new ApiErrorResponse(Instant.now(), status.value(), status.getReasonPhrase(), message, path, null);
    }

    public static ApiErrorResponse of(HttpStatus status, String message, String path, Map<String, String> fieldErrors) {
        return new ApiErrorResponse(Instant.now(), status.value(), status.getReasonPhrase(), message, path, fieldErrors);
    }
}
