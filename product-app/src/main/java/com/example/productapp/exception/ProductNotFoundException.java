package com.example.productapp.exception;

/**
 * Thrown by the service layer when a product ID does not exist.
 * Translated to HTTP 404 by {@link GlobalExceptionHandler}.
 */
public class ProductNotFoundException extends RuntimeException {

    public ProductNotFoundException(Long id) {
        super("Product not found with id: " + id);
    }
}
