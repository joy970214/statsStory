import React, { useState } from 'react';

interface ComprehensiveAnalysisData {
  stat_name: string;
  analysis_date: string;
  metadata: any;
  analysis: {
    statistics_analysis: {
      analysis_result: string;
      status: string;
      error?: string;
    };
    trend_analysis: {
      trend_analysis: string;
      status: string;
      error?: string;
    };
    policy_insights: {
      policy_insights: string;
      status: string;
      error?: string;
    };
    card_news: {
      cards?: any[];
      sections?: any[];
      raw_response?: string;
      status: string;
      error?: string;
    };
    generated_at: string;
  };
}

interface ComprehensiveAnalysisViewerProps {
  analysisData: ComprehensiveAnalysisData;
  onBack: () => void;
}

export const ComprehensiveAnalysisViewer: React.FC<ComprehensiveAnalysisViewerProps> = ({
  analysisData,
  onBack
}) => {
  const [activeTab, setActiveTab] = useState<'stats' | 'trends' | 'policy' | 'cardnews'>('stats');

  const downloadAnalysis = () => {
    const content = generateAnalysisContent();
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${analysisData.stat_name}_종합분석.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const generateAnalysisContent = () => {
    let content = `# ${analysisData.stat_name} 종합 분석 보고서\n\n`;
    content += `생성일: ${new Date(analysisData.analysis_date).toLocaleDateString('ko-KR')}\n\n`;
    
    content += `## 📊 통계 분석\n\n`;
    if (analysisData.analysis.statistics_analysis.status === 'success') {
      content += `${analysisData.analysis.statistics_analysis.analysis_result}\n\n`;
    } else {
      content += `분석 중 오류 발생: ${analysisData.analysis.statistics_analysis.error}\n\n`;
    }
    
    content += `## 📈 트렌드 분석\n\n`;
    if (analysisData.analysis.trend_analysis.status === 'success') {
      content += `${analysisData.analysis.trend_analysis.trend_analysis}\n\n`;
    } else {
      content += `분석 중 오류 발생: ${analysisData.analysis.trend_analysis.error}\n\n`;
    }
    
    content += `## 💡 정책 시사점\n\n`;
    if (analysisData.analysis.policy_insights.status === 'success') {
      content += `${analysisData.analysis.policy_insights.policy_insights}\n\n`;
    } else {
      content += `분석 중 오류 발생: ${analysisData.analysis.policy_insights.error}\n\n`;
    }
    
    content += `## 📱 카드뉴스\n\n`;
    if (analysisData.analysis.card_news.status === 'success') {
      content += `${analysisData.analysis.card_news.raw_response || '카드뉴스 데이터 생성됨'}\n\n`;
    } else {
      content += `생성 중 오류 발생: ${analysisData.analysis.card_news.error}\n\n`;
    }
    
    return content;
  };

  const tabs = [
    { id: 'stats' as const, label: '📊 통계 분석', color: 'blue' },
    { id: 'trends' as const, label: '📈 트렌드 분석', color: 'green' },
    { id: 'policy' as const, label: '💡 정책 시사점', color: 'purple' },
    { id: 'cardnews' as const, label: '📱 카드뉴스', color: 'pink' }
  ];

  const renderAnalysisContent = (content: string, status: string, error?: string) => {
    if (status === 'error') {
      return (
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-red-800 mb-2">오류 발생</h3>
          <p className="text-red-600">{error || '분석 중 오류가 발생했습니다.'}</p>
        </div>
      );
    }

    return (
      <div className="prose max-w-none">
        <div className="whitespace-pre-wrap text-gray-700 leading-relaxed">
          {content}
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* 헤더 */}
      <div className="flex justify-between items-center mb-8">
        <button
          onClick={onBack}
          className="flex items-center text-blue-600 hover:text-blue-800 transition-colors"
        >
          ← 목록으로 돌아가기
        </button>
        
        <button
          onClick={downloadAnalysis}
          className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 transition-colors"
        >
          📄 전체 분석 다운로드
        </button>
      </div>

      {/* 제목 */}
      <div className="bg-gradient-to-r from-indigo-600 to-indigo-800 text-white p-8 rounded-lg mb-8">
        <h1 className="text-3xl font-bold mb-4">🔍 {analysisData.stat_name} 종합 분석</h1>
        <p className="text-indigo-100 text-lg">통계 분석, 트렌드 분석, 정책 시사점, 카드뉴스를 한 번에</p>
        <p className="text-indigo-200 text-sm mt-4">
          분석일시: {new Date(analysisData.analysis_date).toLocaleString('ko-KR')}
        </p>
      </div>

      {/* 분석 상태 요약 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {tabs.map((tab) => {
          const analysisKey = tab.id === 'stats' ? 'statistics_analysis' : 
                            tab.id === 'trends' ? 'trend_analysis' :
                            tab.id === 'policy' ? 'policy_insights' : 'card_news';
          
          // 타입 안전한 상태 확인
          let status = 'error';
          const analysisItem = analysisData.analysis[analysisKey as keyof typeof analysisData.analysis];
          if (analysisItem && typeof analysisItem === 'object' && 'status' in analysisItem) {
            status = analysisItem.status;
          }
          
          return (
            <div key={tab.id} className="bg-white rounded-lg shadow border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-600">{tab.label}</span>
                <span className={`px-2 py-1 text-xs rounded-full ${
                  status === 'success' 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-red-100 text-red-800'
                }`}>
                  {status === 'success' ? '✓ 완료' : '✗ 오류'}
                </span>
              </div>
            </div>
          );
        })}
      </div>

      {/* 탭 네비게이션 */}
      <div className="border-b border-gray-200 mb-8">
        <nav className="flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-4 px-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* 탭 콘텐츠 */}
      <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-8">
        {activeTab === 'stats' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-6">📊 통계 분석 결과</h2>
            {renderAnalysisContent(
              analysisData.analysis.statistics_analysis.analysis_result,
              analysisData.analysis.statistics_analysis.status,
              analysisData.analysis.statistics_analysis.error
            )}
          </div>
        )}

        {activeTab === 'trends' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-6">📈 트렌드 분석 결과</h2>
            {renderAnalysisContent(
              analysisData.analysis.trend_analysis.trend_analysis,
              analysisData.analysis.trend_analysis.status,
              analysisData.analysis.trend_analysis.error
            )}
          </div>
        )}

        {activeTab === 'policy' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-6">💡 정책 시사점</h2>
            {renderAnalysisContent(
              analysisData.analysis.policy_insights.policy_insights,
              analysisData.analysis.policy_insights.status,
              analysisData.analysis.policy_insights.error
            )}
          </div>
        )}

        {activeTab === 'cardnews' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-6">📱 카드뉴스</h2>
            {analysisData.analysis.card_news.status === 'error' ? (
              renderAnalysisContent(
                '',
                analysisData.analysis.card_news.status,
                analysisData.analysis.card_news.error
              )
            ) : (
              <div>
                {analysisData.analysis.card_news.cards && analysisData.analysis.card_news.cards.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {analysisData.analysis.card_news.cards.map((card: any, index: number) => (
                      <div key={index} className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                        <h4 className="font-semibold text-gray-900 mb-2">카드 {card.card_number || index + 1}</h4>
                        <h5 className="font-medium text-blue-600 mb-2">{card.title}</h5>
                        <p className="text-sm text-gray-700 mb-2">{card.main_text?.slice(0, 100)}...</p>
                        <div className="text-lg font-bold text-purple-600">{card.key_figure}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="prose max-w-none">
                    <pre className="whitespace-pre-wrap text-sm text-gray-700">
                      {analysisData.analysis.card_news.raw_response || '카드뉴스 데이터가 없습니다.'}
                    </pre>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 메타데이터 */}
      <div className="mt-8 bg-gray-50 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">📋 통계 메타정보</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <span className="font-medium text-gray-600">제목:</span>
            <p className="text-gray-800 mt-1">{analysisData.metadata.title || 'N/A'}</p>
          </div>
          <div>
            <span className="font-medium text-gray-600">담당부서:</span>
            <p className="text-gray-800 mt-1">{analysisData.metadata.department || 'N/A'}</p>
          </div>
          <div>
            <span className="font-medium text-gray-600">작성목적:</span>
            <p className="text-gray-800 mt-1">{analysisData.metadata.purpose || 'N/A'}</p>
          </div>
          <div>
            <span className="font-medium text-gray-600">작성주기:</span>
            <p className="text-gray-800 mt-1">{analysisData.metadata.frequency || 'N/A'}</p>
          </div>
        </div>
      </div>
    </div>
  );
};