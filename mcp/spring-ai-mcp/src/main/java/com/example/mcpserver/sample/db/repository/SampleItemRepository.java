package com.example.mcpserver.sample.db.repository;

import com.example.mcpserver.sample.db.entity.SampleItem;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface SampleItemRepository extends JpaRepository<SampleItem, Long> {

    List<SampleItem> findByNameContainingIgnoreCase(String name);
}
