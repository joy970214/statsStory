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

function App() {
  const [state, setState] = useState<AppState>('loading');
  const [stats, setStats] = useState<StatItem[]>([]);
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
      // 진행 중인 작업이 있으면 취소 확인
      if (ongoingTask && currentTaskId) {
        const confirmed = window.confirm(
          `현재 "${ongoingTask.statName}" 분석이 진행 중입니다.\n` +
          `"${stat.title}" 분석을 시작하려면 진행 중인 작업을 취소해야 합니다.\n\n` +
          `진행 중인 분석을 취소하고 새로운 분석을 시작하시겠습니까?`
        );

        if (!confirmed) {
          return; // 사용자가 취소하면 아무것도 하지 않음
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

      setError(null);

      const request = {
        stat_name: stat.title,
        stat_url: stat.url || '',
        period: '5years'
      };

      // 모든 분석을 최적화된 버전으로 실행 (실시간 진행률 표시)
      setState('optimized-progress');
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
    { key: 'all', label: '전체', color: 'primary' },
    ...availableStatFields.map((field, index) => ({
      key: field,
      label: field,
      color: ['blue', 'teal', 'purple', 'amber', 'green', 'slate', 'indigo', 'pink', 'yellow', 'red'][index % 10] as string
    }))
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-indigo-100 flex flex-col">
      {/* 헤더 */}
      <header className={`relative bg-gradient-to-r from-white/50 via-blue-50/50 to-indigo-50/50 backdrop-blur-md border-b border-white/30 sticky top-0 z-50 transition-all duration-300 ${
        isScrolled ? 'shadow-lg bg-white/60' : 'shadow-none'
      }`}>
        {/* 배경 장식 */}
        <div className="absolute inset-0 bg-gradient-to-r from-primary-500/5 via-transparent to-secondary-500/5"></div>
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary-500 via-secondary-500 to-primary-600"></div>
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-8">
            <div 
              className="flex items-center cursor-pointer group"
              onClick={handleBackToList}
            >
              {/* 로고 영역 */}
              <div className="flex items-center gap-4">
                <div className="relative">
                  <div className="w-12 h-12 bg-gradient-to-br from-primary-500 to-primary-700 rounded-2xl shadow-lg flex items-center justify-center group-hover:shadow-xl transition-all duration-300 group-hover:scale-105">
                    <ChartBarIcon className="w-7 h-7 text-white" />
                  </div>
                  <div className="absolute -top-1 -right-1 w-4 h-4 bg-secondary-500 rounded-full animate-pulse"></div>
                </div>
                <div>
                  <h1 className="text-3xl font-bold bg-gradient-to-r from-primary-600 via-primary-700 to-primary-800 bg-clip-text text-transparent group-hover:from-primary-700 group-hover:to-primary-900 transition-all duration-300">
                    통계이야기
                  </h1>
                  <p className="text-sm text-gray-600 font-medium mt-1 group-hover:text-primary-600 transition-colors duration-300">
                    국토교통부 통계 카드뉴스
                  </p>
                </div>
              </div>
            </div>
            
            {/* 우측 영역 */}
            <div className="flex items-center gap-6">
              {/* 상태 표시 */}
              <div className="hidden md:flex items-center gap-3">
                <div className="flex items-center gap-2 bg-white/60 backdrop-blur-sm px-4 py-2 rounded-full shadow-sm border border-white/50">
                  <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                  <span className="text-sm font-medium text-gray-700">시스템 정상</span>
                </div>
              </div>
              
              {/* AI 배지 */}
              <div className="flex items-center gap-3 bg-gradient-to-r from-purple-500/10 to-pink-500/10 backdrop-blur-sm px-4 py-2 rounded-full border border-purple-200/50 shadow-sm">
                <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center">
                  <SparklesIcon className="w-4 h-4 text-white" />
                </div>
                <div className="flex flex-col">
                  <span className="text-xs font-semibold text-purple-700">Powered by AI</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 w-full">
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
              <div className="mb-8 bg-gradient-to-r from-primary-50 to-primary-100 border border-primary-200 rounded-xl p-6 shadow-lg">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="relative">
                      <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary-200"></div>
                      <div className="absolute top-0 left-0 animate-spin rounded-full h-8 w-8 border-4 border-transparent border-t-primary-600"></div>
                    </div>
                    <div>
                      <h4 className="font-semibold text-primary-900 text-lg">진행 중인 분석</h4>
                      <p className="text-base text-primary-700 font-medium">
                        "{ongoingTask.statName}" 기본통계현황분석이 진행 중입니다
                      </p>
                      <p className="text-sm text-primary-600 flex items-center gap-2 mt-1">
                        <ClockIcon className="w-4 h-4" />
                        시작 시간: {new Date(ongoingTask.startTime).toLocaleString('ko-KR')}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <button
                      onClick={() => {
                        if (currentTaskId && ongoingTask) {
                          setState('optimized-progress');
                        }
                      }}
                      disabled={isCancelling}
                      className={`px-6 py-3 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
                        isCancelling
                          ? 'bg-gray-400 text-gray-600 cursor-not-allowed'
                          : 'bg-gradient-to-r from-primary-500 to-primary-600 text-white hover:from-primary-600 hover:to-primary-700 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5'
                      }`}
                    >
                      <ChartBarIcon className="w-4 h-4" />
                      진행 상황 보기
                    </button>
                    <button
                      onClick={async () => {
                        if (window.confirm('진행 중인 분석을 취소하시겠습니까?')) {
                          try {
                            setIsCancelling(true);

                            if (currentTaskId) {
                              await statsAPI.cancelAnalysis(currentTaskId);
                            }

                            // API 호출 성공 후 UI 상태 정리
                            localStorage.removeItem('ongoingAnalysisTask');
                            setOngoingTask(null);
                            setCurrentTaskId(null);

                            alert('분석 작업이 취소되었습니다.');

                          } catch (error) {
                            console.error('작업 취소 실패:', error);
                            alert(`작업 취소 실패: ${error instanceof Error ? error.message : '알 수 없는 오류'}`);
                          } finally {
                            setIsCancelling(false);
                          }
                        }
                      }}
                      disabled={isCancelling}
                      className={`px-6 py-3 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
                        isCancelling
                          ? 'bg-gray-400 text-gray-600 cursor-not-allowed'
                          : 'bg-gradient-to-r from-red-500 to-red-600 text-white hover:from-red-600 hover:to-red-700 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5'
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
                  className="bg-gradient-to-r from-secondary-500 to-secondary-600 text-white px-6 py-3 rounded-lg hover:from-secondary-600 hover:to-secondary-700 transition-all duration-200 shadow-lg hover:shadow-xl whitespace-nowrap flex items-center gap-2"
                >
                  <ClipboardDocumentListIcon className="w-5 h-5" />
                  수집된 통계표 보기
                </button>
              </div>

              {/* 필터 버튼들 */}
              <div className="flex flex-wrap gap-3 mb-6">
                {filterOptions.map((option) => {
                  // 동적 클래스명을 미리 정의
                  const getActiveClasses = (color: string) => {
                    switch (color) {
                      case 'primary':
                        return 'bg-gradient-to-r from-primary-500 to-primary-600 text-white shadow-lg';
                      case 'blue':
                        return 'bg-gradient-to-r from-blue-500 to-blue-600 text-white shadow-lg';
                      case 'teal':
                        return 'bg-gradient-to-r from-teal-500 to-teal-600 text-white shadow-lg';
                      case 'purple':
                        return 'bg-gradient-to-r from-purple-500 to-purple-600 text-white shadow-lg';
                      case 'amber':
                        return 'bg-gradient-to-r from-amber-500 to-amber-600 text-white shadow-lg';
                      case 'green':
                        return 'bg-gradient-to-r from-green-500 to-green-600 text-white shadow-lg';
                      case 'slate':
                        return 'bg-gradient-to-r from-slate-500 to-slate-600 text-white shadow-lg';
                      default:
                        return 'bg-gradient-to-r from-gray-500 to-gray-600 text-white shadow-lg';
                    }
                  };

                  return (
                    <button
                      key={option.key}
                      onClick={() => setSelectedFilter(option.key)}
                      className={`px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 flex items-center gap-2 ${
                        selectedFilter === option.key
                          ? getActiveClasses(option.color)
                          : 'bg-white text-gray-600 hover:bg-gray-50 border border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      {selectedFilter === option.key && (
                        <div className="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                      )}
                      {option.label}
                      <span className={`text-xs px-2 py-0.5 rounded-full ${
                        selectedFilter === option.key
                          ? 'bg-white/20 text-white'
                          : 'bg-gray-100 text-gray-500'
                      }`}>
                        {option.key === 'all' 
                          ? stats.length 
                          : stats.filter(stat => stat.stat_field === option.key).length
                        }
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {filteredStats.length === 0 ? (
              <div className="text-center py-12">
                {stats.length === 0 ? (
                  <>
                    <p className="text-gray-500">통계 데이터가 없습니다.</p>
                    <button
                      onClick={loadRecentStats}
                      className="mt-4 bg-gradient-to-r from-primary-500 to-primary-600 text-white px-6 py-3 rounded-lg hover:from-primary-600 hover:to-primary-700 transition-all duration-200 shadow-lg hover:shadow-xl flex items-center gap-2 mx-auto"
                    >
                      <ArrowPathIcon className="w-5 h-5" />
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
                      className="bg-gradient-to-r from-primary-500 to-primary-600 text-white px-6 py-3 rounded-lg hover:from-primary-600 hover:to-primary-700 transition-all duration-200 shadow-lg hover:shadow-xl flex items-center gap-2 mx-auto"
                    >
                      <ChartBarIcon className="w-5 h-5" />
                      전체 보기
                    </button>
                  </>
                )}
              </div>
            ) : (
              <>
                {/* 필터 결과 정보 */}
                <div className="mb-6 flex items-center justify-between">
                  <div className="flex items-center gap-2 text-sm text-gray-600">
                    <ChartBarIcon className="w-4 h-4" />
                    <span>
                      {selectedFilter === 'all' 
                        ? `전체 ${filteredStats.length}개 통계` 
                        : `"${filterOptions.find(opt => opt.key === selectedFilter)?.label}" ${filteredStats.length}개 통계`
                      }
                    </span>
                  </div>
                  {selectedFilter !== 'all' && (
                    <button
                      onClick={() => setSelectedFilter('all')}
                      className="text-sm text-primary-600 hover:text-primary-700 font-medium transition-colors duration-200"
                    >
                      필터 초기화
                    </button>
                  )}
                </div>
                
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
      <footer className="relative bg-gradient-to-r from-gray-900 via-gray-800 to-gray-900 text-white">
        {/* 배경 장식 */}
        <div className="absolute inset-0 bg-gradient-to-r from-primary-500/10 via-transparent to-secondary-500/10"></div>
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary-500 via-secondary-500 to-primary-600"></div>
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {/* 브랜드 섹션 */}
            <div className="md:col-span-1">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-primary-700 rounded-xl shadow-lg flex items-center justify-center">
                  <ChartBarIcon className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white">통계이야기</h3>
                  <p className="text-sm text-gray-400">Statistics Story</p>
                </div>
              </div>
              <p className="text-gray-300 text-sm leading-relaxed">
                국토교통부 통계누리 데이터를 활용한 AI 기반 카드뉴스 자동 생성 서비스입니다.
              </p>
            </div>
            
            {/* 서비스 정보 */}
            <div className="md:col-span-1">
              <h4 className="text-lg font-semibold text-white mb-4">서비스 정보</h4>
              <ul className="space-y-2 text-sm text-gray-300">
                <li className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-primary-500 rounded-full"></div>
                  기본통계현황분석
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-secondary-500 rounded-full"></div>
                  실시간 데이터 수집
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                  AI 카드뉴스 생성
                </li>
                <li className="flex items-center gap-2">
                  <div className="w-2 h-2 bg-pink-500 rounded-full"></div>
                  통계표 분석
                </li>
              </ul>
            </div>
            
            {/* 기술 정보 */}
            <div className="md:col-span-1">
              <h4 className="text-lg font-semibold text-white mb-4">기술 스택</h4>
              <div className="space-y-3">
                <div className="flex items-center gap-3 bg-white/5 rounded-lg p-3">
                  <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-500 rounded-lg flex items-center justify-center">
                    <SparklesIcon className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">Powered by AI</p>
                    <p className="text-xs text-gray-400">Claude Sonnet</p>
                  </div>
                </div>
                <div className="flex items-center gap-3 bg-white/5 rounded-lg p-3">
                  <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-lg flex items-center justify-center">
                    <ChartBarIcon className="w-4 h-4 text-white" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">Data Source</p>
                    <p className="text-xs text-gray-400">국토교통부 통계누리</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
          
          {/* 하단 구분선 및 저작권 */}
          <div className="border-t border-gray-700 mt-8 pt-8">
            <div className="flex justify-center items-center">
              <div className="text-sm text-gray-400">
                <span>© 2025 통계이야기. All rights reserved.</span>
              </div>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
