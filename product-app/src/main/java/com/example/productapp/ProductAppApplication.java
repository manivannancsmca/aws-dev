package com.example.productapp;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * Entry point of the product-app.
 * {@code @SpringBootApplication} enables auto-configuration and component scanning
 * for everything under the {@code com.example.productapp} package.
 */
@SpringBootApplication
public class ProductAppApplication {

    public static void main(String[] args) {
        SpringApplication.run(ProductAppApplication.class, args);
    }
}
