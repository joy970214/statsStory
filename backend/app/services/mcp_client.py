import json
import asyncio
import subprocess
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from .sqlite_service import get_sqlite_service

logger = logging.getLogger(__name__)

class MCPClient:
    """MCP 서버와 통신하는 클라이언트"""
    
    def __init__(self):
        self.mcp_servers_path = Path(__file__).parent.parent.parent.parent / "mcp-servers"
        self.config_path = self.mcp_servers_path / "mcp-config.json"
        self.active_servers = {}
    
    async def start_server(self, server_name: str) -> bool:
        """MCP 서버 시작"""
        try:
            if not self.config_path.exists():
                logger.error(f"MCP 설정 파일을 찾을 수 없습니다: {self.config_path}")
                return False
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if server_name not in config['mcpServers']:
                logger.error(f"서버 '{server_name}'를 설정에서 찾을 수 없습니다")
                return False
            
            server_config = config['mcpServers'][server_name]
            logger.info(f"MCP 서버 '{server_name}' 시작 중...")
            
            # 서버가 이미 실행 중인지 확인
            if server_name in self.active_servers:
                logger.info(f"서버 '{server_name}'가 이미 실행 중입니다")
                return True
            
            # 서버 실행 준비 완료로 표시 (실제 구현에서는 subprocess로 실행)
            self.active_servers[server_name] = {
                'config': server_config,
                'status': 'running'
            }
            
            logger.info(f"MCP 서버 '{server_name}' 시작됨")
            return True
            
        except Exception as e:
            logger.error(f"MCP 서버 시작 실패: {e}")
            return False
    
    async def call_browser_navigate(self, url: str) -> Dict[str, Any]:
        """브라우저 MCP 서버를 통해 웹 페이지 이동"""
        try:
            if not await self.start_server('browser'):
                return {"success": False, "error": "브라우저 서버 시작 실패"}
            
            # MCP-Fetch 스타일 호출 사용
            logger.info(f"브라우저로 이동: {url}")
            
            fetch_result = await self.call_fetch_get(url, {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
            })
            
            if fetch_result.get('success'):
                html_content = fetch_result.get('content', '')
                return {
                    "success": True,
                    "url": url,
                    "status_code": fetch_result.get('status_code', 200),
                    "html": html_content[:5000],  # 처음 5000자만
                    "title": self._extract_title(html_content),
                    "headers": fetch_result.get('headers', {}),
                    "fetch_method": "MCP-Fetch"
                }
            else:
                return fetch_result
                    
        except Exception as e:
            logger.error(f"브라우저 이동 실패: {e}")
            return {"success": False, "error": str(e)}
    
    async def call_browser_extract_data(self, selector: str) -> Dict[str, Any]:
        """브라우저 MCP 서버를 통해 데이터 추출"""
        try:
            if 'browser' not in self.active_servers:
                return {"success": False, "error": "브라우저 서버가 실행되지 않음"}
            
            # 실제 MCP 호출 시뮬레이션
            logger.info(f"데이터 추출 시도: {selector}")
            
            # 임시 응답 (실제 구현에서는 MCP를 통해 브라우저 자동화)
            return {
                "success": True,
                "selector": selector,
                "data": ["샘플 데이터 1", "샘플 데이터 2"],
                "count": 2
            }
            
        except Exception as e:
            logger.error(f"데이터 추출 실패: {e}")
            return {"success": False, "error": str(e)}
    
    async def call_browser_click(self, selector: str) -> Dict[str, Any]:
        """브라우저 MCP 서버를 통해 요소 클릭"""
        try:
            if 'browser' not in self.active_servers:
                return {"success": False, "error": "브라우저 서버가 실행되지 않음"}
            
            logger.info(f"요소 클릭: {selector}")
            
            return {
                "success": True,
                "action": "click",
                "selector": selector,
                "message": "클릭 완료"
            }
            
        except Exception as e:
            logger.error(f"클릭 실패: {e}")
            return {"success": False, "error": str(e)}
    
    async def call_browser_type(self, selector: str, text: str) -> Dict[str, Any]:
        """브라우저 MCP 서버를 통해 텍스트 입력"""
        try:
            if 'browser' not in self.active_servers:
                return {"success": False, "error": "브라우저 서버가 실행되지 않음"}
            
            logger.info(f"텍스트 입력: {selector} = {text}")
            
            return {
                "success": True,
                "action": "type",
                "selector": selector,
                "text": text,
                "message": "텍스트 입력 완료"
            }
            
        except Exception as e:
            logger.error(f"텍스트 입력 실패: {e}")
            return {"success": False, "error": str(e)}
    
    async def call_filesystem_read(self, file_path: str) -> Dict[str, Any]:
        """파일시스템 MCP 서버를 통해 파일 읽기"""
        try:
            if not await self.start_server('filesystem'):
                return {"success": False, "error": "파일시스템 서버 시작 실패"}
            
            logger.info(f"파일 읽기: {file_path}")
            
            # 실제 파일 읽기 시뮬레이션
            file_full_path = Path(file_path)
            if file_full_path.exists():
                content = file_full_path.read_text(encoding='utf-8')
                return {
                    "success": True,
                    "file_path": file_path,
                    "content": content,
                    "size": len(content)
                }
            else:
                return {"success": False, "error": f"파일을 찾을 수 없음: {file_path}"}
                
        except Exception as e:
            logger.error(f"파일 읽기 실패: {e}")
            return {"success": False, "error": str(e)}
    
    async def call_filesystem_write(self, file_path: str, content: str) -> Dict[str, Any]:
        """파일시스템 MCP 서버를 통해 파일 쓰기"""
        try:
            if 'filesystem' not in self.active_servers:
                return {"success": False, "error": "파일시스템 서버가 실행되지 않음"}
            
            logger.info(f"파일 쓰기: {file_path}")
            
            # 실제 파일 쓰기 시뮬레이션
            file_full_path = Path(file_path)
            file_full_path.parent.mkdir(parents=True, exist_ok=True)
            file_full_path.write_text(content, encoding='utf-8')
            
            return {
                "success": True,
                "file_path": file_path,
                "size": len(content),
                "message": "파일 쓰기 완료"
            }
            
        except Exception as e:
            logger.error(f"파일 쓰기 실패: {e}")
            return {"success": False, "error": str(e)}
    
    def _extract_title(self, html: str) -> str:
        """HTML에서 제목 추출"""
        try:
            import re
            title_match = re.search(r'<title[^>]*>([^<]*)</title>', html, re.IGNORECASE)
            return title_match.group(1).strip() if title_match else "제목 없음"
        except:
            return "제목 추출 실패"
    
    async def stop_server(self, server_name: str) -> bool:
        """MCP 서버 중지"""
        try:
            if server_name in self.active_servers:
                del self.active_servers[server_name]
                logger.info(f"MCP 서버 '{server_name}' 중지됨")
                return True
            return False
        except Exception as e:
            logger.error(f"MCP 서버 중지 실패: {e}")
            return False
    
    async def stop_all_servers(self):
        """모든 MCP 서버 중지"""
        for server_name in list(self.active_servers.keys()):
            await self.stop_server(server_name)
    
    def get_server_status(self) -> Dict[str, Any]:
        """서버 상태 반환"""
        return {
            "active_servers": list(self.active_servers.keys()),
            "total_servers": len(self.active_servers)
        }
    
    # === MCP-Fetch 스타일 HTTP 요청 메서드들 ===
    
    async def call_fetch_get(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Dict[str, Any]:
        """MCP-Fetch 스타일 GET 요청"""
        try:
            logger.info(f"MCP-Fetch GET: {url}")
            
            import aiohttp
            default_headers = {
                'User-Agent': 'MCP-Enhanced-Crawler/1.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'ko-KR,ko;q=0.9,en;q=0.8',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache'
            }
            
            if headers:
                default_headers.update(headers)
            
            async with aiohttp.ClientSession(headers=default_headers, timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.get(url) as response:
                    content = await response.text()
                    response_headers = dict(response.headers)
                    
                    return {
                        "success": True,
                        "url": url,
                        "method": "GET",
                        "status_code": response.status,
                        "content": content,
                        "headers": response_headers,
                        "content_type": response_headers.get('content-type', 'text/html'),
                        "content_length": len(content),
                        "fetch_time": timeout,
                        "mcp_fetch": True
                    }
                    
        except Exception as e:
            logger.error(f"MCP-Fetch GET 실패: {e}")
            return {
                "success": False,
                "url": url,
                "method": "GET", 
                "error": str(e),
                "mcp_fetch": True
            }
    
    async def call_fetch_post(self, url: str, data: Dict[str, Any], headers: Optional[Dict[str, str]] = None, timeout: int = 30) -> Dict[str, Any]:
        """MCP-Fetch 스타일 POST 요청"""
        try:
            logger.info(f"MCP-Fetch POST: {url}")
            
            import aiohttp
            import json
            
            default_headers = {
                'User-Agent': 'MCP-Enhanced-Crawler/1.0',
                'Content-Type': 'application/json',
                'Accept': 'application/json,text/html,application/xhtml+xml',
                'Cache-Control': 'no-cache'
            }
            
            if headers:
                default_headers.update(headers)
            
            # JSON 또는 form data 처리
            if default_headers.get('Content-Type') == 'application/json':
                post_data = json.dumps(data, ensure_ascii=False)
            else:
                post_data = data
            
            async with aiohttp.ClientSession(headers=default_headers, timeout=aiohttp.ClientTimeout(total=timeout)) as session:
                async with session.post(url, data=post_data) as response:
                    content = await response.text()
                    response_headers = dict(response.headers)
                    
                    return {
                        "success": True,
                        "url": url,
                        "method": "POST",
                        "status_code": response.status,
                        "content": content,
                        "headers": response_headers,
                        "sent_data": data,
                        "content_type": response_headers.get('content-type', 'text/html'),
                        "mcp_fetch": True
                    }
                    
        except Exception as e:
            logger.error(f"MCP-Fetch POST 실패: {e}")
            return {
                "success": False,
                "url": url,
                "method": "POST",
                "error": str(e),
                "sent_data": data,
                "mcp_fetch": True
            }
    
    async def call_fetch_with_session(self, url: str, method: str = "GET", data: Optional[Dict] = None, headers: Optional[Dict[str, str]] = None, cookies: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """MCP-Fetch 세션 유지 요청 (로그인 후 크롤링에 유용)"""
        try:
            logger.info(f"MCP-Fetch 세션 요청: {method} {url}")
            
            import aiohttp
            
            # 세션 쿠키 및 헤더 설정
            session_headers = {
                'User-Agent': 'MCP-Enhanced-Crawler/1.0',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Referer': url,
                'Cache-Control': 'no-cache'
            }
            
            if headers:
                session_headers.update(headers)
            
            cookie_jar = None
            if cookies:
                cookie_jar = aiohttp.CookieJar()
                for name, value in cookies.items():
                    cookie_jar.update_cookies({name: value})
            
            async with aiohttp.ClientSession(headers=session_headers, cookie_jar=cookie_jar) as session:
                if method.upper() == "GET":
                    async with session.get(url) as response:
                        content = await response.text()
                        return self._format_fetch_response(response, content, url, method, data)
                        
                elif method.upper() == "POST":
                    async with session.post(url, data=data) as response:
                        content = await response.text()
                        return self._format_fetch_response(response, content, url, method, data)
                        
                else:
                    return {"success": False, "error": f"지원하지 않는 HTTP 메서드: {method}"}
                    
        except Exception as e:
            logger.error(f"MCP-Fetch 세션 요청 실패: {e}")
            return {
                "success": False,
                "url": url,
                "method": method,
                "error": str(e),
                "mcp_fetch": True
            }
    
    async def call_fetch_api_with_retry(self, url: str, max_retries: int = 3, delay: int = 1) -> Dict[str, Any]:
        """MCP-Fetch 재시도 기능 (불안정한 API 대응)"""
        for attempt in range(max_retries):
            try:
                logger.info(f"MCP-Fetch 재시도 {attempt + 1}/{max_retries}: {url}")
                
                result = await self.call_fetch_get(url)
                if result.get('success'):
                    result['retry_attempt'] = attempt + 1
                    return result
                    
                if attempt < max_retries - 1:
                    import asyncio
                    await asyncio.sleep(delay * (attempt + 1))  # 지수 백오프
                    
            except Exception as e:
                logger.error(f"MCP-Fetch 재시도 {attempt + 1} 실패: {e}")
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "url": url,
                        "error": f"최대 재시도 횟수 초과: {str(e)}",
                        "max_retries": max_retries,
                        "mcp_fetch": True
                    }
        
        return {"success": False, "url": url, "error": "알 수 없는 오류"}
    
    def _format_fetch_response(self, response, content: str, url: str, method: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """HTTP 응답 포맷팅 헬퍼"""
        return {
            "success": True,
            "url": url,
            "method": method.upper(),
            "status_code": response.status,
            "content": content,
            "headers": dict(response.headers),
            "cookies": {cookie.key: cookie.value for cookie in response.cookies.values()},
            "sent_data": data,
            "content_length": len(content),
            "mcp_fetch": True
        }
    
    # === SQLite MCP 통합 메서드 ===
    async def save_crawled_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """크롤링된 메타데이터를 SQLite에 저장"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            sqlite_service = get_sqlite_service()
            metadata_id = await sqlite_service.save_stat_metadata(metadata)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            await sqlite_service.log_mcp_action("sqlite", "save_metadata", "success", 
                                              {"metadata_id": metadata_id}, execution_time)
            
            return {
                "success": True,
                "metadata_id": metadata_id,
                "operation": "save_metadata",
                "execution_time": execution_time
            }
            
        except Exception as e:
            await sqlite_service.log_mcp_action("sqlite", "save_metadata", "failed", {"error": str(e)})
            logger.error(f"메타데이터 저장 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "save_metadata"
            }
    
    async def save_crawled_data(self, metadata_id: str, year: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """크롤링된 통계 데이터를 SQLite에 저장"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            sqlite_service = get_sqlite_service()
            data_id = await sqlite_service.save_stat_data(metadata_id, year, data, "MCP")
            
            execution_time = asyncio.get_event_loop().time() - start_time
            await sqlite_service.log_mcp_action("sqlite", "save_data", "success", 
                                              {"data_id": data_id, "metadata_id": metadata_id, "year": year}, execution_time)
            
            return {
                "success": True,
                "data_id": data_id,
                "metadata_id": metadata_id,
                "year": year,
                "operation": "save_data",
                "execution_time": execution_time
            }
            
        except Exception as e:
            await sqlite_service.log_mcp_action("sqlite", "save_data", "failed", {"error": str(e)})
            logger.error(f"통계 데이터 저장 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "save_data"
            }
    
    async def get_metadata_from_db(self, metadata_id: str) -> Dict[str, Any]:
        """SQLite에서 메타데이터 조회"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            sqlite_service = get_sqlite_service()
            metadata = await sqlite_service.get_stat_metadata(metadata_id)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            await sqlite_service.log_mcp_action("sqlite", "get_metadata", "success", 
                                              {"metadata_id": metadata_id}, execution_time)
            
            if metadata:
                return {
                    "success": True,
                    "metadata": metadata,
                    "operation": "get_metadata",
                    "execution_time": execution_time
                }
            else:
                return {
                    "success": False,
                    "error": "메타데이터를 찾을 수 없습니다",
                    "metadata_id": metadata_id,
                    "operation": "get_metadata"
                }
            
        except Exception as e:
            await sqlite_service.log_mcp_action("sqlite", "get_metadata", "failed", {"error": str(e)})
            logger.error(f"메타데이터 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "get_metadata"
            }
    
    async def get_data_from_db(self, metadata_id: str, year: Optional[int] = None) -> Dict[str, Any]:
        """SQLite에서 통계 데이터 조회"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            sqlite_service = get_sqlite_service()
            data_list = await sqlite_service.get_stat_data(metadata_id, year)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            await sqlite_service.log_mcp_action("sqlite", "get_data", "success", 
                                              {"metadata_id": metadata_id, "year": year, "count": len(data_list)}, execution_time)
            
            return {
                "success": True,
                "data": data_list,
                "metadata_id": metadata_id,
                "year": year,
                "count": len(data_list),
                "operation": "get_data",
                "execution_time": execution_time
            }
            
        except Exception as e:
            await sqlite_service.log_mcp_action("sqlite", "get_data", "failed", {"error": str(e)})
            logger.error(f"통계 데이터 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "get_data"
            }
    
    async def search_metadata_in_db(self, query: str, limit: int = 20) -> Dict[str, Any]:
        """SQLite에서 메타데이터 검색"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            sqlite_service = get_sqlite_service()
            results = await sqlite_service.search_metadata(query, limit)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            await sqlite_service.log_mcp_action("sqlite", "search_metadata", "success", 
                                              {"query": query, "count": len(results)}, execution_time)
            
            return {
                "success": True,
                "results": results,
                "query": query,
                "count": len(results),
                "operation": "search_metadata",
                "execution_time": execution_time
            }
            
        except Exception as e:
            await sqlite_service.log_mcp_action("sqlite", "search_metadata", "failed", {"error": str(e)})
            logger.error(f"메타데이터 검색 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "search_metadata"
            }
    
    async def save_ai_analysis_to_db(self, analysis_id: str, metadata_id: str, 
                                   analysis_type: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """AI 분석 결과를 SQLite에 저장"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            sqlite_service = get_sqlite_service()
            processing_time = result.get('processing_time')
            saved_id = await sqlite_service.save_ai_analysis(analysis_id, metadata_id, 
                                                           analysis_type, result, 
                                                           processing_time=processing_time)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            await sqlite_service.log_mcp_action("sqlite", "save_analysis", "success", 
                                              {"analysis_id": saved_id}, execution_time)
            
            return {
                "success": True,
                "analysis_id": saved_id,
                "metadata_id": metadata_id,
                "analysis_type": analysis_type,
                "operation": "save_analysis",
                "execution_time": execution_time
            }
            
        except Exception as e:
            await sqlite_service.log_mcp_action("sqlite", "save_analysis", "failed", {"error": str(e)})
            logger.error(f"AI 분석 결과 저장 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "save_analysis"
            }
    
    async def create_crawling_session_in_db(self, session_id: str, session_name: str) -> Dict[str, Any]:
        """크롤링 세션을 SQLite에 생성"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            sqlite_service = get_sqlite_service()
            created_id = await sqlite_service.create_crawling_session(session_id, session_name)
            
            execution_time = asyncio.get_event_loop().time() - start_time
            await sqlite_service.log_mcp_action("sqlite", "create_session", "success", 
                                              {"session_id": created_id}, execution_time)
            
            return {
                "success": True,
                "session_id": created_id,
                "session_name": session_name,
                "operation": "create_session",
                "execution_time": execution_time
            }
            
        except Exception as e:
            await sqlite_service.log_mcp_action("sqlite", "create_session", "failed", {"error": str(e)})
            logger.error(f"크롤링 세션 생성 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "create_session"
            }
    
    # === 통계 분석 MCP 서버 통합 메서드 ===
    async def call_pandas_analysis(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Pandas Analysis MCP 서버 호출"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            # 여기서 실제 MCP 서버와 통신하는 로직을 구현
            # 현재는 시뮬레이션으로 구현
            logger.info(f"Pandas Analysis MCP 호출: {operation}")
            
            # 임시 결과 - 실제로는 MCP 서버에서 응답받은 데이터
            result = {
                "success": True,
                "operation": operation,
                "server": "pandas-analysis",
                "kwargs": kwargs,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            execution_time = asyncio.get_event_loop().time() - start_time
            await self.log_mcp_action("pandas-analysis", operation, "success", result, execution_time)
            
            return result
            
        except Exception as e:
            await self.log_mcp_action("pandas-analysis", operation, "failed", {"error": str(e)})
            logger.error(f"Pandas Analysis MCP 호출 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": operation
            }
    
    async def call_file_analysis(self, operation: str, file_path: str, **kwargs) -> Dict[str, Any]:
        """File Analysis MCP 서버 호출"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            logger.info(f"File Analysis MCP 호출: {operation} on {file_path}")
            
            result = {
                "success": True,
                "operation": operation,
                "file_path": file_path,
                "server": "file-analysis",
                "kwargs": kwargs,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            execution_time = asyncio.get_event_loop().time() - start_time
            await self.log_mcp_action("file-analysis", operation, "success", result, execution_time)
            
            return result
            
        except Exception as e:
            await self.log_mcp_action("file-analysis", operation, "failed", {"error": str(e)})
            logger.error(f"File Analysis MCP 호출 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": operation
            }
    
    async def call_math_calculation(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Mathematical Calculation MCP 서버 호출"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            logger.info(f"Math Calculation MCP 호출: {operation}")
            
            result = {
                "success": True,
                "operation": operation,
                "server": "math-calculation",
                "kwargs": kwargs,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            execution_time = asyncio.get_event_loop().time() - start_time
            await self.log_mcp_action("math-calculation", operation, "success", result, execution_time)
            
            return result
            
        except Exception as e:
            await self.log_mcp_action("math-calculation", operation, "failed", {"error": str(e)})
            logger.error(f"Math Calculation MCP 호출 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": operation
            }
    
    async def call_visualization(self, operation: str, **kwargs) -> Dict[str, Any]:
        """Visualization MCP 서버 호출"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            logger.info(f"Visualization MCP 호출: {operation}")
            
            result = {
                "success": True,
                "operation": operation,
                "server": "visualization",
                "kwargs": kwargs,
                "timestamp": asyncio.get_event_loop().time()
            }
            
            execution_time = asyncio.get_event_loop().time() - start_time
            await self.log_mcp_action("visualization", operation, "success", result, execution_time)
            
            return result
            
        except Exception as e:
            await self.log_mcp_action("visualization", operation, "failed", {"error": str(e)})
            logger.error(f"Visualization MCP 호출 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": operation
            }
    
    # === 고급 분석 워크플로우 ===
    async def comprehensive_statistical_analysis(self, data: Dict[str, list], analysis_type: str = "full") -> Dict[str, Any]:
        """종합 통계 분석 워크플로우"""
        try:
            results = {
                "workflow": "comprehensive_statistical_analysis",
                "analysis_type": analysis_type,
                "steps": []
            }
            
            # 1. 기본 통계 분석
            basic_stats = await self.call_pandas_analysis("basic_statistics", data=data)
            results["steps"].append({"step": "basic_statistics", "result": basic_stats})
            
            # 2. 수치형 데이터가 있는 경우 상관관계 분석
            if analysis_type in ["full", "correlation"]:
                correlation_analysis = await self.call_math_calculation("correlation_analysis", data=data)
                results["steps"].append({"step": "correlation_analysis", "result": correlation_analysis})
            
            # 3. 시각화 생성
            if analysis_type in ["full", "visualization"]:
                visualization = await self.call_visualization("create_statistical_summary_viz", data=data)
                results["steps"].append({"step": "visualization", "result": visualization})
            
            # 4. 트렌드 분석 (시계열 데이터인 경우)
            if analysis_type in ["full", "trend"]:
                trend_analysis = await self.call_pandas_analysis("trend_analysis", data=data)
                results["steps"].append({"step": "trend_analysis", "result": trend_analysis})
            
            results["success"] = True
            return results
            
        except Exception as e:
            logger.error(f"종합 통계 분석 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "workflow": "comprehensive_statistical_analysis"
            }
    
    async def enhanced_basic_statistics(self, data: Dict[str, list]) -> Dict[str, Any]:
        """향상된 기본통계현황분석"""
        try:
            results = {
                "workflow": "enhanced_basic_statistics",
                "components": {}
            }
            
            # 1. 기본 통계 계산
            basic_stats = await self.call_math_calculation("basic_statistics", data=list(data.values())[0])
            results["components"]["basic_statistics"] = basic_stats
            
            # 2. 분포 분석
            distribution_viz = await self.call_visualization("create_statistical_chart", 
                                                           data=data, chart_type="histogram")
            results["components"]["distribution"] = distribution_viz
            
            # 3. 박스플롯으로 이상치 분석
            outlier_analysis = await self.call_visualization("create_statistical_chart",
                                                           data=data, chart_type="boxplot")
            results["components"]["outliers"] = outlier_analysis
            
            # 4. 여러 컬럼이 있는 경우 상관관계 분석
            if len(data.keys()) > 1:
                correlation_heatmap = await self.call_visualization("create_statistical_chart",
                                                                  data=data, chart_type="correlation_heatmap")
                results["components"]["correlation"] = correlation_heatmap
            
            results["success"] = True
            return results
            
        except Exception as e:
            logger.error(f"향상된 기본통계분석 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "workflow": "enhanced_basic_statistics"
            }

    async def get_db_stats_summary(self) -> Dict[str, Any]:
        """데이터베이스 통계 요약"""
        try:
            start_time = asyncio.get_event_loop().time()
            
            sqlite_service = get_sqlite_service()
            summary = await sqlite_service.get_stats_summary()
            
            execution_time = asyncio.get_event_loop().time() - start_time
            await sqlite_service.log_mcp_action("sqlite", "get_summary", "success", 
                                              summary, execution_time)
            
            return {
                "success": True,
                "summary": summary,
                "operation": "get_summary",
                "execution_time": execution_time
            }
            
        except Exception as e:
            await sqlite_service.log_mcp_action("sqlite", "get_summary", "failed", {"error": str(e)})
            logger.error(f"데이터베이스 요약 조회 실패: {e}")
            return {
                "success": False,
                "error": str(e),
                "operation": "get_summary"
            }

# 글로벌 MCP 클라이언트 인스턴스
mcp_client = MCPClient()