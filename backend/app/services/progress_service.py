import asyncio
import json
from typing import Dict, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, asdict
from fastapi import Request
from fastapi.responses import StreamingResponse
import uuid


@dataclass
class ProgressUpdate:
    """진행률 업데이트 정보"""
    task_id: str
    stage: str
    progress: float  # 0-100
    message: str
    timestamp: str
    estimated_remaining_time: Optional[int] = None  # 초 단위


class ProgressTracker:
    """진행률 추적 및 관리"""
    
    def __init__(self):
        self.active_tasks: Dict[str, Dict] = {}
        self.subscribers: Dict[str, asyncio.Queue] = {}
    
    def create_task(self, task_name: str) -> str:
        """새로운 작업 생성 및 ID 반환"""
        task_id = str(uuid.uuid4())
        self.active_tasks[task_id] = {
            "name": task_name,
            "created_at": datetime.now(),
            "current_progress": 0,
            "current_stage": "준비중",
            "current_message": "작업 준비 중...",
            "start_time": datetime.now(),
            "completed": False
        }
        return task_id
    
    def update_progress(
        self, 
        task_id: str, 
        stage: str, 
        progress: float, 
        message: str,
        estimated_remaining_time: Optional[int] = None
    ):
        """진행률 업데이트"""
        if task_id not in self.active_tasks:
            return
        
        # 작업 정보 업데이트
        task_info = self.active_tasks[task_id]
        task_info["current_progress"] = progress
        task_info["current_stage"] = stage
        task_info["current_message"] = message
        task_info["last_update"] = datetime.now()
        
        if progress >= 100:
            task_info["completed"] = True
            task_info["completed_at"] = datetime.now()
        
        # 진행률 업데이트 객체 생성
        update = ProgressUpdate(
            task_id=task_id,
            stage=stage,
            progress=progress,
            message=message,
            timestamp=datetime.now().isoformat(),
            estimated_remaining_time=estimated_remaining_time
        )
        
        # 모든 구독자에게 브로드캐스트
        self._broadcast_update(task_id, update)
    
    def _broadcast_update(self, task_id: str, update: ProgressUpdate):
        """구독자들에게 업데이트 브로드캐스트"""
        # 특정 작업 구독자들
        if task_id in self.subscribers:
            try:
                self.subscribers[task_id].put_nowait(update)
            except asyncio.QueueFull:
                pass  # 큐가 가득 찬 경우 스킵
    
    def subscribe(self, task_id: str) -> asyncio.Queue:
        """작업 진행률 구독"""
        if task_id not in self.subscribers:
            self.subscribers[task_id] = asyncio.Queue(maxsize=100)  # 큐 크기 제한
        return self.subscribers[task_id]
    
    def unsubscribe(self, task_id: str):
        """구독 해제"""
        if task_id in self.subscribers:
            del self.subscribers[task_id]
    
    def task_exists(self, task_id: str) -> bool:
        """작업 존재 여부 확인"""
        return task_id in self.active_tasks
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """작업 상태 조회"""
        return self.active_tasks.get(task_id)
    
    def cleanup_completed_tasks(self, hours: int = 1):
        """완료된 작업들을 정리 (메모리 절약)"""
        now = datetime.now()
        to_remove = []
        
        for task_id, task_info in self.active_tasks.items():
            if (task_info.get("completed") and 
                task_info.get("completed_at") and
                (now - task_info["completed_at"]).total_seconds() > hours * 3600):
                to_remove.append(task_id)
        
        for task_id in to_remove:
            del self.active_tasks[task_id]
            if task_id in self.subscribers:
                del self.subscribers[task_id]


# 전역 진행률 추적기
progress_tracker = ProgressTracker()


async def stream_progress(task_id: str) -> StreamingResponse:
    """SSE를 통한 진행률 스트리밍"""
    print(f"[SSE] 진행률 스트림 시작: {task_id}")
    
    async def event_generator():
        # 구독 시작
        queue = progress_tracker.subscribe(task_id)
        print(f"[SSE] 큐 구독 완료: {task_id}")
        
        try:
            # 현재 작업 상태 전송 (있는 경우)
            task_status = progress_tracker.get_task_status(task_id)
            if task_status:
                initial_update = ProgressUpdate(
                    task_id=task_id,
                    stage=task_status["current_stage"],
                    progress=task_status["current_progress"],
                    message=task_status["current_message"],
                    timestamp=datetime.now().isoformat()
                )
                print(f"[SSE] 초기 상태 전송: {initial_update}")
                yield f"data: {json.dumps(asdict(initial_update))}\n\n"
            else:
                print(f"[SSE] 작업 상태 없음: {task_id}")
            
            # 새로운 업데이트 대기 및 전송
            while True:
                try:
                    # 타임아웃으로 주기적 하트비트
                    update = await asyncio.wait_for(queue.get(), timeout=30)
                    print(f"[SSE] 업데이트 전송: {update}")
                    yield f"data: {json.dumps(asdict(update))}\n\n"
                    
                    # 작업 완료 시 종료
                    if update.progress >= 100:
                        print(f"[SSE] 작업 완료: {task_id}")
                        break
                        
                except asyncio.TimeoutError:
                    # 하트비트 전송
                    heartbeat = {
                        "type": "heartbeat",
                        "timestamp": datetime.now().isoformat()
                    }
                    yield f"data: {json.dumps(heartbeat)}\n\n"
                    
        except asyncio.CancelledError:
            pass
        finally:
            # 구독 해제
            progress_tracker.unsubscribe(task_id)
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Cache-Control"
        }
    )


class ProgressCallback:
    """진행률 콜백 - 크롤러에서 사용"""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.start_time = datetime.now()
    
    def update(self, stage: str, progress: float, message: str):
        """진행률 업데이트"""
        # 예상 남은 시간 계산
        estimated_remaining_time = None
        if progress > 0:
            elapsed_time = (datetime.now() - self.start_time).total_seconds()
            if elapsed_time > 0:
                total_estimated_time = elapsed_time * (100 / progress)
                estimated_remaining_time = int(total_estimated_time - elapsed_time)
        
        progress_tracker.update_progress(
            self.task_id, 
            stage, 
            progress, 
            message,
            estimated_remaining_time
        )


# 백그라운드 정리 작업
async def cleanup_task():
    """주기적으로 완료된 작업들 정리"""
    while True:
        try:
            await asyncio.sleep(3600)  # 1시간마다
            progress_tracker.cleanup_completed_tasks()
        except Exception as e:
            print(f"정리 작업 오류: {e}")


# 애플리케이션 시작 시 백그라운드 작업 시작
_cleanup_task = None

def start_background_cleanup():
    """백그라운드 정리 작업 시작"""
    global _cleanup_task
    if _cleanup_task is None:
        _cleanup_task = asyncio.create_task(cleanup_task())

def stop_background_cleanup():
    """백그라운드 정리 작업 중단"""
    global _cleanup_task
    if _cleanup_task:
        _cleanup_task.cancel()
        _cleanup_task = None