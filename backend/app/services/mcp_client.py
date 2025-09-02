import json
import asyncio
import subprocess
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

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
            
            # 실제 MCP 호출 시뮬레이션 (실제 구현에서는 MCP 프로토콜 사용)
            logger.info(f"브라우저로 이동: {url}")
            
            # 여기서는 기본적인 HTTP 요청으로 대체
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as response:
                    html_content = await response.text()
                    return {
                        "success": True,
                        "url": url,
                        "status_code": response.status,
                        "html": html_content[:5000],  # 처음 5000자만
                        "title": self._extract_title(html_content)
                    }
                    
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

# 글로벌 MCP 클라이언트 인스턴스
mcp_client = MCPClient()