package com.example.mcpserver.sample.db.mapper;

import com.example.mcpserver.sample.db.entity.SampleItem;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

import java.util.List;

@Mapper
public interface SampleItemMapper {

    List<SampleItem> findAll(@Param("limit") int limit, @Param("offset") int offset);

    SampleItem findById(@Param("id") Long id);

    List<SampleItem> findByName(@Param("name") String name, @Param("limit") int limit);

    int insert(SampleItem item);

    int update(SampleItem item);

    int deleteById(@Param("id") Long id);
}
