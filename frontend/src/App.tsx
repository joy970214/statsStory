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

type AppState = 'loading' | 'stats-list' | 'viewing-advanced-cardnews' | 'optimized-progress' | 'viewing-table-analysis' | 'collected-stats' | 'stat-detail' | 'stat-distribution' | 'stat-summary';

function App() {
  const [state, setState] = useState<AppState>('loading');
  const [stats, setStats] = useState<StatItem[]>([]);
  const [selectedStat, setSelectedStat] = useState<StatItem | null>(null);
  const [advancedCardNews, setAdvancedCardNews] = useState<AdvancedCardNewsResponse | null>(null);
  const [optimizedResult, setOptimizedResult] = useState<any | null>(null);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [ongoingTask, setOngoingTask] = useState<{taskId: string, statName: string, startTime: string, statInfo?: StatItem} | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tableAnalysisStatName, setTableAnalysisStatName] = useState<string | null>(null);
  const [selectedStatForDetail, setSelectedStatForDetail] = useState<string | null>(null);

  useEffect(() => {
    loadRecentStats();
    checkOngoingTask();
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
          console.log('저장된 작업 상태 확인 실패, 정리:', error);
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
      console.log('API 호출 시작...');
      const response = await statsAPI.getRecentStats();
      console.log('API 응답:', response);
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
          console.log('기존 작업 취소 시작, taskId:', currentTaskId);
          await statsAPI.cancelAnalysis(currentTaskId);
          localStorage.removeItem('ongoingAnalysisTask');
          setOngoingTask(null);
          setCurrentTaskId(null);
          console.log('기존 분석 작업이 취소되었습니다.');
        } catch (cancelError) {
          console.error('기존 작업 취소 실패:', cancelError);
          // 취소 실패해도 새 작업은 시작
        }
      }

      setSelectedStat(stat);
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
    setSelectedStat(null);
    setAdvancedCardNews(null);
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

  return (
    <div className="min-h-screen bg-gray-50">
      {/* 헤더 */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div 
              className="flex items-center cursor-pointer"
              onClick={handleBackToList}
            >
              <h1 className="text-2xl font-bold text-gray-900">통계이야기</h1>
              <span className="ml-3 text-sm text-gray-500">국토교통부 통계 카드뉴스</span>
            </div>
            
            <div className="text-sm text-gray-600">
              powered by Claude
            </div>
          </div>
        </div>
      </header>

      {/* 메인 콘텐츠 */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-md p-4">
            <p className="text-red-800">{error}</p>
            <button
              onClick={loadRecentStats}
              className="mt-2 text-red-600 hover:text-red-800 underline"
            >
              다시 시도하기
            </button>
          </div>
        )}

        {state === 'loading' && (
          <LoadingSpinner message="최신 통계 목록을 불러오는 중..." />
        )}

        {state === 'stats-list' && (
          <div>
            {/* 진행 중인 작업 알림 */}
            {ongoingTask && currentTaskId && (
              <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
                    <div>
                      <h4 className="font-medium text-blue-900">진행 중인 분석</h4>
                      <p className="text-sm text-blue-700">
                        "{ongoingTask.statName}" 기본통계현황분석이 진행 중입니다
                      </p>
                      <p className="text-xs text-blue-600">
                        시작 시간: {new Date(ongoingTask.startTime).toLocaleString('ko-KR')}
                      </p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => {
                        if (currentTaskId && ongoingTask?.statInfo) {
                          setSelectedStat(ongoingTask.statInfo);
                          setState('optimized-progress');
                        }
                      }}
                      className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 text-sm"
                    >
                      진행 상황 보기
                    </button>
                    <button
                      onClick={async () => {
                        if (window.confirm('진행 중인 분석을 취소하시겠습니까?')) {
                          try {
                            // 즉시 UI 상태 정리 (API 호출 전에)
                            localStorage.removeItem('ongoingAnalysisTask');
                            setOngoingTask(null);
                            setCurrentTaskId(null);

                            console.log('작업 취소 시작, taskId:', currentTaskId);
                            if (currentTaskId) {
                              const response = await statsAPI.cancelAnalysis(currentTaskId);
                              console.log('취소 API 응답:', response);
                            }

                            console.log('작업 취소 완료');
                            alert('분석 작업이 취소되었습니다.');

                          } catch (error) {
                            console.error('작업 취소 실패:', error);
                            alert(`작업 취소 실패: ${error instanceof Error ? error.message : '알 수 없는 오류'}`);
                          }
                        }
                      }}
                      className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 text-sm"
                    >
                      취소
                    </button>
                  </div>
                </div>
              </div>
            )}

            <div className="mb-8">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900 mb-2">
                    📊 최신 통계 목록
                  </h2>
                  <p className="text-gray-600">
                    최근 1달 이내 발표된 국토교통부 통계를 확인하고 카드뉴스를 생성해보세요.
                  </p>
                </div>
                <button
                  onClick={handleViewCollectedStats}
                  className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 whitespace-nowrap"
                >
                  📋 수집된 통계표 보기
                </button>
              </div>
            </div>

            {stats.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-500">통계 데이터가 없습니다.</p>
                <button
                  onClick={loadRecentStats}
                  className="mt-4 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
                >
                  새로고침
                </button>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {stats.map((stat) => (
                  <StatCard
                    key={stat.id}
                    stat={stat}
                    onSelect={handleStatSelect}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {state === 'optimized-progress' && currentTaskId && selectedStat && (
          <RealTimeProgressViewer 
            taskId={currentTaskId}
            statName={selectedStat.title}
            onComplete={handleOptimizedComplete}
            onError={handleOptimizedError}
          />
        )}



        {state === 'viewing-advanced-cardnews' && (advancedCardNews || optimizedResult) && (
          <EnhancedBasicStatisticsViewer 
            analysisData={optimizedResult || advancedCardNews} 
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
      <footer className="bg-white border-t mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center text-sm text-gray-500">
            <p>© 2024 통계이야기. 국토교통부 통계누리 데이터 활용.</p>
            <p className="mt-1">AI 기반 카드뉴스 자동 생성 서비스</p>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
