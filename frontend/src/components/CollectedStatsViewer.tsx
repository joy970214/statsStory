import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  ClipboardDocumentListIcon,
  ArrowLeftIcon,
  ChartBarIcon,
  TrashIcon,
  ArrowTopRightOnSquareIcon,
  CalendarIcon,
  TagIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';

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
      const response = await fetch('/api/stats-list');
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setStatsData(data);
    } catch (err) {
      console.error('수집된 통계 목록 로드 오류:', err);
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
      <div className="fixed inset-0 bg-white/80 z-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block w-16 h-16 border-4 border-gray-200 border-t-primary-600 rounded-full animate-spin mb-4"></div>
          <h3 className="text-lg font-semibold text-gray-800 mb-2">수집된 통계표 로딩</h3>
          <p className="text-gray-600">데이터를 불러오는 중입니다...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <div className="flex items-start gap-3">
          <ExclamationTriangleIcon className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-red-800 mb-2">오류 발생</h3>
            <p className="text-red-700 mb-4">{error}</p>
            <div className="flex gap-2">
              <button
                onClick={loadCollectedStats}
                className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 transition-colors flex items-center gap-2 text-sm font-medium"
              >
                <ArrowPathIcon className="w-4 h-4" />
                다시 시도
              </button>
              <button
                onClick={onBack}
                className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-50 transition-colors flex items-center gap-2 text-sm font-medium"
              >
                <ArrowLeftIcon className="w-4 h-4" />
                뒤로 가기
              </button>
            </div>
          </div>
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
            <h2 className="text-2xl font-bold text-gray-900 mb-2 flex items-center gap-3">
              <ClipboardDocumentListIcon className="w-7 h-7 text-primary-600" />
              수집된 통계 목록
            </h2>
            <p className="text-gray-600">
              시스템에 저장된 <span className="font-semibold text-primary-600">{statsData?.total_collected_stats || 0}개</span>의 통계를 확인하고 분석할 수 있습니다.
            </p>
          </div>
          <button
            onClick={onBack}
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-50 transition-colors flex items-center gap-2 text-sm font-medium"
          >
            <ArrowLeftIcon className="w-4 h-4" />
            뒤로 가기
          </button>
        </div>
      </div>

      {/* 통계 요약 */}
      {statsData && (
        <motion.div 
          className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <ClipboardDocumentListIcon className="w-5 h-5 text-blue-600" />
              <h3 className="text-base font-semibold text-gray-900">총 통계</h3>
            </div>
            <p className="text-2xl font-bold text-blue-600">{statsData.total_collected_stats}</p>
          </div>
          
          <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <DocumentTextIcon className="w-5 h-5 text-indigo-600" />
              <h3 className="text-base font-semibold text-gray-900">총 통계표</h3>
            </div>
            <p className="text-2xl font-bold text-indigo-600">
              {statsData.stats.reduce((sum, stat) => sum + (stat.table_names?.length || 0), 0).toLocaleString()}
            </p>
          </div>
          
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <ChartBarIcon className="w-5 h-5 text-green-600" />
              <h3 className="text-base font-semibold text-gray-900">총 데이터 포인트</h3>
            </div>
            <p className="text-2xl font-bold text-green-600">
              {statsData.stats.reduce((sum, stat) => sum + stat.total_data_points, 0).toLocaleString()}
            </p>
          </div>
          
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
              <CalendarIcon className="w-5 h-5 text-amber-600" />
              <h3 className="text-base font-semibold text-gray-900">최근 수집</h3>
            </div>
            <p className="text-base font-semibold text-amber-700">
              {statsData.stats.length > 0
                ? formatDate(statsData.stats[0].saved_at)
                : '수집데이터 없음'
              }
            </p>
          </div>
        </motion.div>
      )}

      {/* 통계표 목록 */}
      {statsData && statsData.stats.length === 0 ? (
        <motion.div 
          className="text-center py-12"
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <ClipboardDocumentListIcon className="w-10 h-10 text-gray-400" />
          </div>
          <p className="text-gray-500 text-lg font-medium">수집된 통계표가 없습니다.</p>
          <p className="text-gray-400 mt-2">먼저 통계 분석을 실행하여 데이터를 수집해주세요.</p>
        </motion.div>
      ) : (
        <motion.div 
          className="space-y-6"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          {statsData?.stats.map((stat, index) => (
            <motion.div
              key={stat.cache_key}
              className="bg-white border border-gray-200 rounded-lg shadow p-6"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-4">
                    <h3 className="text-xl font-semibold text-gray-900">
                      {stat.stat_name}
                    </h3>
                    <span className="bg-blue-100 text-blue-800 text-xs font-medium px-3 py-1.5 rounded-full flex items-center gap-1 border border-blue-300">
                      <TagIcon className="w-3 h-3" />
                      {stat.department}
                    </span>
                  </div>

                  {/* 데이터 정보 */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        <span className="text-xs text-gray-600">총 데이터</span>
                      </div>
                      <span className="text-lg font-bold text-blue-600">
                        {stat.total_data_points.toLocaleString()}개
                      </span>
                    </div>
                    <div className="bg-cyan-50 border border-cyan-200 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 bg-cyan-500 rounded-full"></div>
                        <span className="text-xs text-gray-600">총 필드</span>
                      </div>
                      <span className="text-lg font-bold text-cyan-600">
                        {stat.data_fields_info.total_fields.toLocaleString()}개
                      </span>
                    </div>
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span className="text-xs text-gray-600">숫자 데이터</span>
                      </div>
                      <span className="text-lg font-bold text-green-600">
                        {stat.data_fields_info.numeric_fields.toLocaleString()}개
                      </span>
                    </div>
                    <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                        <span className="text-xs text-gray-600">텍스트 데이터</span>
                      </div>
                      <span className="text-lg font-bold text-purple-600">
                        {stat.data_fields_info.text_fields.toLocaleString()}개
                      </span>
                    </div>
                  </div>

                  {/* 테이블 이름 */}
                  {stat.table_names && stat.table_names.length > 0 && (
                    <div className="mb-4">
                      <span className="text-sm font-medium text-gray-700 block mb-2">포함된 통계표:</span>
                      <div className="flex flex-wrap gap-2">
                        {stat.table_names.slice(0, 3).map((tableName, idx) => (
                          <span
                            key={idx}
                            className="bg-indigo-50 text-indigo-700 text-xs px-3 py-1.5 rounded-full border border-indigo-200 font-medium"
                          >
                            {tableName}
                          </span>
                        ))}
                        {stat.table_names.length > 3 && (
                          <span className="text-xs text-gray-500 px-3 py-1.5 bg-gray-100 rounded-full">
                            +{stat.table_names.length - 3}개 더
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <CalendarIcon className="w-4 h-4" />
                    <span>수집 시간: {formatDate(stat.saved_at)}</span>
                  </div>
                </div>

                <div className="flex flex-col space-y-2 ml-6">
                  <button
                    onClick={() => onSelectStat(stat.stat_name)}
                    className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors text-sm font-medium whitespace-nowrap flex items-center gap-2"
                  >
                    <ChartBarIcon className="w-4 h-4" />
                    상세 분석
                  </button>
                  <button
                    onClick={() => window.open(stat.stat_url, '_blank')}
                    className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-50 transition-colors text-sm font-medium whitespace-nowrap flex items-center gap-2"
                  >
                    <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                    원본
                  </button>
                  <button
                    onClick={() => deleteStat(stat.cache_key, stat.stat_name)}
                    className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700 transition-colors text-sm font-medium whitespace-nowrap flex items-center gap-2"
                    title="이 통계표의 모든 데이터를 삭제합니다"
                  >
                    <TrashIcon className="w-4 h-4" />
                    삭제
                  </button>
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
};

export default CollectedStatsViewer;