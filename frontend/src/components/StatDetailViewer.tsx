import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  ChartBarIcon,
  ArrowLeftIcon,
  ArrowPathIcon,
  ExclamationTriangleIcon,
  DocumentChartBarIcon,
  TableCellsIcon,
  TagIcon
} from '@heroicons/react/24/outline';
import { API_ORIGIN } from '../services/api';

interface TableDetail {
  total_records: number;
  year_range: {
    min_year: number | null;
    max_year: number | null;
  };
  data_fields: {
    total_fields: number;
    numeric_fields: string[];
    text_fields: string[];
    numeric_count: number;
    text_count: number;
  };
  sample_data: Array<{
    sample_index: number;
    year: number;
    data_preview: Record<string, {
      value: any;
      type: 'numeric' | 'text';
    }>;
  }>;
}

interface StatDetailResponse {
  stat_name: string;
  stat_url: string;
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
  total_data_points: number;
  tables_detail: Record<string, TableDetail>;
}

interface Props {
  statName: string;
  onBack: () => void;
  onViewDistribution: (statName: string) => void;
  onViewSummary: (statName: string) => void;
}

export const StatDetailViewer: React.FC<Props> = ({
  statName,
  onBack,
  onViewDistribution,
  onViewSummary
}) => {
  const [loading, setLoading] = useState(true);
  const [detailData, setDetailData] = useState<StatDetailResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);

  useEffect(() => {
    loadStatDetail();
  }, [statName]);

  const loadStatDetail = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await fetch(`${API_ORIGIN}/api/stats-detail/${encodeURIComponent(statName)}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setDetailData(data);

      // 첫 번째 테이블을 기본 선택
      const tableNames = Object.keys(data.tables_detail);
      if (tableNames.length > 0) {
        setSelectedTable(tableNames[0]);
      }
    } catch (err) {
      setError(`상세 정보를 불러오는데 실패했습니다: ${err instanceof Error ? err.message : '알 수 없는 오류'}`);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-white/80 z-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block w-16 h-16 border-4 border-gray-200 border-t-primary-600 rounded-full animate-spin mb-4"></div>
          <h3 className="text-lg font-semibold text-gray-800 mb-2">통계 상세 정보 로딩</h3>
          <p className="text-gray-600">'{statName}' 데이터를 불러오는 중...</p>
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
                onClick={loadStatDetail}
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

  if (!detailData) return null;

  const selectedTableData = selectedTable ? detailData.tables_detail[selectedTable] : null;

  return (
    <div>
      {/* 헤더 */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2 flex items-center gap-3">
              <DocumentChartBarIcon className="w-7 h-7 text-primary-600" />
              {detailData.stat_name}
            </h2>
            <p className="text-gray-600 mb-3">
              {detailData.metadata.title} - {detailData.metadata.department}
            </p>

            {/* 키워드 */}
            {detailData.metadata.keywords && detailData.metadata.keywords.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {detailData.metadata.keywords.map((keyword, idx) => (
                  <span
                    key={idx}
                    className="bg-blue-50 text-blue-700 text-xs font-medium px-3 py-1.5 rounded-full border border-blue-200 flex items-center gap-1"
                  >
                    <TagIcon className="w-3 h-3" />
                    {keyword}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="flex flex-col gap-2">
            <button
              onClick={() => onViewDistribution(statName)}
              className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700 text-sm font-medium transition-colors flex items-center gap-2 whitespace-nowrap"
            >
              <ChartBarIcon className="w-4 h-4" />
              분포 특성 분석
            </button>
            <button
              onClick={() => onViewSummary(statName)}
              className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700 text-sm font-medium transition-colors flex items-center gap-2 whitespace-nowrap"
            >
              <TableCellsIcon className="w-4 h-4" />
              객관적 현황 요약
            </button>
            <button
              onClick={onBack}
              className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-50 text-sm font-medium transition-colors flex items-center gap-2"
            >
              <ArrowLeftIcon className="w-4 h-4" />
              뒤로 가기
            </button>
          </div>
        </div>
      </div>

      {/* 메타데이터 정보 */}
      <motion.div 
        className="bg-white rounded-lg shadow border border-gray-200 p-6 mb-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
      >
        <h3 className="text-lg font-semibold text-gray-900 mb-3">통계정보 상세</h3>

        {/* 기본 정보 - 콤팩트하게 */}
        <div className="space-y-2">
          <div className="flex items-start">
            <span className="text-sm font-medium text-gray-600 min-w-[80px]">제목:</span>
            <p className="text-sm text-gray-900 flex-1">{detailData.metadata?.title || '정보 없음'}</p>
          </div>
          <div className="flex items-start">
            <span className="text-sm font-medium text-gray-600 min-w-[80px]">작성기관:</span>
            <p className="text-sm text-gray-700 flex-1">{detailData.metadata?.department || '정보 없음'}</p>
          </div>
          <div className="flex items-start">
            <span className="text-sm font-medium text-gray-600 min-w-[80px]">키워드:</span>
            <div className="flex flex-wrap gap-1 flex-1">
              {(detailData.metadata?.keywords || []).map((keyword, index) => (
                <span key={index} className="bg-primary-100 text-primary-800 px-2 py-0.5 rounded-full text-xs">
                  {keyword}
                </span>
              ))}
            </div>
          </div>
        </div>

      </motion.div>

      {/* 용어정리 - 콤팩트하게 */}
      {((detailData.metadata?.terminology && Object.keys(detailData.metadata.terminology).length > 0) ||
        (detailData.metadata?.related_terms && Object.keys(detailData.metadata.related_terms).length > 0)) && (
        <motion.div 
          className="bg-white rounded-lg shadow border border-gray-200 p-6 mb-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          <h3 className="text-lg font-semibold text-gray-900 mb-4">용어정리</h3>

          {/* 수집된 관련용어 탭 정보 (terminology) */}
          {detailData.metadata?.terminology && Object.keys(detailData.metadata.terminology).length > 0 && (
            <div className="mb-4 last:mb-0">
              <h4 className="text-sm font-medium text-warning-700 mb-2 flex items-center">
                <span className="bg-warning-100 text-warning-700 px-2 py-0.5 rounded text-xs">수집된 관련용어</span>
              </h4>
              <div className="bg-warning-50 rounded-lg p-3">
                <div className="bg-white rounded-md p-3 space-y-1.5">
                  {Object.entries(detailData.metadata.terminology).map(([key, value], index) => (
                    <div key={index} className="flex items-start gap-2">
                      <span className="text-sm font-medium text-warning-700 min-w-[100px] flex-shrink-0">{key}:</span>
                      <span className="text-sm text-gray-900 flex-1">{value || '-'}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* 기존 관련용어 정보 */}
          {detailData.metadata?.related_terms && Object.keys(detailData.metadata.related_terms).length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-secondary-700 mb-2 flex items-center">
                <span className="bg-secondary-100 text-secondary-700 px-2 py-0.5 rounded text-xs">기본 관련용어</span>
              </h4>
              <div className="bg-secondary-50 rounded-lg p-3">
                <div className="bg-white rounded-md p-3 space-y-1.5">
                  {Object.entries(detailData.metadata.related_terms).map(([key, value], index) => (
                    <div key={index} className="flex items-start gap-2">
                      <span className="text-sm font-medium text-secondary-700 min-w-[100px] flex-shrink-0">{key}:</span>
                      <span className="text-sm text-gray-900 flex-1">{value || '-'}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* 전체 요약 */}
      <motion.div 
        className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.3 }}
      >
        <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <TableCellsIcon className="w-5 h-5 text-indigo-600" />
            <h3 className="text-base font-semibold text-gray-900">총 통계표</h3>
          </div>
          <p className="text-2xl font-bold text-indigo-600">{detailData.total_tables}</p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <ChartBarIcon className="w-5 h-5 text-green-600" />
            <h3 className="text-base font-semibold text-gray-900">총 데이터 포인트</h3>
          </div>
          <p className="text-2xl font-bold text-green-600">{detailData.total_data_points.toLocaleString()}</p>
        </div>
        <div className="bg-cyan-50 border border-cyan-200 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-2">
            <DocumentChartBarIcon className="w-5 h-5 text-cyan-600" />
            <h3 className="text-base font-semibold text-gray-900">전체 필드 수</h3>
          </div>
          <p className="text-2xl font-bold text-cyan-600">
            {Object.values(detailData.tables_detail).reduce((sum, table) => sum + table.data_fields.total_fields, 0).toLocaleString()}
          </p>
        </div>
      </motion.div>

      {/* 테이블 선택 탭 */}
      <motion.div 
        className="mb-6"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.4 }}
      >
        <h3 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
          <TableCellsIcon className="w-5 h-5 text-primary-600" />
          통계표별 상세 정보
        </h3>
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 overflow-x-auto">
            {Object.keys(detailData.tables_detail).map((tableName) => (
              <button
                key={tableName}
                onClick={() => setSelectedTable(tableName)}
                className={`py-3 px-1 border-b-2 font-medium text-sm whitespace-nowrap transition-colors ${
                  selectedTable === tableName
                    ? 'border-primary-500 text-primary-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tableName}
              </button>
            ))}
          </nav>
        </div>
      </motion.div>

      {/* 선택된 테이블 상세 정보 */}
      {selectedTableData && (
        <motion.div 
          className="space-y-6"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          key={selectedTable}
        >
          {/* 기본 정보 */}
          <div className="bg-white border border-gray-200 rounded-lg shadow p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">기본 정보</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <span className="text-xs text-gray-600 block mb-1">총 레코드</span>
                <p className="text-lg font-bold text-blue-600">{selectedTableData.total_records.toLocaleString()}개</p>
              </div>
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                <span className="text-xs text-gray-600 block mb-1">연도 범위</span>
                <p className="text-lg font-bold text-amber-600">
                  {selectedTableData.year_range.min_year && selectedTableData.year_range.max_year
                    ? `${selectedTableData.year_range.min_year} - ${selectedTableData.year_range.max_year}`
                    : 'N/A'
                  }
                </p>
              </div>
              <div className="bg-cyan-50 border border-cyan-200 rounded-lg p-3">
                <span className="text-xs text-gray-600 block mb-1">총 필드</span>
                <p className="text-lg font-bold text-cyan-600">{selectedTableData.data_fields.total_fields.toLocaleString()}개</p>
              </div>
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                <span className="text-xs text-gray-600 block mb-1">숫자/텍스트</span>
                <p className="text-lg font-bold text-purple-600">
                  <span className="text-green-600">{selectedTableData.data_fields.numeric_count.toLocaleString()}</span>
                  /
                  <span className="text-blue-600">{selectedTableData.data_fields.text_count.toLocaleString()}</span>
                </p>
              </div>
            </div>
          </div>

          {/* 데이터 필드 정보 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* 숫자 필드 */}
            <div className="bg-green-50 border border-green-200 rounded-lg shadow p-6">
              <h4 className="text-lg font-semibold text-green-800 mb-3">
                숫자 데이터 필드 ({selectedTableData.data_fields.numeric_count.toLocaleString()}개)
              </h4>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {selectedTableData.data_fields.numeric_fields.map((field, idx) => (
                  <span
                    key={idx}
                    className="inline-block bg-green-100 text-green-700 text-sm px-2 py-1 rounded-md mr-1 mb-1 border border-green-200"
                  >
                    {field}
                  </span>
                ))}
              </div>
            </div>

            {/* 텍스트 필드 */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg shadow p-6">
              <h4 className="text-lg font-semibold text-blue-800 mb-3">
                텍스트 데이터 필드 ({selectedTableData.data_fields.text_count.toLocaleString()}개)
              </h4>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {selectedTableData.data_fields.text_fields.map((field, idx) => (
                  <span
                    key={idx}
                    className="inline-block bg-blue-100 text-blue-700 text-sm px-2 py-1 rounded-md mr-1 mb-1 border border-blue-200"
                  >
                    {field}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* 샘플 데이터 */}
          <div className="bg-white border border-gray-200 rounded-lg shadow p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">샘플 데이터</h4>
            <div className="space-y-4">
              {selectedTableData.sample_data.map((sample, idx) => (
                <div key={idx} className="border border-gray-200 rounded-lg p-4 bg-gray-50">
                  <div className="flex items-center justify-between mb-3">
                    <h5 className="font-medium text-gray-900">
                      샘플 #{sample.sample_index}
                    </h5>
                    <span className="bg-blue-100 text-blue-700 text-sm font-medium px-3 py-1 rounded-full border border-blue-200">
                      {sample.year}년
                    </span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {Object.entries(sample.data_preview).map(([field, info]) => (
                      <div key={field} className="bg-white p-3 rounded-md border border-gray-200">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-gray-700 truncate" title={field}>
                            {field}
                          </span>
                          <span className={`text-xs px-1.5 py-0.5 rounded-full font-medium ${
                            info.type === 'numeric'
                              ? 'bg-green-100 text-green-700 border border-green-200'
                              : 'bg-blue-100 text-blue-700 border border-blue-200'
                          }`}>
                            {info.type}
                          </span>
                        </div>
                        <p className="text-sm text-gray-900 font-mono break-all">
                          {typeof info.value === 'object' ? JSON.stringify(info.value) : String(info.value)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      )}

      {/* 관련 용어 */}
      {detailData.metadata.related_terms && Object.keys(detailData.metadata.related_terms).length > 0 && (
        <div className="mt-8 bg-white border border-gray-200 rounded-lg p-6">
          <h4 className="text-lg font-semibold text-gray-900 mb-4">관련 용어 정의</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {Object.entries(detailData.metadata.related_terms).map(([term, definition], idx) => (
              <div key={idx} className="border border-gray-100 rounded p-3">
                <h5 className="font-medium text-gray-900 mb-1">{term}</h5>
                <p className="text-sm text-gray-600">{definition}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default StatDetailViewer;