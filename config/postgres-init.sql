-- PostgreSQL initialization script for Chroma Vector Search

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- Metadata tables
CREATE TABLE IF NOT EXISTS collections (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    document_count INTEGER DEFAULT 0,
    file_count INTEGER DEFAULT 0,
    total_size_bytes BIGINT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS files (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    file_name VARCHAR(255) NOT NULL,
    file_extension VARCHAR(50),
    file_size_bytes BIGINT,
    language VARCHAR(50),
    line_count INTEGER,
    chunk_count INTEGER DEFAULT 0,
    indexed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP WITH TIME ZONE,
    metadata JSONB,
    UNIQUE(collection_id, file_path)
);

CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    file_id UUID REFERENCES files(id) ON DELETE CASCADE,
    chunk_id VARCHAR(255) NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    line_start INTEGER NOT NULL,
    line_end INTEGER NOT NULL,
    content_preview TEXT,
    embedding_dimension INTEGER,
    metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(file_id, chunk_id)
);

CREATE TABLE IF NOT EXISTS indexing_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    job_id VARCHAR(255) NOT NULL UNIQUE,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    progress FLOAT DEFAULT 0.0,
    total_files INTEGER DEFAULT 0,
    processed_files INTEGER DEFAULT 0,
    total_chunks INTEGER DEFAULT 0,
    processed_chunks INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    parameters JSONB
);

CREATE TABLE IF NOT EXISTS search_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    collection_id UUID REFERENCES collections(id) ON DELETE CASCADE,
    query TEXT NOT NULL,
    results_count INTEGER DEFAULT 0,
    processing_time_ms INTEGER,
    user_agent TEXT,
    client_ip INET,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_files_collection_id ON files(collection_id);
CREATE INDEX IF NOT EXISTS idx_files_file_path ON files(file_path);
CREATE INDEX IF NOT EXISTS idx_chunks_file_id ON chunks(file_id);
CREATE INDEX IF NOT EXISTS idx_chunks_content_hash ON chunks(content_hash);
CREATE INDEX IF NOT EXISTS idx_indexing_jobs_status ON indexing_jobs(status);
CREATE INDEX IF NOT EXISTS idx_indexing_jobs_collection_id ON indexing_jobs(collection_id);
CREATE INDEX IF NOT EXISTS idx_search_history_collection_id ON search_history(collection_id);
CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON search_history(created_at DESC);

-- Full-text search index for file paths
CREATE INDEX IF NOT EXISTS idx_files_file_path_gin ON files USING gin(file_path gin_trgm_ops);

-- Metadata indexes
CREATE INDEX IF NOT EXISTS idx_files_metadata ON files USING gin(metadata);
CREATE INDEX IF NOT EXISTS idx_chunks_metadata ON chunks USING gin(metadata);

-- Update triggers for timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_collections_updated_at 
    BEFORE UPDATE ON collections 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Statistics view
CREATE OR REPLACE VIEW collection_statistics AS
SELECT 
    c.id,
    c.name,
    c.document_count,
    c.file_count,
    c.total_size_bytes,
    c.created_at,
    c.updated_at,
    COUNT(DISTINCT f.language) as languages_count,
    COALESCE(SUM(f.chunk_count), 0) as total_chunks,
    COALESCE(AVG(f.line_count), 0) as avg_lines_per_file,
    COALESCE(AVG(f.file_size_bytes), 0) as avg_file_size_bytes
FROM collections c
LEFT JOIN files f ON c.id = f.collection_id
GROUP BY c.id, c.name, c.document_count, c.file_count, c.total_size_bytes, c.created_at, c.updated_at;

-- Insert default collection
INSERT INTO collections (name, description) 
VALUES ('codebase_vectors', 'Default collection for codebase vectors')
ON CONFLICT (name) DO NOTHING;