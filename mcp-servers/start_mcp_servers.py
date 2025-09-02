#!/usr/bin/env python3
"""
MCP 서버들을 시작하는 스크립트
AI API 없이도 통계 분석을 수행할 수 있도록 MCP 서버들을 실행합니다.
"""

import subprocess
import time
import signal
import sys
import os
from pathlib import Path

class MCPServerManager:
    def __init__(self):
        self.servers = {}
        self.processes = {}
        self.base_path = Path(__file__).parent
        
    def start_server(self, name: str, command: str, args: list, env: dict = None):
        """MCP 서버 시작"""
        try:
            print(f"🚀 {name} 서버 시작 중...")
            
            # 환경 변수 설정
            server_env = os.environ.copy()
            if env:
                server_env.update(env)
            
            # Python 경로 설정
            if name in ["pandas-analysis", "file-analysis", "math-calculation", "visualization"]:
                server_env["PYTHONPATH"] = str(self.base_path)
            
            # 서버 실행
            process = subprocess.Popen(
                [command] + args,
                cwd=self.base_path,
                env=server_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            self.processes[name] = process
            self.servers[name] = {
                "command": command,
                "args": args,
                "env": env,
                "status": "running"
            }
            
            print(f"✅ {name} 서버가 시작되었습니다. (PID: {process.pid})")
            return True
            
        except Exception as e:
            print(f"❌ {name} 서버 시작 실패: {e}")
            return False
    
    def start_all_servers(self):
        """모든 MCP 서버 시작"""
        print("🔧 MCP 서버들을 시작합니다...")
        
        # Python 기반 서버들 시작
        servers_config = {
            "pandas-analysis": {
                "command": "python",
                "args": ["pandas_analysis_server.py"],
                "env": {"PYTHONPATH": str(self.base_path)}
            },
            "file-analysis": {
                "command": "python",
                "args": ["file_analysis_server.py"],
                "env": {"PYTHONPATH": str(self.base_path)}
            },
            "math-calculation": {
                "command": "python",
                "args": ["math_calculation_server.py"],
                "env": {"PYTHONPATH": str(self.base_path)}
            },
            "visualization": {
                "command": "python",
                "args": ["visualization_server.py"],
                "env": {"PYTHONPATH": str(self.base_path)}
            }
        }
        
        for name, config in servers_config.items():
            if self.start_server(name, config["command"], config["args"], config["env"]):
                time.sleep(1)  # 서버 간격을 두고 시작
        
        print(f"\n📊 총 {len(self.processes)}개의 MCP 서버가 실행 중입니다:")
        for name, process in self.processes.items():
            print(f"   - {name}: PID {process.pid}")
    
    def stop_server(self, name: str):
        """특정 MCP 서버 중지"""
        if name in self.processes:
            process = self.processes[name]
            try:
                process.terminate()
                process.wait(timeout=5)
                print(f"🛑 {name} 서버가 중지되었습니다.")
            except subprocess.TimeoutExpired:
                process.kill()
                print(f"💀 {name} 서버가 강제 종료되었습니다.")
            
            del self.processes[name]
            if name in self.servers:
                del self.servers[name]
    
    def stop_all_servers(self):
        """모든 MCP 서버 중지"""
        print("\n🛑 모든 MCP 서버를 중지합니다...")
        
        for name in list(self.processes.keys()):
            self.stop_server(name)
        
        print("✅ 모든 MCP 서버가 중지되었습니다.")
    
    def check_server_status(self):
        """서버 상태 확인"""
        print("\n📋 MCP 서버 상태:")
        
        if not self.processes:
            print("   실행 중인 서버가 없습니다.")
            return
        
        for name, process in self.processes.items():
            if process.poll() is None:
                print(f"   ✅ {name}: 실행 중 (PID: {process.pid})")
            else:
                print(f"   ❌ {name}: 종료됨 (PID: {process.pid})")
                # 종료된 프로세스 정리
                del self.processes[name]
    
    def monitor_servers(self):
        """서버 모니터링"""
        try:
            print("\n👀 서버 모니터링을 시작합니다. (Ctrl+C로 종료)")
            
            while True:
                self.check_server_status()
                time.sleep(10)  # 10초마다 상태 확인
                
        except KeyboardInterrupt:
            print("\n\n🛑 모니터링을 중지합니다...")
            self.stop_all_servers()
    
    def signal_handler(self, signum, frame):
        """시그널 핸들러"""
        print(f"\n\n🛑 시그널 {signum}을 받았습니다. 서버들을 정리합니다...")
        self.stop_all_servers()
        sys.exit(0)

def main():
    """메인 함수"""
    print("🚀 MCP 서버 매니저")
    print("=" * 50)
    
    # 시그널 핸들러 등록
    manager = MCPServerManager()
    signal.signal(signal.SIGINT, manager.signal_handler)
    signal.signal(signal.SIGTERM, manager.signal_handler)
    
    try:
        # 모든 서버 시작
        manager.start_all_servers()
        
        # 서버 상태 확인
        manager.check_server_status()
        
        # 사용자 선택
        while True:
            print("\n" + "=" * 50)
            print("1. 서버 상태 확인")
            print("2. 서버 모니터링 시작")
            print("3. 특정 서버 중지")
            print("4. 모든 서버 중지")
            print("5. 종료")
            print("=" * 50)
            
            choice = input("선택하세요 (1-5): ").strip()
            
            if choice == "1":
                manager.check_server_status()
            elif choice == "2":
                manager.monitor_servers()
            elif choice == "3":
                if manager.processes:
                    print("중지할 서버:")
                    for i, name in enumerate(manager.processes.keys(), 1):
                        print(f"   {i}. {name}")
                    try:
                        server_idx = int(input("서버 번호를 선택하세요: ")) - 1
                        server_names = list(manager.processes.keys())
                        if 0 <= server_idx < len(server_names):
                            manager.stop_server(server_names[server_idx])
                        else:
                            print("❌ 잘못된 번호입니다.")
                    except ValueError:
                        print("❌ 숫자를 입력해주세요.")
                else:
                    print("❌ 실행 중인 서버가 없습니다.")
            elif choice == "4":
                manager.stop_all_servers()
            elif choice == "5":
                break
            else:
                print("❌ 잘못된 선택입니다. 1-5 중에서 선택해주세요.")
    
    except KeyboardInterrupt:
        print("\n\n🛑 프로그램을 종료합니다...")
    finally:
        manager.stop_all_servers()
        print("👋 MCP 서버 매니저를 종료합니다.")

if __name__ == "__main__":
    main()
