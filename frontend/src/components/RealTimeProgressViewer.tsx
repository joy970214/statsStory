import React, { useState, useEffect } from 'react';
import { statsAPI } from '../services/api';

interface ProgressData {
  task_id: string;
  stage: string;
  progress: number;
  message: string;
  timestamp: string;
  estimated_remaining_time?: number;
  type?: string; // 하트비트 등을 위한 타입 필드
}

interface RealTimeProgressViewerProps {
  taskId: string;
  statName: string;
  onComplete: (result: any) => void;
  onError: (error: string) => void;
}

export const RealTimeProgressViewer: React.FC<RealTimeProgressViewerProps> = ({
  taskId,
  statName,
  onComplete,
  onError
}) => {
  const [progress, setProgress] = useState<ProgressData | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [eventSource, setEventSource] = useState<EventSource | null>(null);
  const [startTime] = useState(new Date());
  const [elapsedTime, setElapsedTime] = useState(0);

  // 경과 시간 업데이트 타이머
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedTime(prev => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    console.log(`[RealTimeProgressViewer] useEffect 시작 - taskId: ${taskId}`);
    
    // 초기 진행률 설정 (연결 시도 표시)
    setProgress({
      task_id: taskId,
      stage: '연결 시도 중',
      progress: 0,
      message: '서버와 연결을 시도하고 있습니다...',
      timestamp: new Date().toISOString()
    });
    
    let sse: EventSource | null = null;
    let connectionTimeout: NodeJS.Timeout;
    
    // SSE 연결 시작 (약간의 지연 후)
    const timeoutId = setTimeout(() => {
      console.log(`[RealTimeProgressViewer] 지연 후 SSE 연결 실행 - taskId: ${taskId}`);
      sse = statsAPI.subscribeToProgress(taskId, (data: any) => {
        console.log('[RealTimeProgressViewer] 진행률 업데이트 수신:', data);
        
        if (data.type === 'connection') {
          console.log('[RealTimeProgressViewer] 연결 확인 메시지 수신');
          setIsConnected(true);
          return;
        }
        
        if (data.type === 'heartbeat') {
          console.log('[RealTimeProgressViewer] 하트비트 수신');
          return; // 하트비트는 무시
        }

        console.log('[RealTimeProgressViewer] 진행률 상태 업데이트:', data);
        setProgress(data);
        setIsConnected(true);

        // 완료 시 결과 가져오기
        if (data.progress >= 100) {
          console.log('[RealTimeProgressViewer] 분석 완료, 결과 조회 시작');
          handleCompletion();
        }
      });

      sse.onopen = () => {
        console.log('[RealTimeProgressViewer] SSE 연결 성공');
        setIsConnected(true);
      };

      sse.onerror = (error) => {
        console.error('[RealTimeProgressViewer] SSE 연결 오류:', error);
        setIsConnected(false);
        // 재연결 시도는 브라우저가 자동으로 처리
      };

      setEventSource(sse);
      
      // 15초 후에도 진행률이 0이면 오류 표시
      connectionTimeout = setTimeout(() => {
        setProgress(prev => prev && prev.progress === 0 ? {
          ...prev,
          stage: '연결 대기 중',
          message: 'SSE 연결을 기다리고 있습니다. 네트워크 상태를 확인해주세요.'
        } : prev);
      }, 15000);
      
    }, 500); // 500ms 지연

    return () => {
      clearTimeout(timeoutId);
      if (connectionTimeout) {
        clearTimeout(connectionTimeout);
      }
      if (sse) {
        console.log('[RealTimeProgressViewer] SSE 연결 정리');
        sse.close();
      }
    };
  }, [taskId]);

  const handleCompletion = async () => {
    try {
      // 잠시 대기 후 결과 조회 (백엔드에서 결과 저장 완료 대기)
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const result = await statsAPI.getAnalysisResult(taskId);
      onComplete(result);
    } catch (error) {
      console.error('결과 조회 오류:', error);
      onError('분석 결과를 가져오는데 실패했습니다.');
    } finally {
      if (eventSource) {
        eventSource.close();
      }
    }
  };

  const formatElapsedTime = () => {
    const minutes = Math.floor(elapsedTime / 60);
    const seconds = elapsedTime % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  const formatRemainingTime = (seconds?: number) => {
    if (!seconds || seconds <= 0) return null;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `약 ${minutes > 0 ? `${minutes}분 ` : ''}${remainingSeconds}초 남음`;
  };

  if (!progress) {
    return (
      <div className="text-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p className="mt-4 text-gray-600">분석 연결 중...</p>
        <p className="text-sm text-gray-500">통계: {statName}</p>
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto">
      {/* 헤더 */}
      <div className="mb-6 text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          최적화된 기본통계현황분석
        </h2>
        <p className="text-gray-600">{statName}</p>
        <div className="flex justify-center items-center mt-2 text-sm text-gray-500">
          <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
            isConnected ? 'bg-green-500' : 'bg-red-500'
          }`}></span>
          {isConnected ? '실시간 연결됨' : '연결 끊어짐'}
          <span className="ml-4">경과시간: {formatElapsedTime()}</span>
        </div>
      </div>

      {/* 진행률 바 */}
      <div className="mb-6">
        <div className="flex justify-between items-center mb-2">
          <span className="text-sm font-medium text-gray-700">{progress.stage}</span>
          <span className="text-sm font-medium text-gray-700">{progress.progress.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div 
            className="bg-blue-600 h-3 rounded-full transition-all duration-500 ease-out"
            style={{ width: `${Math.min(progress.progress, 100)}%` }}
          ></div>
        </div>
        {progress.estimated_remaining_time && (
          <p className="text-sm text-gray-600 mt-2 text-right">
            {formatRemainingTime(progress.estimated_remaining_time)}
          </p>
        )}
      </div>

      {/* 현재 상태 메시지 */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
        <div className="flex">
          <div className="flex-shrink-0">
            {progress.progress < 100 ? (
              <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"></div>
            ) : (
              <div className="rounded-full h-5 w-5 bg-green-500 flex items-center justify-center">
                <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                </svg>
              </div>
            )}
          </div>
          <div className="ml-3 flex-1">
            <p className="text-sm font-medium text-blue-800">{progress.message}</p>
            <p className="text-xs text-blue-600 mt-1">
              마지막 업데이트: {new Date(progress.timestamp).toLocaleTimeString()}
            </p>
          </div>
        </div>
      </div>

      {/* 처리 단계 표시 */}
      <div className="bg-white border rounded-lg p-4">
        <h3 className="text-lg font-medium text-gray-900 mb-4">처리 단계</h3>
        <div className="space-y-3">
          {[
            { name: '초기화', key: 'init', description: '최적화된 크롤러 초기화 및 설정' },
            { name: '메타데이터', key: 'metadata', description: '통계정보 및 관련용어 수집' },
            { name: '통계표목록', key: 'tables', description: '사용 가능한 통계표 목록 조회' },
            { name: '데이터수집', key: 'data', description: '병렬 통계표 데이터 수집' },
            { name: '분석', key: 'analysis', description: '분석 인사이트 생성' },
            { name: '완료', key: 'complete', description: '분석 결과 정리 및 완료' }
          ].map((step, index) => {
            const isActive = progress.stage.toLowerCase().includes(step.key) || 
                           step.name === progress.stage;
            const isCompleted = progress.progress > (index * 16.67);
            
            return (
              <div key={step.key} className="flex items-start">
                <div className="flex-shrink-0 mr-3 mt-1">
                  {isCompleted ? (
                    <div className="w-5 h-5 bg-green-500 rounded-full flex items-center justify-center">
                      <svg className="w-3 h-3 text-white" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                      </svg>
                    </div>
                  ) : isActive ? (
                    <div className="w-5 h-5 bg-blue-600 rounded-full animate-pulse"></div>
                  ) : (
                    <div className="w-5 h-5 bg-gray-300 rounded-full"></div>
                  )}
                </div>
                <div className="flex-1">
                  <p className={`text-sm font-medium ${
                    isActive ? 'text-blue-600' : isCompleted ? 'text-green-600' : 'text-gray-500'
                  }`}>
                    {step.name}
                  </p>
                  <p className="text-xs text-gray-600">{step.description}</p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};