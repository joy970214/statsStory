import React, { useState, useEffect } from 'react';
import { statsAPI } from '../services/api';
import { motion } from 'framer-motion';
import { 
  CheckCircleIcon, 
  ClockIcon, 
  SparklesIcon
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

      {/* 처리 단계 표시 */}
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
        <div className="space-y-4">
          {[
            { name: '초기화', key: 'init', description: '최적화된 크롤러 초기화 및 설정', threshold: 0 },
            { name: '통계표목록', key: 'tables', description: '사용 가능한 통계표 목록 조회', threshold: 15 },
            { name: '데이터수집', key: 'data', description: '통계표별 메타데이터 및 데이터 수집', threshold: 30 },
            { name: '데이터분석', key: 'stats', description: '기본 통계량 계산', threshold: 80 },
            { name: '벡터DB저장', key: 'vector', description: 'ChromaDB에 데이터 저장 (채팅용)', threshold: 82 },
            { name: 'AI분석', key: 'ai', description: 'Ollama AI 인사이트 생성', threshold: 88 },
            { name: '완료', key: 'complete', description: '분석 결과 정리 및 완료', threshold: 100 }
          ].map((step, index) => {
            const isActive = progress.stage.toLowerCase().includes(step.key) ||
                           step.name === progress.stage ||
                           (step.key === 'data' && progress.stage.includes('데이터')) ||
                           (step.key === 'stats' && progress.stage.includes('분석') && progress.progress >= 80 && progress.progress < 82) ||
                           (step.key === 'vector' && (progress.stage.includes('벡터') || progress.stage.includes('DB'))) ||
                           (step.key === 'ai' && (progress.stage.includes('AI') || progress.message.includes('Ollama') || progress.message.includes('인사이트')));
            const isCompleted = progress.progress >= step.threshold;
            
            return (
              <motion.div 
                key={step.key} 
                className="flex items-start p-3 rounded-lg transition-all duration-200 hover:bg-gray-50"
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.8 + index * 0.1 }}
              >
                <div className="flex-shrink-0 mr-4 mt-1">
                  {isCompleted ? (
                    <motion.div 
                      className="w-6 h-6 bg-green-500 rounded-full flex items-center justify-center shadow-lg"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: "spring", stiffness: 500, damping: 30 }}
                    >
                      <CheckCircleIcon className="w-4 h-4 text-white" />
                    </motion.div>
                  ) : isActive ? (
                    <motion.div 
                      className="w-6 h-6 bg-primary-600 rounded-full shadow-lg"
                      animate={{ 
                        scale: [1, 1.1, 1],
                        opacity: [1, 0.7, 1]
                      }}
                      transition={{ 
                        duration: 1.5, 
                        repeat: Infinity,
                        ease: "easeInOut"
                      }}
                    />
                  ) : (
                    <div className="w-6 h-6 bg-gray-300 rounded-full"></div>
                  )}
                </div>
                <div className="flex-1">
                  <p className={`text-base font-semibold mb-1 ${
                    isActive ? 'text-primary-600' : isCompleted ? 'text-green-600' : 'text-gray-500'
                  }`}>
                    {step.name}
                  </p>
                  <p className="text-sm text-gray-600">{step.description}</p>
                </div>
              </motion.div>
            );
          })}
        </div>
      </motion.div>
    </motion.div>
  );
};