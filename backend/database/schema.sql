-- 통계이야기 프로젝트 SQLite 데이터베이스 스키마
-- 생성일: 2025-09-02
-- MCP-SQLite 서버와 함께 사용됨

-- === 통계 메타데이터 테이블 ===
CREATE TABLE IF NOT EXISTS stat_metadata (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    purpose TEXT,
    frequency TEXT,
    department TEXT,
    contact TEXT,
    keywords TEXT, -- JSON 배열로 저장
    related_terms TEXT, -- JSON 객체로 저장
    url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- === 통계 데이터 테이블 ===
CREATE TABLE IF NOT EXISTS stat_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metadata_id TEXT NOT NULL,
    year INTEGER NOT NULL,
    data_json TEXT NOT NULL, -- JSON 형태로 통계 데이터 저장
    collection_method TEXT DEFAULT 'MCP', -- 'MCP', 'Legacy', 'Manual'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (metadata_id) REFERENCES stat_metadata(id),
    UNIQUE(metadata_id, year) -- 같은 메타데이터의 같은 연도는 유일
);

-- === 크롤링 세션 테이블 ===
CREATE TABLE IF NOT EXISTS crawling_sessions (
    id TEXT PRIMARY KEY,
    session_name TEXT NOT NULL,
    start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    end_time DATETIME,
    status TEXT DEFAULT 'running', -- 'running', 'completed', 'failed'
    total_stats INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    error_details TEXT, -- JSON 배열
    mcp_servers_used TEXT, -- JSON 배열 (browser, filesystem, sqlite)
    notes TEXT
);

-- === AI 분석 결과 테이블 ===
CREATE TABLE IF NOT EXISTS ai_analyses (
    id TEXT PRIMARY KEY,
    metadata_id TEXT NOT NULL,
    analysis_type TEXT NOT NULL, -- 'basic', 'advanced', 'comprehensive'
    analysis_result TEXT NOT NULL, -- JSON 형태로 분석 결과 저장
    ai_model TEXT DEFAULT 'claude-3-sonnet',
    processing_time REAL, -- 초 단위
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (metadata_id) REFERENCES stat_metadata(id)
);

-- === 카드뉴스 생성 로그 테이블 ===
CREATE TABLE IF NOT EXISTS cardnews_generations (
    id TEXT PRIMARY KEY,
    analysis_id TEXT NOT NULL,
    cardnews_type TEXT NOT NULL, -- 'basic', 'advanced', 'comprehensive'
    cardnews_data TEXT NOT NULL, -- JSON 형태로 카드뉴스 데이터 저장
    generation_time REAL, -- 초 단위
    user_feedback TEXT, -- 'good', 'bad', 'neutral'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (analysis_id) REFERENCES ai_analyses(id)
);

-- === MCP 서버 상태 로그 테이블 ===
CREATE TABLE IF NOT EXISTS mcp_server_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    server_name TEXT NOT NULL, -- 'browser', 'filesystem', 'sqlite'
    action TEXT NOT NULL, -- 'start', 'stop', 'error', 'api_call'
    status TEXT NOT NULL, -- 'success', 'failed'
    details TEXT, -- JSON 형태로 상세 정보
    execution_time REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- === 사용자 세션 및 설정 테이블 ===
CREATE TABLE IF NOT EXISTS user_sessions (
    id TEXT PRIMARY KEY,
    session_data TEXT, -- JSON 형태로 세션 데이터
    last_activity DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- === 시스템 설정 테이블 ===
CREATE TABLE IF NOT EXISTS system_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- === 인덱스 생성 ===
CREATE INDEX IF NOT EXISTS idx_stat_data_metadata_year ON stat_data(metadata_id, year);
CREATE INDEX IF NOT EXISTS idx_stat_metadata_created ON stat_metadata(created_at);
CREATE INDEX IF NOT EXISTS idx_ai_analyses_type_created ON ai_analyses(analysis_type, created_at);
CREATE INDEX IF NOT EXISTS idx_crawling_sessions_status ON crawling_sessions(status, start_time);
CREATE INDEX IF NOT EXISTS idx_mcp_logs_server_created ON mcp_server_logs(server_name, created_at);

-- === 기본 시스템 설정 삽입 ===
INSERT OR IGNORE INTO system_settings (key, value, description) VALUES
('db_version', '1.0.0', '데이터베이스 스키마 버전'),
('mcp_enabled', 'true', 'MCP 서버 사용 여부'),
('default_analysis_type', 'basic', '기본 분석 유형'),
('max_crawling_sessions', '10', '최대 동시 크롤링 세션 수'),
('ai_model_name', 'claude-3-sonnet', '사용할 AI 모델'),
('data_retention_days', '365', '데이터 보관 기간 (일)'),
('auto_cleanup_enabled', 'true', '자동 정리 기능 사용 여부');

-- === 뷰 생성 ===
-- 통계 요약 뷰
CREATE VIEW IF NOT EXISTS stats_summary AS
SELECT 
    m.id,
    m.title,
    m.department,
    COUNT(DISTINCT d.year) as year_count,
    MIN(d.year) as earliest_year,
    MAX(d.year) as latest_year,
    COUNT(DISTINCT a.id) as analysis_count,
    m.created_at
FROM stat_metadata m
LEFT JOIN stat_data d ON m.id = d.metadata_id
LEFT JOIN ai_analyses a ON m.id = a.metadata_id
GROUP BY m.id, m.title, m.department, m.created_at;

-- MCP 서버 성능 뷰  
CREATE VIEW IF NOT EXISTS mcp_performance AS
SELECT 
    server_name,
    action,
    COUNT(*) as call_count,
    AVG(execution_time) as avg_execution_time,
    MAX(execution_time) as max_execution_time,
    SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as success_count,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failure_count,
    DATE(created_at) as log_date
FROM mcp_server_logs
GROUP BY server_name, action, DATE(created_at);

-- === 트리거 생성 ===
-- stat_metadata 업데이트 시간 자동 갱신
CREATE TRIGGER IF NOT EXISTS update_stat_metadata_timestamp
    AFTER UPDATE ON stat_metadata
    FOR EACH ROW
BEGIN
    UPDATE stat_metadata SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- === 샘플 데이터 삽입 (개발/테스트용) ===
INSERT OR IGNORE INTO stat_metadata (id, title, purpose, frequency, department, keywords, related_terms, url) VALUES
('sample_housing', '전국 주택 건설 현황', '주택 건설 동향 파악 및 정책 수립 지원', '월간', '국토교통부', 
 '["주택", "건설", "통계", "MCP"]', '{"건설": "Construction", "주택": "Housing"}', 
 'https://stat.molit.go.kr/portal/cate/statView.do?hMenuId=HMENU00158');

INSERT OR IGNORE INTO stat_data (metadata_id, year, data_json, collection_method) VALUES
('sample_housing', 2024, '{"전체": 400000, "서울": 50000, "경기": 120000, "기타": 230000}', 'MCP'),
('sample_housing', 2023, '{"전체": 380000, "서울": 48000, "경기": 115000, "기타": 217000}', 'MCP'),
('sample_housing', 2022, '{"전체": 360000, "서울": 45000, "경기": 110000, "기타": 205000}', 'MCP');

-- === 데이터베이스 정리 프로시저 (만료된 데이터 삭제) ===
-- SQLite에서는 저장 프로시저가 없으므로 주석으로 설명
-- 다음 쿼리를 주기적으로 실행하여 오래된 데이터 정리:
-- DELETE FROM mcp_server_logs WHERE created_at < datetime('now', '-90 days');
-- DELETE FROM user_sessions WHERE expires_at < datetime('now');
-- DELETE FROM crawling_sessions WHERE start_time < datetime('now', '-365 days') AND status = 'completed';