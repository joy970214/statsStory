"""
SQLite MCP Integration Service
데이터베이스 작업을 위한 MCP 통합 서비스
"""

import json
import logging
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

logger = logging.getLogger(__name__)

class SQLiteService:
    """SQLite MCP 통합 서비스"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(Path(__file__).parent.parent.parent / "data" / "statsStory.db")
        self.ensure_db_exists()
    
    def ensure_db_exists(self):
        """데이터베이스 파일 존재 확인"""
        db_file = Path(self.db_path)
        if not db_file.exists():
            logger.warning(f"Database not found at {self.db_path}")
            db_file.parent.mkdir(parents=True, exist_ok=True)
    
    def get_connection(self) -> sqlite3.Connection:
        """데이터베이스 연결 반환"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 딕셔너리 형태로 결과 반환
        return conn
    
    # === 통계 메타데이터 관리 ===
    async def save_stat_metadata(self, metadata: Dict[str, Any]) -> str:
        """통계 메타데이터 저장"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 키워드와 관련 용어를 JSON으로 변환
                keywords_json = json.dumps(metadata.get('keywords', []), ensure_ascii=False)
                related_terms_json = json.dumps(metadata.get('related_terms', {}), ensure_ascii=False)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO stat_metadata 
                    (id, title, purpose, frequency, department, contact, keywords, related_terms, url)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metadata['id'],
                    metadata.get('title'),
                    metadata.get('purpose'),
                    metadata.get('frequency'),
                    metadata.get('department'),
                    metadata.get('contact'),
                    keywords_json,
                    related_terms_json,
                    metadata.get('url')
                ))
                
                conn.commit()
                logger.info(f"Saved metadata: {metadata['id']}")
                return metadata['id']
                
        except Exception as e:
            logger.error(f"Error saving metadata: {e}")
            raise
    
    async def get_stat_metadata(self, metadata_id: str) -> Optional[Dict[str, Any]]:
        """통계 메타데이터 조회"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM stat_metadata WHERE id = ?", (metadata_id,))
                row = cursor.fetchone()
                
                if row:
                    result = dict(row)
                    # JSON 필드 파싱
                    if result.get('keywords'):
                        result['keywords'] = json.loads(result['keywords'])
                    if result.get('related_terms'):
                        result['related_terms'] = json.loads(result['related_terms'])
                    return result
                return None
                
        except Exception as e:
            logger.error(f"Error getting metadata: {e}")
            return None
    
    async def list_stat_metadata(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """통계 메타데이터 목록 조회"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM stat_metadata 
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """, (limit, offset))
                
                results = []
                for row in cursor.fetchall():
                    result = dict(row)
                    if result.get('keywords'):
                        result['keywords'] = json.loads(result['keywords'])
                    if result.get('related_terms'):
                        result['related_terms'] = json.loads(result['related_terms'])
                    results.append(result)
                
                return results
                
        except Exception as e:
            logger.error(f"Error listing metadata: {e}")
            return []
    
    # === 통계 데이터 관리 ===
    async def save_stat_data(self, metadata_id: str, year: int, data: Dict[str, Any], 
                           collection_method: str = "MCP") -> int:
        """통계 데이터 저장"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                data_json = json.dumps(data, ensure_ascii=False)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO stat_data 
                    (metadata_id, year, data_json, collection_method)
                    VALUES (?, ?, ?, ?)
                """, (metadata_id, year, data_json, collection_method))
                
                conn.commit()
                data_id = cursor.lastrowid
                logger.info(f"Saved stat data: {metadata_id}/{year} -> ID {data_id}")
                return data_id
                
        except Exception as e:
            logger.error(f"Error saving stat data: {e}")
            raise
    
    async def get_stat_data(self, metadata_id: str, year: Optional[int] = None) -> List[Dict[str, Any]]:
        """통계 데이터 조회"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if year:
                    cursor.execute("""
                        SELECT * FROM stat_data 
                        WHERE metadata_id = ? AND year = ?
                        ORDER BY year DESC
                    """, (metadata_id, year))
                else:
                    cursor.execute("""
                        SELECT * FROM stat_data 
                        WHERE metadata_id = ?
                        ORDER BY year DESC
                    """, (metadata_id,))
                
                results = []
                for row in cursor.fetchall():
                    result = dict(row)
                    if result.get('data_json'):
                        result['data'] = json.loads(result['data_json'])
                        del result['data_json']  # 원본 JSON 문자열 제거
                    results.append(result)
                
                return results
                
        except Exception as e:
            logger.error(f"Error getting stat data: {e}")
            return []
    
    # === AI 분석 결과 관리 ===
    async def save_ai_analysis(self, analysis_id: str, metadata_id: str, 
                             analysis_type: str, result: Dict[str, Any],
                             ai_model: str = "claude-3-sonnet",
                             processing_time: float = None) -> str:
        """AI 분석 결과 저장"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                result_json = json.dumps(result, ensure_ascii=False)
                
                cursor.execute("""
                    INSERT OR REPLACE INTO ai_analyses 
                    (id, metadata_id, analysis_type, analysis_result, ai_model, processing_time)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (analysis_id, metadata_id, analysis_type, result_json, ai_model, processing_time))
                
                conn.commit()
                logger.info(f"Saved AI analysis: {analysis_id}")
                return analysis_id
                
        except Exception as e:
            logger.error(f"Error saving AI analysis: {e}")
            raise
    
    async def get_ai_analysis(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """AI 분석 결과 조회"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM ai_analyses WHERE id = ?", (analysis_id,))
                row = cursor.fetchone()
                
                if row:
                    result = dict(row)
                    if result.get('analysis_result'):
                        result['analysis_result'] = json.loads(result['analysis_result'])
                    return result
                return None
                
        except Exception as e:
            logger.error(f"Error getting AI analysis: {e}")
            return None
    
    # === 크롤링 세션 관리 ===
    async def create_crawling_session(self, session_id: str, session_name: str) -> str:
        """크롤링 세션 생성"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO crawling_sessions (id, session_name, status)
                    VALUES (?, ?, 'running')
                """, (session_id, session_name))
                conn.commit()
                logger.info(f"Created crawling session: {session_id}")
                return session_id
                
        except Exception as e:
            logger.error(f"Error creating crawling session: {e}")
            raise
    
    async def update_crawling_session(self, session_id: str, **updates) -> bool:
        """크롤링 세션 업데이트"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 업데이트할 필드들 구성
                set_clause = []
                params = []
                
                for key, value in updates.items():
                    if key in ['status', 'total_stats', 'success_count', 'error_count', 
                              'error_details', 'mcp_servers_used', 'notes', 'end_time']:
                        set_clause.append(f"{key} = ?")
                        if key in ['error_details', 'mcp_servers_used'] and isinstance(value, (list, dict)):
                            params.append(json.dumps(value, ensure_ascii=False))
                        else:
                            params.append(value)
                
                if set_clause:
                    params.append(session_id)
                    query = f"UPDATE crawling_sessions SET {', '.join(set_clause)} WHERE id = ?"
                    cursor.execute(query, params)
                    conn.commit()
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error updating crawling session: {e}")
            return False
    
    # === MCP 서버 로그 관리 ===
    async def log_mcp_action(self, server_name: str, action: str, status: str,
                           details: Optional[Dict[str, Any]] = None,
                           execution_time: Optional[float] = None) -> int:
        """MCP 서버 액션 로그"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                details_json = json.dumps(details, ensure_ascii=False) if details else None
                
                cursor.execute("""
                    INSERT INTO mcp_server_logs 
                    (server_name, action, status, details, execution_time)
                    VALUES (?, ?, ?, ?, ?)
                """, (server_name, action, status, details_json, execution_time))
                
                conn.commit()
                log_id = cursor.lastrowid
                logger.debug(f"Logged MCP action: {server_name}/{action} -> {status}")
                return log_id
                
        except Exception as e:
            logger.error(f"Error logging MCP action: {e}")
            return 0
    
    # === 통계 및 분석 ===
    async def get_stats_summary(self) -> Dict[str, Any]:
        """통계 요약 정보"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 기본 통계
                cursor.execute("SELECT COUNT(*) as count FROM stat_metadata")
                metadata_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM stat_data")
                data_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count FROM ai_analyses")
                analysis_count = cursor.fetchone()['count']
                
                # 최근 활동
                cursor.execute("""
                    SELECT COUNT(*) as count FROM crawling_sessions 
                    WHERE start_time > datetime('now', '-7 days')
                """)
                recent_sessions = cursor.fetchone()['count']
                
                return {
                    'metadata_count': metadata_count,
                    'data_count': data_count,
                    'analysis_count': analysis_count,
                    'recent_crawling_sessions': recent_sessions,
                    'db_path': self.db_path,
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Error getting stats summary: {e}")
            return {'error': str(e)}
    
    async def search_metadata(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """메타데이터 검색"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # 제목, 목적, 부서, 키워드에서 검색
                search_query = f"%{query}%"
                cursor.execute("""
                    SELECT * FROM stat_metadata 
                    WHERE title LIKE ? OR purpose LIKE ? OR department LIKE ? OR keywords LIKE ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (search_query, search_query, search_query, search_query, limit))
                
                results = []
                for row in cursor.fetchall():
                    result = dict(row)
                    if result.get('keywords'):
                        result['keywords'] = json.loads(result['keywords'])
                    if result.get('related_terms'):
                        result['related_terms'] = json.loads(result['related_terms'])
                    results.append(result)
                
                return results
                
        except Exception as e:
            logger.error(f"Error searching metadata: {e}")
            return []

# 전역 인스턴스
_sqlite_service = None

def get_sqlite_service() -> SQLiteService:
    """SQLite 서비스 싱글톤 인스턴스 반환"""
    global _sqlite_service
    if _sqlite_service is None:
        _sqlite_service = SQLiteService()
    return _sqlite_service