import React, { useState, useEffect } from 'react';
import { StatCard } from './components/StatCard';
import { LoadingSpinner } from './components/LoadingSpinner';
import EnhancedBasicStatisticsViewer from './components/EnhancedBasicStatisticsViewer';
import { RealTimeProgressViewer } from './components/RealTimeProgressViewer';
import TableAnalysisViewer from './components/TableAnalysisViewer';
import CollectedStatsViewer from './components/CollectedStatsViewer';
import StatDetailViewer from './components/StatDetailViewer';
import StatDistributionViewer from './components/StatDistributionViewer';
import StatSummaryViewer from './components/StatSummaryViewer';
import {
  statsAPI,
  StatItem,
  AdvancedCardNewsResponse
} from './services/api';
import { 
  ChartBarIcon, 
  DocumentTextIcon, 
  ClipboardDocumentListIcon,
  SparklesIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  ClockIcon
} from '@heroicons/react/24/outline';

type AppState = 'loading' | 'stats-list' | 'viewing-advanced-cardnews' | 'optimized-progress' | 'viewing-table-analysis' | 'collected-stats' | 'stat-detail' | 'stat-distribution' | 'stat-summary';

type SystemStatus = {
  isOnline: boolean;
  isServerConnected: boolean;
};

function App() {
  const [state, setState] = useState<AppState>('loading');
  const [stats, setStats] = useState<StatItem[]>([]);
  const [systemStatus, setSystemStatus] = useState<SystemStatus>({
    isOnline: navigator.onLine,
    isServerConnected: false
  });
  const [optimizedResult, setOptimizedResult] = useState<any | null>(null);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [ongoingTask, setOngoingTask] = useState<{taskId: string, statName: string, startTime: string, statInfo?: StatItem} | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isCancelling, setIsCancelling] = useState<boolean>(false);
  const [tableAnalysisStatName, setTableAnalysisStatName] = useState<string | null>(null);
  const [selectedStatForDetail, setSelectedStatForDetail] = useState<string | null>(null);
  const [isScrolled, setIsScrolled] = useState<boolean>(false);
  const [selectedFilter, setSelectedFilter] = useState<string>('all');

  useEffect(() => {
    loadRecentStats();
    checkOngoingTask();
    checkSystemStatus();
    
    // 인터넷 연결 상태 모니터링
    const handleOnline = () => setSystemStatus(prev => ({ ...prev, isOnline: true }));
    const handleOffline = () => setSystemStatus(prev => ({ ...prev, isOnline: false }));
    
    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    
    // 서버 연결 상태 주기적 확인
    const serverCheckInterval = setInterval(checkServerConnection, 30000); // 30초마다
    
    return () => {
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      clearInterval(serverCheckInterval);
    };
  }, []);

  // 스크롤 이벤트 리스너
  useEffect(() => {
    const handleScroll = () => {
      const scrollTop = window.scrollY;
      setIsScrolled(scrollTop > 20);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const checkOngoingTask = async () => {
    const savedTask = localStorage.getItem('ongoingAnalysisTask');
    if (savedTask) {
      try {
        const task = JSON.parse(savedTask);

        // 실제로 진행 중인 작업인지 서버에서 확인
        try {
          const response = await statsAPI.getAnalysisStatus(task.taskId);
          if (response.completed) {
            // 이미 완료된 작업이면 localStorage에서 제거
            localStorage.removeItem('ongoingAnalysisTask');
            return;
          }
          // 실제로 진행 중인 작업이면 상태 설정
          setOngoingTask(task);
          setCurrentTaskId(task.taskId);
        } catch (error) {
          // 작업 상태 확인 실패 시 localStorage에서 제거
          localStorage.removeItem('ongoingAnalysisTask');
        }
      } catch (error) {
        localStorage.removeItem('ongoingAnalysisTask');
      }
    }
  };

  const checkSystemStatus = async () => {
    // 인터넷 연결 상태 확인
    const isOnline = navigator.onLine;

    // 서버 연결 상태 확인 (가벼운 헬스 체크 사용)
    let isServerConnected = false;
    try {
      await statsAPI.healthCheck();
      isServerConnected = true;
    } catch (error) {
      isServerConnected = false;
    }

    setSystemStatus({ isOnline, isServerConnected });
  };

  const checkServerConnection = async () => {
    try {
      await statsAPI.healthCheck();
      setSystemStatus(prev => ({ ...prev, isServerConnected: true }));
    } catch (error) {
      setSystemStatus(prev => ({ ...prev, isServerConnected: false }));
    }
  };

  const loadRecentStats = async () => {
    try {
      setState('loading');
      setError(null);
      const response = await statsAPI.getRecentStats();
      setStats(response.stats);
      setState('stats-list');
    } catch (err) {
      console.error('API 호출 오류:', err);
      setError(`통계 데이터를 불러오는데 실패했습니다: ${err instanceof Error ? err.message : '알 수 없는 오류'}`);
      setState('stats-list');
    }
  };

  const handleStatSelect = async (stat: StatItem) => {
    try {
      // 🚀 즉시 로딩 화면 표시 (API 호출 전)
      setState('optimized-progress');
      setError(null);

      // 진행 중인 작업이 있으면 취소 확인
      if (ongoingTask && currentTaskId) {
        const confirmed = window.confirm(
          `현재 "${ongoingTask.statName}" 분석이 진행 중입니다.\n` +
          `"${stat.title}" 분석을 시작하려면 진행 중인 작업을 취소해야 합니다.\n\n` +
          `진행 중인 분석을 취소하고 새로운 분석을 시작하시겠습니까?`
        );

        if (!confirmed) {
          setState('stats-list'); // 취소 시 원래 화면으로 복귀
          return;
        }

        // 기존 작업 취소
        try {
          setIsCancelling(true);
          await statsAPI.cancelAnalysis(currentTaskId);
          localStorage.removeItem('ongoingAnalysisTask');
          setOngoingTask(null);
          setCurrentTaskId(null);
        } catch (cancelError) {
          console.error('기존 작업 취소 실패:', cancelError);
          // 취소 실패해도 새 작업은 시작
        } finally {
          setIsCancelling(false);
        }
      }

      const request = {
        stat_name: stat.title,
        stat_url: stat.url || '',
        period: '5years'
      };

      // API 호출
      const startResponse = await statsAPI.startOptimizedAnalysis(request);
      setCurrentTaskId(startResponse.task_id);

      // 진행 중인 작업을 localStorage에 저장
      const taskInfo = {
        taskId: startResponse.task_id,
        statName: stat.title,
        startTime: new Date().toISOString(),
        statInfo: stat
      };
      localStorage.setItem('ongoingAnalysisTask', JSON.stringify(taskInfo));
      setOngoingTask(taskInfo);

    } catch (err) {
      console.error('분석 생성 오류:', err);
      setError(`분석 생성에 실패했습니다: ${err instanceof Error ? err.message : '알 수 없는 오류'}`);
      setState('stats-list');
    }
  };

  const handleBackToList = () => {
    setState('stats-list');
    setOptimizedResult(null);
    setTableAnalysisStatName(null);
    setSelectedStatForDetail(null);
    setError(null);
    // 진행 중인 작업이 있으면 currentTaskId는 유지
    if (!ongoingTask) {
      setCurrentTaskId(null);
    }
  };

  const handleOptimizedComplete = (result: any) => {
    setOptimizedResult(result);
    setState('viewing-advanced-cardnews'); // 결과를 기존 뷰어로 표시

    // 작업 완료 시 localStorage에서 제거
    localStorage.removeItem('ongoingAnalysisTask');
    setOngoingTask(null);
    setCurrentTaskId(null);
  };

  const handleOptimizedError = (errorMsg: string) => {
    setError(`최적화된 분석 실패: ${errorMsg}`);
    setState('stats-list');

    // 작업 실패 시 localStorage에서 제거
    localStorage.removeItem('ongoingAnalysisTask');
    setOngoingTask(null);
    setCurrentTaskId(null);
  };

  const handleViewTableAnalysis = (statName: string) => {
    setTableAnalysisStatName(statName);
    setState('viewing-table-analysis');
  };

  const handleViewCollectedStats = () => {
    setState('collected-stats');
  };

  const handleSelectStatForDetail = (statName: string) => {
    setSelectedStatForDetail(statName);
    setState('stat-detail');
  };

  const handleViewDistribution = (statName: string) => {
    setSelectedStatForDetail(statName);
    setState('stat-distribution');
  };

  const handleViewSummary = (statName: string) => {
    setSelectedStatForDetail(statName);
    setState('stat-summary');
  };

  // 필터링된 통계 목록
  const filteredStats = stats.filter(stat => {
    if (selectedFilter === 'all') return true;
    return stat.stat_field === selectedFilter;
  });

  // 실제 데이터에서 사용되는 stat_field 값들 추출
  const availableStatFields = Array.from(new Set(stats.map(stat => stat.stat_field).filter(Boolean) as string[]));
  
  // 사용 가능한 필터 옵션들 (동적으로 생성)
  const filterOptions = [
    { key: 'all', label: '전체' },
    ...availableStatFields.map((field) => ({
      key: field,
      label: field
    }))
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* 헤더 */}
      <header className={`bg-white border-b sticky top-0 z-50 transition-shadow ${
        isScrolled ? 'shadow-sm' : ''
      }`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div 
              className="flex items-center cursor-pointer"
              onClick={handleBackToList}
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
                  <ChartBarIcon className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-xl font-bold text-gray-900">
                    통계이야기
                  </h1>
                  <p className="text-xs text-gray-500">
                    국토교통부 통계 카드뉴스
                  </p>
                </div>
              </div>
            </div>
            
            {/* 우측 영역 */}
            <div className="flex items-center gap-4">
              {/* 상태 표시 */}
              <div className="hidden md:flex items-center gap-2 bg-gray-50 px-3 py-1.5 rounded-md border border-gray-200">
                {(() => {
                  if (!systemStatus.isOnline) {
                    return (
                      <>
                        <div className="w-2 h-2 bg-orange-500 rounded-full"></div>
                        <span className="text-xs text-gray-600">인터넷 연결 안됨</span>
                      </>
                    );
                  } else if (!systemStatus.isServerConnected) {
                    return (
                      <>
                        <div className="w-2 h-2 bg-red-500 rounded-full"></div>
                        <span className="text-xs text-gray-600">서버 연결 안됨</span>
                      </>
                    );
                  } else {
                    return (
                      <>
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span className="text-xs text-gray-600">시스템 정상</span>
                      </>
                    );
                  }
                })()}
              </div>
              
              {/* AI 배지 */}
              <div className="flex items-center gap-2 bg-primary-50 px-3 py-1.5 rounded-md border border-primary-200">
                <SparklesIcon className="w-4 h-4 text-primary-600" />
                <span className="text-xs font-medium text-primary-700">AI 분석</span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 pb-16 w-full">
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-6 shadow-sm">
            <div className="flex items-start gap-3">
              <ExclamationTriangleIcon className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
              <div className="flex-1">
                <p className="text-red-800 font-medium">{error}</p>
            <button
              onClick={loadRecentStats}
                  className="mt-3 text-red-600 hover:text-red-800 underline font-medium transition-colors duration-200"
            >
              다시 시도하기
            </button>
              </div>
            </div>
          </div>
        )}

        {state === 'loading' && (
          <LoadingSpinner message="최신 통계 목록을 불러오는 중..." fullScreen={true} />
        )}

        {state === 'stats-list' && (
          <div>
            {/* 진행 중인 작업 알림 */}
            {ongoingTask && currentTaskId && (
              <div className="mb-8 bg-primary-50 border border-primary-200 rounded-lg p-6">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
                    <div>
                      <h4 className="font-semibold text-gray-900 text-base">진행 중인 분석</h4>
                      <p className="text-sm text-gray-700">
                        "{ongoingTask.statName}" 기본통계현황분석이 진행 중입니다
                      </p>
                      <p className="text-xs text-gray-600 flex items-center gap-1.5 mt-1">
                        <ClockIcon className="w-3.5 h-3.5" />
                        시작: {new Date(ongoingTask.startTime).toLocaleString('ko-KR')}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        if (currentTaskId && ongoingTask) {
                          setState('optimized-progress');
                        }
                      }}
                      disabled={isCancelling}
                      className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${
                        isCancelling
                          ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                          : 'bg-primary-600 text-white hover:bg-primary-700'
                      }`}
                    >
                      <ChartBarIcon className="w-4 h-4" />
                      진행 상황
                    </button>
                    <button
                      onClick={async () => {
                        if (window.confirm('진행 중인 분석을 취소하시겠습니까?')) {
                          try {
                            setIsCancelling(true);

                            if (currentTaskId) {
                              await statsAPI.cancelAnalysis(currentTaskId);
                            }

                            localStorage.removeItem('ongoingAnalysisTask');
                            setOngoingTask(null);
                            setCurrentTaskId(null);

                          } catch (error) {
                            console.error('작업 취소 실패:', error);
                            alert(`작업 취소 실패: ${error instanceof Error ? error.message : '알 수 없는 오류'}`);
                          } finally {
                            setIsCancelling(false);
                          }
                        }
                      }}
                      disabled={isCancelling}
                      className={`px-4 py-2 rounded-md text-sm font-medium transition-colors flex items-center gap-2 ${
                        isCancelling
                          ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                          : 'bg-red-600 text-white hover:bg-red-700'
                      }`}
                    >
                      <ExclamationTriangleIcon className="w-4 h-4" />
                      {isCancelling ? '취소 중...' : '취소'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            <div className="mb-8">
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 mb-2 flex items-center gap-2">
                    <ChartBarIcon className="w-6 h-6 text-primary-600" />
                    최신 통계 목록
                  </h2>
                  <p className="text-gray-600">
                    최근 1달 이내 발표된 국토교통부 통계를 확인하고 카드뉴스를 생성해보세요.
                  </p>
                </div>
                <button
                  onClick={handleViewCollectedStats}
                  className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-50 transition-colors whitespace-nowrap flex items-center gap-2 text-sm font-medium"
                >
                  <ClipboardDocumentListIcon className="w-4 h-4" />
                  수집된 통계표
                </button>
              </div>

              {/* 필터 버튼들과 통계 개수 */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                {/* 필터 버튼들 */}
                <div className="flex flex-wrap gap-2">
                  {filterOptions.map((option) => (
                    <button
                      key={option.key}
                      onClick={() => setSelectedFilter(option.key)}
                      className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors flex items-center gap-1.5 ${
                        selectedFilter === option.key
                          ? 'bg-primary-600 text-white'
                          : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200'
                      }`}
                    >
                      {option.label}
                      <span className={`text-xs px-1.5 py-0.5 rounded ${
                        selectedFilter === option.key
                          ? 'bg-primary-500 text-white'
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {option.key === 'all' 
                          ? stats.length 
                          : stats.filter(stat => stat.stat_field === option.key).length
                        }
                      </span>
                    </button>
                  ))}
                </div>

                {/* 통계 개수 표시 */}
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <ChartBarIcon className="w-4 h-4" />
                  <span>
                    {selectedFilter === 'all' 
                      ? `전체 ${stats.length}개 통계` 
                      : `"${filterOptions.find(opt => opt.key === selectedFilter)?.label}" ${stats.filter(stat => stat.stat_field === selectedFilter).length}개 통계`
                    }
                  </span>
                </div>
              </div>
            </div>

            {filteredStats.length === 0 ? (
              <div className="text-center py-12">
                {stats.length === 0 ? (
                  <>
                    <p className="text-gray-500">통계 데이터가 없습니다.</p>
                    <button
                      onClick={loadRecentStats}
                      className="mt-4 bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700 transition-colors flex items-center gap-2 mx-auto text-sm font-medium"
                    >
                      <ArrowPathIcon className="w-4 h-4" />
                      새로고침
                    </button>
                  </>
                ) : (
                  <>
                    <p className="text-gray-500 mb-2">선택한 필터에 해당하는 통계가 없습니다.</p>
                    <p className="text-sm text-gray-400 mb-4">
                      "{filterOptions.find(opt => opt.key === selectedFilter)?.label}" 카테고리의 통계가 없습니다.
                    </p>
                    <button
                      onClick={() => setSelectedFilter('all')}
                      className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700 transition-colors flex items-center gap-2 mx-auto text-sm font-medium"
                    >
                      <ChartBarIcon className="w-4 h-4" />
                      전체 보기
                    </button>
                  </>
                )}
              </div>
            ) : (
              <>
                {/* 필터 초기화 버튼 (필요한 경우에만 표시) */}
                {selectedFilter !== 'all' && (
                  <div className="mb-4 flex justify-end">
                    <button
                      onClick={() => setSelectedFilter('all')}
                      className="text-sm text-primary-600 hover:text-primary-700 font-medium transition-colors flex items-center gap-1.5"
                    >
                      <ChartBarIcon className="w-4 h-4" />
                      필터 초기화
                    </button>
                  </div>
                )}
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {filteredStats.map((stat) => (
                    <StatCard
                      key={stat.id}
                      stat={stat}
                      onSelect={handleStatSelect}
                      disabled={isCancelling}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {state === 'optimized-progress' && currentTaskId && ongoingTask && (
          <RealTimeProgressViewer 
            taskId={currentTaskId}
            statName={ongoingTask.statName}
            onComplete={handleOptimizedComplete}
            onError={handleOptimizedError}
          />
        )}



        {state === 'viewing-advanced-cardnews' && optimizedResult && (
          <EnhancedBasicStatisticsViewer 
            analysisData={optimizedResult} 
            onBack={handleBackToList}
            onViewTableAnalysis={handleViewTableAnalysis}
          />
        )}
        {state === 'viewing-table-analysis' && tableAnalysisStatName && (
          <TableAnalysisViewer
            statName={tableAnalysisStatName}
            onBack={handleBackToList}
          />
        )}

        {state === 'collected-stats' && (
          <CollectedStatsViewer
            onSelectStat={handleSelectStatForDetail}
            onBack={handleBackToList}
          />
        )}

        {state === 'stat-detail' && selectedStatForDetail && (
          <StatDetailViewer
            statName={selectedStatForDetail}
            onBack={handleBackToList}
            onViewDistribution={handleViewDistribution}
            onViewSummary={handleViewSummary}
          />
        )}

        {state === 'stat-distribution' && selectedStatForDetail && (
          <StatDistributionViewer
            statName={selectedStatForDetail}
            onBack={handleBackToList}
          />
        )}

        {state === 'stat-summary' && selectedStatForDetail && (
          <StatSummaryViewer
            statName={selectedStatForDetail}
            onBack={handleBackToList}
          />
        )}
      </main>

      {/* 푸터 */}
      <footer className="bg-gray-900 text-white border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* 브랜드 섹션 */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                  <ChartBarIcon className="w-5 h-5 text-white" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">통계이야기</h3>
                </div>
              </div>
              <p className="text-gray-400 text-sm">
                국토교통부 통계누리 데이터를 활용한 AI 기반 카드뉴스 생성 서비스
              </p>
            </div>
            
            {/* 서비스 정보 */}
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">서비스 정보</h4>
              <ul className="space-y-1.5 text-sm text-gray-400">
                <li>기본통계현황분석</li>
                <li>실시간 데이터 수집</li>
                <li>AI 카드뉴스 생성</li>
                <li>통계표 분석</li>
              </ul>
            </div>
            
            {/* 기술 정보 */}
            <div>
              <h4 className="text-sm font-semibold text-white mb-3">기술 스택</h4>
              <div className="space-y-2 text-sm text-gray-400">
                <div>
                  <p className="font-medium text-white">AI Engine</p>
                  <p className="text-xs">Claude Sonnet</p>
                </div>
                <div>
                  <p className="font-medium text-white">Data Source</p>
                  <p className="text-xs">국토교통부 통계누리</p>
                </div>
              </div>
            </div>
          </div>
          
          {/* 저작권 */}
          <div className="border-t border-gray-800 mt-8 pt-6">
            <p className="text-center text-sm text-gray-500">
              © 2025 통계이야기. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
