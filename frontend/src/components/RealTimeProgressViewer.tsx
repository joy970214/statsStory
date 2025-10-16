import React, { useState, useEffect } from 'react';
import { statsAPI } from '../services/api';
import { motion } from 'framer-motion';
import { 
  CheckCircleIcon, 
  ClockIcon, 
  SparklesIcon,
  RocketLaunchIcon,
  ClipboardDocumentListIcon,
  ChartBarIcon,
  MagnifyingGlassIcon,
  CircleStackIcon,
  CpuChipIcon,
  CheckBadgeIcon
} from '@heroicons/react/24/outline';

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
  const [elapsedTime, setElapsedTime] = useState(0);

  // 경과 시간 업데이트 타이머
  useEffect(() => {
    const timer = setInterval(() => {
      setElapsedTime(prev => prev + 1);
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {

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

    // 완료 처리 함수 (useEffect 내부로 이동)
    const handleCompletion = async () => {
      try {
        // 잠시 대기 후 결과 조회 (백엔드에서 결과 저장 완료 대기)
        await new Promise(resolve => setTimeout(resolve, 1000));

        const result = await statsAPI.getAnalysisResult(taskId);
        onComplete(result);
      } catch (error) {
        onError('분석 결과를 가져오는데 실패했습니다.');
      } finally {
        if (sse) {
          sse.close();
        }
      }
    };

    // 브라우저 종료 시 EventSource 정리를 위한 이벤트 리스너
    const handleBeforeUnload = () => {
      if (sse) {
        sse.close();
      }
    };

    // 페이지 가시성 변경 시 처리 (탭 전환 등)
    const handleVisibilityChange = () => {
      // 페이지 가시성 변경 처리
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // SSE 연결 시작 (약간의 지연 후)
    const timeoutId = setTimeout(() => {
      sse = statsAPI.subscribeToProgress(taskId, (data: any) => {
        if (data.type === 'connection') {
          setIsConnected(true);
          return;
        }

        if (data.type === 'heartbeat') {
          return; // 하트비트는 무시
        }

        setProgress(data);
        setIsConnected(true);

        // 취소된 경우 알림 표시
        if (data.stage === '취소됨' || data.message?.includes('취소')) {
          alert('데이터 수집이 취소되었습니다.');
          onError('작업이 사용자에 의해 취소되었습니다.');
          return;
        }

        // 완료 시 결과 가져오기
        if (data.progress >= 100) {
          handleCompletion();
        }
      });

      sse.onopen = () => {
        setIsConnected(true);
      };

      sse.onerror = (error) => {
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
      // 타이머 정리
      clearTimeout(timeoutId);
      if (connectionTimeout) {
        clearTimeout(connectionTimeout);
      }

      // EventSource 정리
      if (sse) {
        sse.close();
      }

      // 이벤트 리스너 제거
      window.removeEventListener('beforeunload', handleBeforeUnload);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [taskId]);

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
      <motion.div 
        className="text-center py-12"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="relative mx-auto w-16 h-16 mb-4">
          <motion.div 
            className="w-16 h-16 rounded-full border-4 border-primary-200"
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          />
          <motion.div 
            className="absolute top-0 left-0 w-16 h-16 rounded-full border-4 border-transparent border-t-primary-600"
            animate={{ rotate: 360 }}
            transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
          />
          <motion.div 
            className="absolute inset-0 flex items-center justify-center"
            animate={{ 
              scale: [1, 1.1, 1],
            }}
            transition={{ 
              duration: 1.5, 
              repeat: Infinity, 
              ease: "easeInOut" 
            }}
          >
            <SparklesIcon className="w-6 h-6 text-primary-600" />
          </motion.div>
        </div>
        <motion.p 
          className="text-gray-700 font-medium text-lg"
          animate={{ opacity: [0.7, 1, 0.7] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          분석 연결 중...
        </motion.p>
        <p className="text-sm text-gray-500 mt-2">통계: {statName}</p>
      </motion.div>
    );
  }

  return (
    <motion.div 
      className="max-w-2xl mx-auto"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      {/* 헤더 */}
      <div className="mb-8 text-center">
        <h2 className="text-2xl font-bold text-gray-900 mb-3">
          통계현황분석
        </h2>
        <p className="text-gray-600 mb-4">
          {statName}
        </p>
        <motion.div 
          className="flex justify-center items-center gap-4 text-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.4 }}
        >
          <div className="flex items-center gap-2">
            <motion.div 
              className={`w-3 h-3 rounded-full ${
                isConnected ? 'bg-green-500' : 'bg-red-500'
              }`}
              animate={{ 
                scale: isConnected ? [1, 1.2, 1] : 1,
                opacity: isConnected ? [1, 0.7, 1] : 1
              }}
              transition={{ 
                duration: 2, 
                repeat: Infinity,
                ease: "easeInOut"
              }}
            />
            <span className={`font-medium ${
              isConnected ? 'text-green-600' : 'text-red-600'
            }`}>
              {isConnected ? '실시간 연결됨' : '연결 끊어짐'}
            </span>
          </div>
          <div className="flex items-center gap-2 text-gray-600">
            <ClockIcon className="w-4 h-4" />
            <span>경과시간: {formatElapsedTime()}</span>
          </div>
        </motion.div>
      </div>

      {/* 진행률 바 */}
      <motion.div 
        className="mb-8"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
      >
        <div className="flex justify-between items-center mb-3">
          <span className="text-lg font-semibold text-gray-800">{progress.stage}</span>
          <span className="text-lg font-bold text-primary-600">{progress.progress.toFixed(1)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-4 shadow-inner">
          <motion.div 
            className="bg-gradient-to-r from-primary-500 to-primary-600 h-4 rounded-full shadow-lg"
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(progress.progress, 100)}%` }}
            transition={{ duration: 0.8, ease: "easeOut" }}
          />
        </div>
        {progress.estimated_remaining_time && (
          <motion.p 
            className="text-sm text-gray-600 mt-3 text-right font-medium"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.6 }}
          >
            {formatRemainingTime(progress.estimated_remaining_time)}
          </motion.p>
        )}
      </motion.div>

      {/* 현재 상태 메시지 */}
      <motion.div 
        className="bg-gradient-to-r from-primary-50 to-primary-100 border border-primary-200 rounded-xl p-6 mb-8 shadow-lg"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ delay: 0.6 }}
      >
        <div className="flex items-start">
          <div className="flex-shrink-0">
            {progress.progress < 100 ? (
              <motion.div 
                className="relative w-8 h-8"
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
              >
                <div className="w-8 h-8 rounded-full border-4 border-primary-200"></div>
                <div className="absolute top-0 left-0 w-8 h-8 rounded-full border-4 border-transparent border-t-primary-600"></div>
              </motion.div>
            ) : (
              <motion.div 
                className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center"
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: "spring", stiffness: 500, damping: 30 }}
              >
                <CheckCircleIcon className="w-5 h-5 text-white" />
              </motion.div>
            )}
          </div>
          <div className="ml-4 flex-1">
            <p className="text-base font-semibold text-primary-800 mb-2">{progress.message}</p>
            <p className="text-sm text-primary-600 flex items-center gap-2">
              <ClockIcon className="w-4 h-4" />
              마지막 업데이트: {new Date(progress.timestamp).toLocaleTimeString()}
            </p>
          </div>
        </div>
      </motion.div>

      {/* 처리 단계 표시 - 가로 레이아웃 */}
      <motion.div
        className="bg-white border border-gray-200 rounded-xl p-6 shadow-lg"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.7 }}
      >
        <h3 className="text-xl font-semibold text-gray-900 mb-6 flex items-center gap-2">
          <SparklesIcon className="w-5 h-5 text-primary-600" />
          처리 단계
        </h3>
        <div className="relative">
          {/* 연결선 */}
          <div className="absolute top-8 left-0 right-0 h-0.5 bg-gray-200" style={{ zIndex: 0 }} />
          
          {/* 단계들 */}
          <div className="relative flex justify-between items-start" style={{ zIndex: 1 }}>
            {[
              { name: '초기화', key: 'init', Icon: RocketLaunchIcon, threshold: 0, endThreshold: 15 },
              { name: '통계표목록', key: 'tables', Icon: ClipboardDocumentListIcon, threshold: 15, endThreshold: 30 },
              { name: '데이터수집', key: 'data', Icon: ChartBarIcon, threshold: 30, endThreshold: 80 },
              { name: '데이터분석', key: 'stats', Icon: MagnifyingGlassIcon, threshold: 80, endThreshold: 82 },
              { name: '벡터DB', key: 'vector', Icon: CircleStackIcon, threshold: 82, endThreshold: 88 },
              { name: 'AI분석', key: 'ai', Icon: CpuChipIcon, threshold: 88, endThreshold: 100 },
              { name: '완료', key: 'complete', Icon: CheckBadgeIcon, threshold: 100, endThreshold: 101 }
            ].map((step, index) => {
              // 진행률 범위로 현재 활성 단계 판단 (더 정확함)
              const isInProgressRange = progress.progress >= step.threshold && progress.progress < step.endThreshold;
              
              // 텍스트 기반 추가 체크 (보조적)
              const isActiveByText = progress.stage.toLowerCase().includes(step.key) ||
                                   step.name === progress.stage ||
                                   (step.key === 'data' && progress.stage.includes('데이터')) ||
                                   (step.key === 'stats' && progress.stage.includes('분석') && progress.progress >= 80 && progress.progress < 82) ||
                                   (step.key === 'vector' && (progress.stage.includes('벡터') || progress.stage.includes('DB'))) ||
                                   (step.key === 'ai' && (progress.stage.includes('AI') || progress.message.includes('Ollama') || progress.message.includes('인사이트')));
              
              // 진행률 범위 또는 텍스트 매칭으로 활성 판단
              const isActive = isInProgressRange || isActiveByText;
              
              // 완료: 진행률이 단계 범위를 넘었고 활성 상태가 아님
              const isCompleted = progress.progress >= step.endThreshold;
              
              return (
                <motion.div 
                  key={step.key} 
                  className="flex flex-col items-center"
                  style={{ flex: '1' }}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.8 + index * 0.1 }}
                >
                  {/* 아이콘/상태 표시 */}
                  <div className="relative mb-3">
                    {isCompleted ? (
                      <motion.div 
                        className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center shadow-lg"
                        initial={{ scale: 0 }}
                        animate={{ scale: 1 }}
                        transition={{ type: "spring", stiffness: 500, damping: 30 }}
                      >
                        <CheckCircleIcon className="w-8 h-8 text-white" />
                      </motion.div>
                    ) : isActive ? (
                      <motion.div 
                        className="w-16 h-16 bg-primary-600 rounded-full flex items-center justify-center shadow-lg"
                        animate={{ 
                          scale: [1, 1.1, 1],
                          boxShadow: [
                            '0 10px 15px -3px rgba(59, 130, 246, 0.3)',
                            '0 20px 25px -5px rgba(59, 130, 246, 0.5)',
                            '0 10px 15px -3px rgba(59, 130, 246, 0.3)'
                          ]
                        }}
                        transition={{ 
                          duration: 1.5, 
                          repeat: Infinity,
                          ease: "easeInOut"
                        }}
                      >
                        <step.Icon className="w-8 h-8 text-white" />
                      </motion.div>
                    ) : (
                      <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center opacity-50">
                        <step.Icon className="w-8 h-8 text-gray-400" />
                      </div>
                    )}
                  </div>
                  
                  {/* 단계 이름 */}
                  <p className={`text-xs font-semibold text-center whitespace-nowrap ${
                    isActive ? 'text-primary-600' : isCompleted ? 'text-green-600' : 'text-gray-400'
                  }`}>
                    {step.name}
                  </p>
                </motion.div>
              );
            })}
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
};