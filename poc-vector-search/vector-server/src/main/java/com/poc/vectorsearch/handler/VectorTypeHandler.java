package com.poc.vectorsearch.handler;

import com.pgvector.PGvector;
import com.poc.vectorsearch.domain.EmbeddingVector;
import org.apache.ibatis.type.BaseTypeHandler;
import org.apache.ibatis.type.JdbcType;
import org.apache.ibatis.type.MappedTypes;

import java.sql.CallableStatement;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;

@MappedTypes(EmbeddingVector.class)
public class VectorTypeHandler extends BaseTypeHandler<EmbeddingVector> {

    @Override
    public void setNonNullParameter(PreparedStatement ps, int i, EmbeddingVector parameter, JdbcType jdbcType)
            throws SQLException {
        PGvector.addVectorType(ps.getConnection());
        ps.setObject(i, new PGvector(parameter.getValues()));
    }

    @Override
    public EmbeddingVector getNullableResult(ResultSet rs, String columnName) throws SQLException {
        return EmbeddingVector.parse(rs.getString(columnName));
    }

    @Override
    public EmbeddingVector getNullableResult(ResultSet rs, int columnIndex) throws SQLException {
        return EmbeddingVector.parse(rs.getString(columnIndex));
    }

    @Override
    public EmbeddingVector getNullableResult(CallableStatement cs, int columnIndex) throws SQLException {
        return EmbeddingVector.parse(cs.getString(columnIndex));
    }
}
