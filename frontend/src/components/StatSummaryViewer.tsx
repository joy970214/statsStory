import React, { useState, useEffect } from 'react';
import { API_ORIGIN } from '../services/api';

interface KeyMetrics {
  total_records: number;
  year_span: number;
  field_count: number;
  numeric_field_count: number;
  data_completeness: number;
  key_numeric_fields: string[];
}

interface TableSummary {
  objective_summary: string;
  key_metrics: KeyMetrics;
  data_insights: string[];
}

interface StatSummaryResponse {
  stat_name: string;
  analysis_type: string;
  metadata: {
    title: string;
    department: string;
    keywords: string[];
    purpose?: string;
    frequency?: string;
    contact?: string;
    search_field?: string;
    responsible_department?: string;
    statistical_info?: Record<string, any>;
    major_items?: Record<string, any>;
    meaning_analysis?: Record<string, any>;
    terminology?: Record<string, any>;
    related_terms?: Record<string, any>;
  };
  total_tables: number;
  analysis_date: string;
  table_summaries: Record<string, TableSummary>;
}

interface Props {
  statName: string;
  onBack: () => void;
}

export const StatSummaryViewer: React.FC<Props> = ({ statName, onBack }) => {
  const [loading, setLoading] = useState(true);
  const [summaryData, setSummaryData] = useState<StatSummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);

  useEffect(() => {
    loadObjectiveSummary();
  }, [statName]);

  const loadObjectiveSummary = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log(`객관적 현황 요약 API 호출: ${statName}`);

      // 1. 기본 요약 데이터 로드
      const response = await fetch(`${API_ORIGIN}/api/stats-summary/${encodeURIComponent(statName)}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const summaryResponse = await response.json();
      console.log('객관적 현황 요약 응답:', summaryResponse);

      // 2. 상세 메타데이터를 위해 기본통계분석 API도 호출
      try {
        const basicStatsResponse = await fetch(`${API_ORIGIN}/api/generate-advanced-cardnews`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            stat_name: statName,
            analysis_type: '기본통계현황분석'
          })
        });

        if (basicStatsResponse.ok) {
          const basicStatsData = await basicStatsResponse.json();
          console.log('기본통계분석 메타데이터:', basicStatsData.metadata);

          // 기본 요약 데이터에 상세 메타데이터 병합
          if (basicStatsData.metadata) {
            summaryResponse.metadata = {
              ...summaryResponse.metadata,
              ...basicStatsData.metadata
            };
          }
        }
      } catch (metadataError) {
        console.warn('상세 메타데이터 로드 실패:', metadataError);
        // 메타데이터 로드 실패해도 기본 요약은 표시
      }

      setSummaryData(summaryResponse);

      // 첫 번째 테이블을 기본 선택
      const tableNames = Object.keys(summaryResponse.table_summaries);
      if (tableNames.length > 0) {
        setSelectedTable(tableNames[0]);
      }
    } catch (err) {
      console.error('객관적 현황 요약 로드 오류:', err);
      setError(`현황 요약을 불러오는데 실패했습니다: ${err instanceof Error ? err.message : '알 수 없는 오류'}`);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-white/80 z-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block w-16 h-16 border-4 border-gray-200 border-t-primary-600 rounded-full animate-spin mb-4"></div>
          <h3 className="text-lg font-semibold text-gray-800 mb-2">객관적 현황 요약 로딩</h3>
          <p className="text-gray-600">'{statName}' 데이터를 요약하는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-6">
        <h3 className="text-lg font-medium text-red-800 mb-2">오류 발생</h3>
        <p className="text-red-700 mb-4">{error}</p>
        <div className="flex space-x-3">
          <button
            onClick={loadObjectiveSummary}
            className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700"
          >
            다시 시도
          </button>
          <button
            onClick={onBack}
            className="bg-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-400"
          >
            뒤로 가기
          </button>
        </div>
      </div>
    );
  }

  if (!summaryData) return null;

  const selectedTableData = selectedTable ? summaryData.table_summaries[selectedTable] : null;

  return (
    <div>
      {/* 헤더 */}
      <div className="mb-8">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              객관적 현황 요약
            </h2>
            <p className="text-gray-600 mb-2">
              <strong>{summaryData.stat_name}</strong>
            </p>
            <p className="text-sm text-gray-500 mb-3">
              {summaryData.metadata.title} - {summaryData.metadata.department}
            </p>
            <p className="text-xs text-gray-400">
              분석 일시: {new Date(summaryData.analysis_date).toLocaleString('ko-KR')}
            </p>

            {/* 키워드 */}
            {summaryData.metadata.keywords && summaryData.metadata.keywords.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-3">
                {summaryData.metadata.keywords.map((keyword, idx) => (
                  <span
                    key={idx}
                    className="bg-green-100 text-green-800 text-sm px-3 py-1 rounded-full"
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={onBack}
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-50 transition-colors text-sm font-medium"
          >
            뒤로 가기
          </button>
        </div>
      </div>

      {/* 메타데이터 정보 - 강제 표시 */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">메타데이터 정보</h3>
        <div className="bg-yellow-100 p-2 mb-4 rounded">
          <p className="text-sm">디버그: summaryData존재여부={summaryData ? '있음' : '없음'}, metadata존재여부={summaryData?.metadata ? '있음' : '없음'}</p>
        </div>

        {/* 기본 정보 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="space-y-3">
            <div>
              <span className="text-sm font-medium text-gray-600">제목:</span>
              <p className="text-gray-900">{summaryData.metadata?.title || '정보 없음'}</p>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-600">목적:</span>
              <p className="text-gray-700">{summaryData.metadata?.purpose || '정보 없음'}</p>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-600">주기:</span>
              <p className="text-gray-700">{summaryData.metadata?.frequency || '정보 없음'}</p>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-600">담당자:</span>
              <p className="text-gray-700">{summaryData.metadata?.contact || '정보 없음'}</p>
            </div>
          </div>
          <div className="space-y-3">
            <div>
              <span className="text-sm font-medium text-gray-600">작성기관:</span>
              <p className="text-gray-700">{summaryData.metadata?.department || '정보 없음'}</p>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-600">검색분야:</span>
              <p className="text-gray-700">{summaryData.metadata?.search_field || '정보 없음'}</p>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-600">담당부서:</span>
              <p className="text-gray-700">{summaryData.metadata?.responsible_department || '정보 없음'}</p>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-600">키워드:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {(summaryData.metadata?.keywords || []).map((keyword, index) => (
                  <span key={index} className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs">
                    {keyword}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* 상세 메타정보 탭 */}
        {(summaryData.metadata?.statistical_info || summaryData.metadata?.major_items ||
          summaryData.metadata?.meaning_analysis || summaryData.metadata?.terminology) && (
          <div className="border-t pt-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">📊 상세 메타정보</h4>

            {/* 통계정보 상세 */}
            {summaryData.metadata?.statistical_info && Object.keys(summaryData.metadata.statistical_info).length > 0 && (
              <div className="mb-6">
                <h5 className="text-md font-medium text-gray-800 mb-3 flex items-center">
                  <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded text-sm mr-2">통계정보상세</span>
                </h5>
                <div className="bg-blue-50 rounded-lg p-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {Object.entries(summaryData.metadata.statistical_info).map(([key, value], index) => (
                      <div key={index} className="flex flex-col">
                        <span className="text-xs font-medium text-blue-700">{key}</span>
                        <span className="text-sm text-blue-900">{value || '-'}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 주요항목 */}
            {summaryData.metadata?.major_items && Object.keys(summaryData.metadata.major_items).length > 0 && (
              <div className="mb-6">
                <h5 className="text-md font-medium text-gray-800 mb-3 flex items-center">
                  <span className="bg-green-100 text-green-800 px-2 py-1 rounded text-sm mr-2">주요항목</span>
                </h5>
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="space-y-2">
                    {Object.entries(summaryData.metadata.major_items).map(([key, value], index) => (
                      <div key={index} className="border-b border-green-200 pb-2 last:border-b-0">
                        <span className="text-sm font-medium text-green-800">{key}:</span>
                        <span className="text-sm text-green-700 ml-2">{value || '-'}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 의미분석 */}
            {summaryData.metadata?.meaning_analysis && Object.keys(summaryData.metadata.meaning_analysis).length > 0 && (
              <div className="mb-6">
                <h5 className="text-md font-medium text-gray-800 mb-3 flex items-center">
                  <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded text-sm mr-2">의미분석</span>
                </h5>
                <div className="bg-purple-50 rounded-lg p-4">
                  <div className="space-y-2">
                    {Object.entries(summaryData.metadata.meaning_analysis).map(([key, value], index) => (
                      <div key={index} className="border-b border-purple-200 pb-2 last:border-b-0">
                        <span className="text-sm font-medium text-purple-800">{key}:</span>
                        <span className="text-sm text-purple-700 ml-2">{value || '-'}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 용어정의 */}
            {summaryData.metadata?.terminology && Object.keys(summaryData.metadata.terminology).length > 0 && (
              <div className="mb-6">
                <h5 className="text-md font-medium text-gray-800 mb-3 flex items-center">
                  <span className="bg-orange-100 text-orange-800 px-2 py-1 rounded text-sm mr-2">용어정의</span>
                </h5>
                <div className="bg-orange-50 rounded-lg p-4">
                  <div className="space-y-2">
                    {Object.entries(summaryData.metadata.terminology).map(([key, value], index) => (
                      <div key={index} className="border-b border-orange-200 pb-2 last:border-b-0">
                        <span className="text-sm font-medium text-orange-800">{key}:</span>
                        <span className="text-sm text-orange-700 ml-2">{value || '-'}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 관련용어 */}
            {summaryData.metadata?.related_terms && Object.keys(summaryData.metadata.related_terms).length > 0 && (
              <div className="mb-6">
                <h5 className="text-md font-medium text-gray-800 mb-3 flex items-center">
                  <span className="bg-gray-100 text-gray-800 px-2 py-1 rounded text-sm mr-2">관련용어</span>
                </h5>
                <div className="bg-gray-50 rounded-lg p-4">
                  <div className="space-y-2">
                    {Object.entries(summaryData.metadata.related_terms).map(([key, value], index) => (
                      <div key={index} className="border-b border-gray-200 pb-2 last:border-b-0">
                        <span className="text-sm font-medium text-gray-800">{key}:</span>
                        <span className="text-sm text-gray-700 ml-2">{value || '-'}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 전체 요약 */}
      <div className="bg-success-50 border border-success-200 rounded-lg p-6 mb-8">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          전체 현황 개요
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="text-center">
            <p className="text-2xl font-bold text-green-600">{summaryData.total_tables}</p>
            <p className="text-sm text-gray-600">총 통계표 수</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-blue-600">
              {Object.values(summaryData.table_summaries).reduce((sum, table) => sum + table.key_metrics.total_records, 0).toLocaleString()}
            </p>
            <p className="text-sm text-gray-600">전체 데이터 레코드</p>
          </div>
          <div className="text-center">
            <p className="text-2xl font-bold text-purple-600">
              {Object.values(summaryData.table_summaries).reduce((sum, table) => sum + table.key_metrics.field_count, 0)}
            </p>
            <p className="text-sm text-gray-600">전체 데이터 필드</p>
          </div>
        </div>
      </div>

      {/* 테이블 선택 탭 */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          통계표별 상세 요약 ({summaryData.total_tables}개 테이블)
        </h3>
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 overflow-x-auto">
            {Object.keys(summaryData.table_summaries).map((tableName) => (
              <button
                key={tableName}
                onClick={() => setSelectedTable(tableName)}
                className={`py-2 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${
                  selectedTable === tableName
                    ? 'border-green-500 text-green-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tableName}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* 선택된 테이블 상세 요약 */}
      {selectedTableData && (
        <div className="space-y-6">
          {/* 객관적 요약 본문 */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <span className="mr-2">📖</span>
              객관적 현황 요약
            </h4>
            <div className="bg-gray-50 border-l-4 border-green-500 p-4 rounded-r-lg">
              <p className="text-gray-800 leading-relaxed whitespace-pre-wrap">
                {selectedTableData.objective_summary}
              </p>
            </div>
          </div>

          {/* 주요 지표 */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <span className="mr-2">🎯</span>
              주요 지표
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-center">
                <p className="text-xs text-blue-600 font-medium">총 레코드</p>
                <p className="text-lg font-bold text-blue-800">
                  {selectedTableData.key_metrics.total_records.toLocaleString()}
                </p>
              </div>
              <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-center">
                <p className="text-xs text-green-600 font-medium">년도 범위</p>
                <p className="text-lg font-bold text-green-800">
                  {selectedTableData.key_metrics.year_span}년
                </p>
              </div>
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3 text-center">
                <p className="text-xs text-purple-600 font-medium">필드 수</p>
                <p className="text-lg font-bold text-purple-800">
                  {selectedTableData.key_metrics.field_count}
                </p>
              </div>
              <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 text-center">
                <p className="text-xs text-orange-600 font-medium">숫자 필드</p>
                <p className="text-lg font-bold text-orange-800">
                  {selectedTableData.key_metrics.numeric_field_count}
                </p>
              </div>
              <div className="bg-teal-50 border border-teal-200 rounded-lg p-3 text-center">
                <p className="text-xs text-teal-600 font-medium">완성도</p>
                <p className="text-lg font-bold text-teal-800">
                  {selectedTableData.key_metrics.data_completeness.toFixed(1)}%
                </p>
              </div>
              <div className="bg-pink-50 border border-pink-200 rounded-lg p-3 text-center">
                <p className="text-xs text-pink-600 font-medium">핵심 필드</p>
                <p className="text-lg font-bold text-pink-800">
                  {selectedTableData.key_metrics.key_numeric_fields.length}
                </p>
              </div>
            </div>
          </div>

          {/* 핵심 수치 필드 */}
          {selectedTableData.key_metrics.key_numeric_fields.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
                <span className="mr-2">🔢</span>
                핵심 수치 필드
              </h4>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {selectedTableData.key_metrics.key_numeric_fields.map((field, idx) => (
                  <div key={idx} className="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
                    <p className="font-medium text-indigo-800">{field}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 데이터 인사이트 */}
          {selectedTableData.data_insights.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-lg p-6">
              <h4 className="text-lg font-semibold text-gray-900 mb-2 flex items-center">
                <span className="mr-2">💡</span>
                데이터 인사이트
              </h4>
              <p className="text-sm text-gray-600 mb-4">
                통계표: <strong>{selectedTable}</strong>
              </p>
              <div className="space-y-3">
                {selectedTableData.data_insights.map((insight, idx) => (
                  <div key={idx} className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-r-lg">
                    <p className="text-gray-800 text-sm leading-relaxed whitespace-pre-line">
                      {insight.split('. ').join('.\n')}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 종합 평가 */}
          <div className="bg-gradient-to-r from-gray-50 to-blue-50 border border-gray-200 rounded-lg p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4 flex items-center">
              <span className="mr-2">📈</span>
              종합 평가
            </h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center p-4 bg-white rounded-lg border">
                <h5 className="font-medium text-gray-800 mb-2">데이터 규모</h5>
                <p className="text-2xl font-bold text-blue-600">
                  {selectedTableData.key_metrics.total_records >= 1000 ? '대규모' :
                   selectedTableData.key_metrics.total_records >= 100 ? '중규모' : '소규모'}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {selectedTableData.key_metrics.total_records.toLocaleString()}개 레코드
                </p>
              </div>
              <div className="text-center p-4 bg-white rounded-lg border">
                <h5 className="font-medium text-gray-800 mb-2">데이터 품질</h5>
                <p className="text-2xl font-bold text-green-600">
                  {selectedTableData.key_metrics.data_completeness >= 90 ? '우수' :
                   selectedTableData.key_metrics.data_completeness >= 70 ? '양호' : '개선필요'}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  완성도 {selectedTableData.key_metrics.data_completeness.toFixed(1)}%
                </p>
              </div>
              <div className="text-center p-4 bg-white rounded-lg border">
                <h5 className="font-medium text-gray-800 mb-2">분석 적합성</h5>
                <p className="text-2xl font-bold text-purple-600">
                  {selectedTableData.key_metrics.numeric_field_count >= 5 ? '최적' :
                   selectedTableData.key_metrics.numeric_field_count >= 2 ? '적합' : '제한적'}
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  {selectedTableData.key_metrics.numeric_field_count}개 수치 필드
                </p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StatSummaryViewer;