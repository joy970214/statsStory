import React, { useState, useEffect } from 'react';
import { statsAPI } from '../services/api';

interface StatInfo {
  stat_name: string;
  cache_key: string;
  stat_url: string;
  department: string;
  keywords: string[];
  total_data_points: number;
  data_fields_info: {
    total_fields: number;
    numeric_fields: number;
    text_fields: number;
  };
  table_names: string[];
  saved_at: string;
}

interface CollectedStatsListResponse {
  total_collected_stats: number;
  stats: StatInfo[];
}

interface Props {
  onSelectStat: (statName: string) => void;
  onBack: () => void;
}

export const CollectedStatsViewer: React.FC<Props> = ({ onSelectStat, onBack }) => {
  const [loading, setLoading] = useState(true);
  const [statsData, setStatsData] = useState<CollectedStatsListResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadCollectedStats();
  }, []);

  const loadCollectedStats = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('수집된 통계표 목록 API 호출 시작...');

      const response = await fetch('/api/stats-list');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('수집된 통계표 목록 응답:', data);
      setStatsData(data);
    } catch (err) {
      console.error('수집된 통계표 목록 로드 오류:', err);
      setError(`통계표 목록을 불러오는데 실패했습니다: ${err instanceof Error ? err.message : '알 수 없는 오류'}`);
    } finally {
      setLoading(false);
    }
  };

  const deleteStat = async (cacheKey: string, statName: string) => {
    if (!window.confirm(`정말로 '${statName}' 통계표를 삭제하시겠습니까?\n\n삭제된 데이터는 복구할 수 없습니다.`)) {
      return;
    }

    try {
      console.log(`통계표 삭제 시작: ${cacheKey}`);

      const response = await fetch(`/api/stats/${cacheKey}`, {
        method: 'DELETE',
      });

      const result = await response.json();

      if (response.ok && result.success) {
        alert(`✅ ${result.message}`);
        // 목록 새로고침
        await loadCollectedStats();
      } else {
        throw new Error(result.message || '삭제 실패');
      }
    } catch (err) {
      console.error('통계표 삭제 오류:', err);
      alert(`❌ 통계표 삭제 중 오류가 발생했습니다: ${err instanceof Error ? err.message : '알 수 없는 오류'}`);
    }
  };

  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('ko-KR', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    } catch {
      return dateString;
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">수집된 통계표 목록을 불러오는 중...</p>
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
            onClick={loadCollectedStats}
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

  return (
    <div>
      {/* 헤더 */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              📋 수집된 통계표 목록
            </h2>
            <p className="text-gray-600">
              시스템에 저장된 {statsData?.total_collected_stats || 0}개의 통계표를 실제 통계표명으로 확인하고 분석할 수 있습니다.
            </p>
          </div>
          <button
            onClick={onBack}
            className="bg-gray-500 text-white px-4 py-2 rounded-md hover:bg-gray-600"
          >
            뒤로 가기
          </button>
        </div>
      </div>

      {/* 통계 요약 */}
      {statsData && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-blue-800">총 통계표</h3>
            <p className="text-2xl font-bold text-blue-600">{statsData.total_collected_stats}</p>
          </div>
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-green-800">총 데이터 포인트</h3>
            <p className="text-2xl font-bold text-green-600">
              {statsData.stats.reduce((sum, stat) => sum + stat.total_data_points, 0).toLocaleString()}
            </p>
          </div>
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-purple-800">평균 필드 수</h3>
            <p className="text-2xl font-bold text-purple-600">
              {statsData.stats.length > 0
                ? Math.round(statsData.stats.reduce((sum, stat) => sum + stat.data_fields_info.total_fields, 0) / statsData.stats.length)
                : 0
              }
            </p>
          </div>
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
            <h3 className="text-lg font-semibold text-orange-800">최근 수집</h3>
            <p className="text-sm font-medium text-orange-600">
              {statsData.stats.length > 0
                ? formatDate(statsData.stats[0].saved_at)
                : 'N/A'
              }
            </p>
          </div>
        </div>
      )}

      {/* 통계표 목록 */}
      {statsData && statsData.stats.length === 0 ? (
        <div className="text-center py-12">
          <p className="text-gray-500 text-lg">수집된 통계표가 없습니다.</p>
          <p className="text-gray-400 mt-2">먼저 통계 분석을 실행하여 데이터를 수집해주세요.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {statsData?.stats.map((stat, index) => (
            <div
              key={stat.cache_key}
              className="bg-white border border-gray-200 rounded-lg shadow-sm hover:shadow-md transition-shadow p-6"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-3">
                    <h3 className="text-lg font-semibold text-gray-900">
                      {stat.stat_name}
                    </h3>
                    <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded-full">
                      {stat.department}
                    </span>
                  </div>

                  {/* 키워드 */}
                  {stat.keywords && stat.keywords.length > 0 && (
                    <div className="flex flex-wrap gap-1 mb-3">
                      {stat.keywords.map((keyword, idx) => (
                        <span
                          key={idx}
                          className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded"
                        >
                          {keyword}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* 데이터 정보 */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-3">
                    <div className="text-sm">
                      <span className="text-gray-500">총 데이터:</span>
                      <span className="font-medium text-gray-900 ml-1">
                        {stat.total_data_points.toLocaleString()}개
                      </span>
                    </div>
                    <div className="text-sm">
                      <span className="text-gray-500">총 필드:</span>
                      <span className="font-medium text-gray-900 ml-1">
                        {stat.data_fields_info.total_fields}개
                      </span>
                    </div>
                    <div className="text-sm">
                      <span className="text-gray-500">숫자 데이터:</span>
                      <span className="font-medium text-green-600 ml-1">
                        {stat.data_fields_info.numeric_fields}개
                      </span>
                    </div>
                    <div className="text-sm">
                      <span className="text-gray-500">텍스트 데이터:</span>
                      <span className="font-medium text-blue-600 ml-1">
                        {stat.data_fields_info.text_fields}개
                      </span>
                    </div>
                  </div>

                  {/* 테이블 이름 */}
                  {stat.table_names && stat.table_names.length > 0 && (
                    <div className="mb-3">
                      <span className="text-sm text-gray-500 block mb-1">포함된 통계표:</span>
                      <div className="flex flex-wrap gap-1">
                        {stat.table_names.slice(0, 3).map((tableName, idx) => (
                          <span
                            key={idx}
                            className="bg-indigo-50 text-indigo-700 text-xs px-2 py-1 rounded border border-indigo-200"
                          >
                            {tableName}
                          </span>
                        ))}
                        {stat.table_names.length > 3 && (
                          <span className="text-xs text-gray-500 px-2 py-1">
                            +{stat.table_names.length - 3}개 더
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  <div className="text-xs text-gray-500">
                    수집 시간: {formatDate(stat.saved_at)}
                  </div>
                </div>

                <div className="flex flex-col space-y-2 ml-4">
                  <button
                    onClick={() => onSelectStat(stat.stat_name)}
                    className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 text-sm font-medium whitespace-nowrap"
                  >
                    📊 상세 분석
                  </button>
                  <button
                    onClick={() => window.open(stat.stat_url, '_blank')}
                    className="bg-gray-200 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-300 text-sm font-medium whitespace-nowrap"
                  >
                    🔗 원본 보기
                  </button>
                  <button
                    onClick={() => deleteStat(stat.cache_key, stat.stat_name)}
                    className="bg-red-500 text-white px-4 py-2 rounded-md hover:bg-red-600 text-sm font-medium whitespace-nowrap"
                    title="이 통계표의 모든 데이터를 삭제합니다"
                  >
                    🗑️ 삭제
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};