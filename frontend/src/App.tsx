import React, { useState, useEffect } from 'react';
import { StatCard } from './components/StatCard';
import { BasicAnalysisViewer } from './components/BasicAnalysisViewer';
import { LoadingSpinner } from './components/LoadingSpinner';
import { BasicStatisticsViewer } from './components/BasicStatisticsViewer';
import { ComprehensiveAnalysisViewer } from './components/ComprehensiveAnalysisViewer';
import { 
  statsAPI, 
  StatItem, 
  BasicAnalysisResponse,
  ComprehensiveAnalysisResponse,
  AdvancedCardNewsResponse,
  StatisticsAnalysisResponse,
  TrendAnalysisResponse,
  PolicyInsightsResponse
} from './services/api';

type AppState = 'loading' | 'stats-list' | 'generating' | 'viewing-story' | 'viewing-comprehensive' | 'viewing-advanced-cardnews';

function App() {
  const [state, setState] = useState<AppState>('loading');
  const [stats, setStats] = useState<StatItem[]>([]);
  const [selectedStat, setSelectedStat] = useState<StatItem | null>(null);
  const [story, setStory] = useState<BasicAnalysisResponse | null>(null);
  const [comprehensiveAnalysis, setComprehensiveAnalysis] = useState<ComprehensiveAnalysisResponse | null>(null);
  const [advancedCardNews, setAdvancedCardNews] = useState<AdvancedCardNewsResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [analysisType, setAnalysisType] = useState<'basic' | 'comprehensive' | 'advanced-cardnews'>('basic');

  useEffect(() => {
    loadRecentStats();
  }, []);

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

  const handleStatSelect = async (stat: StatItem, type: 'basic' | 'comprehensive' | 'advanced-cardnews' = 'basic') => {
    try {
      setState('generating');
      setSelectedStat(stat);
      setAnalysisType(type);
      setError(null);
      
      const request = {
        stat_name: stat.title,
        stat_url: stat.url || '',
        period: '5years'
      };

      if (type === 'comprehensive') {
        const analysisResponse = await statsAPI.generateComprehensiveAnalysis(request);
        setComprehensiveAnalysis(analysisResponse);
        setState('viewing-comprehensive');
      } else if (type === 'advanced-cardnews') {
        const cardNewsResponse = await statsAPI.generateAdvancedCardNews(request);
        setAdvancedCardNews(cardNewsResponse);
        setState('viewing-advanced-cardnews');
      } else {
        const storyResponse = await statsAPI.generateStory(request);
        setStory(storyResponse);
        setState('viewing-story');
      }
    } catch (err) {
      console.error('분석 생성 오류:', err);
      setError(`분석 생성에 실패했습니다: ${err instanceof Error ? err.message : '알 수 없는 오류'}`);
      setState('stats-list');
    }
  };

  const handleBackToList = () => {
    setState('stats-list');
    setSelectedStat(null);
    setStory(null);
    setComprehensiveAnalysis(null);
    setAdvancedCardNews(null);
    setError(null);
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
            <div className="mb-8">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">
                📊 최신 통계 목록
              </h2>
              <p className="text-gray-600">
                최근 1달 이내 발표된 국토교통부 통계를 확인하고 카드뉴스를 생성해보세요.
              </p>
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

        {state === 'generating' && (
          <div className="text-center py-12">
            <LoadingSpinner message={
              analysisType === 'comprehensive' 
                ? "AI가 종합 분석을 수행하고 있습니다..." 
                : analysisType === 'advanced-cardnews'
                ? "AI가 기본통계현황분석을 수행하고 있습니다..."
                : "AI가 기본 분석을 수행하고 있습니다..."
            } />
            <div className="mt-6 max-w-md mx-auto">
              <div className={`rounded-lg p-4 ${
                analysisType === 'comprehensive' ? 'bg-indigo-50' :
                analysisType === 'advanced-cardnews' ? 'bg-pink-50' : 'bg-blue-50'
              }`}>
                <p className={`text-sm font-medium ${
                  analysisType === 'comprehensive' ? 'text-indigo-800' :
                  analysisType === 'advanced-cardnews' ? 'text-pink-800' : 'text-blue-800'
                }`}>
                  선택된 통계: {selectedStat?.title}
                </p>
                <div className={`mt-2 text-xs ${
                  analysisType === 'comprehensive' ? 'text-indigo-600' :
                  analysisType === 'advanced-cardnews' ? 'text-pink-600' : 'text-blue-600'
                }`}>
                  {analysisType === 'comprehensive' ? (
                    <>
                      • 5년치 데이터 수집 중...<br />
                      • 통계 분석 수행 중...<br />
                      • 트렌드 분석 수행 중...<br />
                      • 정책 시사점 도출 중...<br />
                      • 카드뉴스 생성 중...
                    </>
                  ) : analysisType === 'advanced-cardnews' ? (
                    <>
                      • 기초통계 지표 계산 중...<br />
                      • 현황 파악 분석 중...<br />
                      • 데이터 분포 분석 중...<br />
                      • 객관적 인사이트 도출 중...
                    </>
                  ) : (
                    <>
                      • 메타데이터 추출 중...<br />
                      • 데이터 구조 분석 중...<br />
                      • 데이터 정리 중...
                    </>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}

        {state === 'viewing-story' && story && (
          <BasicAnalysisViewer analysisData={story} onBack={handleBackToList} />
        )}

        {state === 'viewing-comprehensive' && comprehensiveAnalysis && (
          <ComprehensiveAnalysisViewer analysisData={comprehensiveAnalysis} onBack={handleBackToList} />
        )}

        {state === 'viewing-advanced-cardnews' && advancedCardNews && (
          <BasicStatisticsViewer analysisData={advancedCardNews} onBack={handleBackToList} />
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
