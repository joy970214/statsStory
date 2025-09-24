import React, { useState, useEffect } from 'react';
import { statsAPI } from '../services/api';
import { motion } from 'framer-motion';
import { 
  ClipboardDocumentListIcon,
  ArrowLeftIcon,
  ChartBarIcon,
  TrashIcon,
  ArrowTopRightOnSquareIcon,
  SparklesIcon,
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
      <motion.div 
        className="min-h-screen flex items-center justify-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.5 }}
      >
        <div className="text-center">
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
            수집된 통계표 목록을 불러오는 중...
          </motion.p>
        </div>
      </motion.div>
    );
  }

  if (error) {
    return (
      <motion.div 
        className="bg-red-50 border border-red-200 rounded-xl p-6 shadow-lg"
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
      >
        <div className="flex items-start gap-3">
          <ExclamationTriangleIcon className="w-6 h-6 text-red-500 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <h3 className="text-lg font-semibold text-red-800 mb-2">오류 발생</h3>
            <p className="text-red-700 mb-4">{error}</p>
            <div className="flex gap-3">
              <button
                onClick={loadCollectedStats}
                className="bg-gradient-to-r from-red-500 to-red-600 text-white px-6 py-3 rounded-lg hover:from-red-600 hover:to-red-700 transition-all duration-200 shadow-lg hover:shadow-xl flex items-center gap-2"
              >
                <ArrowPathIcon className="w-4 h-4" />
                다시 시도
              </button>
              <button
                onClick={onBack}
                className="bg-gray-300 text-gray-700 px-6 py-3 rounded-lg hover:bg-gray-400 transition-all duration-200 flex items-center gap-2"
              >
                <ArrowLeftIcon className="w-4 h-4" />
                뒤로 가기
              </button>
            </div>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <div>
      {/* 헤더 */}
      <motion.div 
        className="mb-8"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold bg-gradient-to-r from-primary-600 to-primary-800 bg-clip-text text-transparent mb-3 flex items-center gap-3">
              <ClipboardDocumentListIcon className="w-8 h-8 text-primary-600" />
              수집된 통계표 목록
            </h2>
            <p className="text-gray-600 text-lg">
              시스템에 저장된 <span className="font-semibold text-primary-600">{statsData?.total_collected_stats || 0}개</span>의 통계표를 실제 통계표명으로 확인하고 분석할 수 있습니다.
            </p>
          </div>
          <button
            onClick={onBack}
            className="bg-gradient-to-r from-gray-500 to-gray-600 text-white px-6 py-3 rounded-lg hover:from-gray-600 hover:to-gray-700 transition-all duration-200 shadow-lg hover:shadow-xl flex items-center gap-2"
          >
            <ArrowLeftIcon className="w-5 h-5" />
            뒤로 가기
          </button>
        </div>
      </motion.div>

      {/* 통계 요약 */}
      {statsData && (
        <motion.div 
          className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <motion.div 
            className="bg-gradient-to-br from-blue-50 to-blue-100 border border-blue-200 rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-300"
            whileHover={{ scale: 1.02 }}
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center">
                <ClipboardDocumentListIcon className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-blue-800">총 통계표</h3>
            </div>
            <p className="text-3xl font-bold text-blue-600">{statsData.total_collected_stats}</p>
          </motion.div>
          
          <motion.div 
            className="bg-gradient-to-br from-green-50 to-green-100 border border-green-200 rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-300"
            whileHover={{ scale: 1.02 }}
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center">
                <ChartBarIcon className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-green-800">총 데이터 포인트</h3>
            </div>
            <p className="text-3xl font-bold text-green-600">
              {statsData.stats.reduce((sum, stat) => sum + stat.total_data_points, 0).toLocaleString()}
            </p>
          </motion.div>
          
          <motion.div 
            className="bg-gradient-to-br from-purple-50 to-purple-100 border border-purple-200 rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-300"
            whileHover={{ scale: 1.02 }}
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center">
                <DocumentTextIcon className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-purple-800">평균 필드 수</h3>
            </div>
            <p className="text-3xl font-bold text-purple-600">
              {statsData.stats.length > 0
                ? Math.round(statsData.stats.reduce((sum, stat) => sum + stat.data_fields_info.total_fields, 0) / statsData.stats.length)
                : 0
              }
            </p>
          </motion.div>
          
          <motion.div 
            className="bg-gradient-to-br from-amber-50 to-amber-100 border border-amber-200 rounded-xl p-6 shadow-lg hover:shadow-xl transition-all duration-300"
            whileHover={{ scale: 1.02 }}
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 bg-gradient-to-br from-amber-500 to-amber-600 rounded-xl flex items-center justify-center">
                <CalendarIcon className="w-5 h-5 text-white" />
              </div>
              <h3 className="text-lg font-semibold text-amber-800">최근 수집</h3>
            </div>
            <p className="text-sm font-medium text-amber-600">
              {statsData.stats.length > 0
                ? formatDate(statsData.stats[0].saved_at)
                : 'N/A'
              }
            </p>
          </motion.div>
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
              className="bg-white border border-gray-200 rounded-xl shadow-lg hover:shadow-2xl transition-all duration-300 p-6 group"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
              whileHover={{ scale: 1.01 }}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-3 mb-4">
                    <h3 className="text-xl font-semibold text-gray-900 group-hover:text-primary-700 transition-colors duration-200">
                      {stat.stat_name}
                    </h3>
                    <span className="bg-gradient-to-r from-primary-100 to-primary-200 text-primary-800 text-xs font-medium px-3 py-1.5 rounded-full flex items-center gap-1">
                      <TagIcon className="w-3 h-3" />
                      {stat.department}
                    </span>
                  </div>

                  {/* 키워드 */}
                  {stat.keywords && stat.keywords.length > 0 && (
                    <div className="flex flex-wrap gap-2 mb-4">
                      {stat.keywords.map((keyword, idx) => (
                        <span
                          key={idx}
                          className="bg-gray-100 text-gray-700 text-xs px-3 py-1.5 rounded-full font-medium hover:bg-gray-200 transition-colors duration-200"
                        >
                          {keyword}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* 데이터 정보 */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div className="bg-blue-50 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        <span className="text-xs text-gray-600">총 데이터</span>
                      </div>
                      <span className="text-lg font-bold text-blue-600">
                        {stat.total_data_points.toLocaleString()}개
                      </span>
                    </div>
                    <div className="bg-purple-50 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                        <span className="text-xs text-gray-600">총 필드</span>
                      </div>
                      <span className="text-lg font-bold text-purple-600">
                        {stat.data_fields_info.total_fields}개
                      </span>
                    </div>
                    <div className="bg-green-50 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span className="text-xs text-gray-600">숫자 데이터</span>
                      </div>
                      <span className="text-lg font-bold text-green-600">
                        {stat.data_fields_info.numeric_fields}개
                      </span>
                    </div>
                    <div className="bg-teal-50 rounded-lg p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <div className="w-2 h-2 bg-teal-500 rounded-full"></div>
                        <span className="text-xs text-gray-600">텍스트 데이터</span>
                      </div>
                      <span className="text-lg font-bold text-teal-600">
                        {stat.data_fields_info.text_fields}개
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

                <div className="flex flex-col space-y-3 ml-6">
                  <button
                    onClick={() => onSelectStat(stat.stat_name)}
                    className="bg-gradient-to-r from-primary-500 to-primary-600 text-white px-6 py-3 rounded-lg hover:from-primary-600 hover:to-primary-700 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 text-sm font-medium whitespace-nowrap flex items-center gap-2"
                  >
                    <ChartBarIcon className="w-4 h-4" />
                    상세 분석
                  </button>
                  <button
                    onClick={() => window.open(stat.stat_url, '_blank')}
                    className="bg-gradient-to-r from-gray-500 to-gray-600 text-white px-6 py-3 rounded-lg hover:from-gray-600 hover:to-gray-700 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 text-sm font-medium whitespace-nowrap flex items-center gap-2"
                  >
                    <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                    원본 보기
                  </button>
                  <button
                    onClick={() => deleteStat(stat.cache_key, stat.stat_name)}
                    className="bg-gradient-to-r from-red-500 to-red-600 text-white px-6 py-3 rounded-lg hover:from-red-600 hover:to-red-700 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 text-sm font-medium whitespace-nowrap flex items-center gap-2"
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