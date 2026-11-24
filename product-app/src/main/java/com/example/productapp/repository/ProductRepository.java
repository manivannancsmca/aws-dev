package com.example.productapp.repository;

import com.example.productapp.entity.Product;
import org.springframework.data.jpa.repository.JpaRepository;

/**
 * Spring Data JPA generates the implementation at runtime.
 * JpaRepository already provides save, findById, findAll, delete, existsById, count ...
 */
public interface ProductRepository extends JpaRepository<Product, Long> {
}
