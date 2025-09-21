import React, { useState, useEffect } from 'react';

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
      console.log(`통계표 상세 정보 API 호출: ${statName}`);

      const response = await fetch(`/api/stats-detail/${encodeURIComponent(statName)}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('통계표 상세 정보 응답:', data);
      setDetailData(data);

      // 첫 번째 테이블을 기본 선택
      const tableNames = Object.keys(data.tables_detail);
      if (tableNames.length > 0) {
        setSelectedTable(tableNames[0]);
      }
    } catch (err) {
      console.error('통계표 상세 정보 로드 오류:', err);
      setError(`상세 정보를 불러오는데 실패했습니다: ${err instanceof Error ? err.message : '알 수 없는 오류'}`);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600">'{statName}' 상세 정보를 불러오는 중...</p>
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
            onClick={loadStatDetail}
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

  if (!detailData) return null;

  const selectedTableData = selectedTable ? detailData.tables_detail[selectedTable] : null;

  return (
    <div>
      {/* 헤더 */}
      <div className="mb-8">
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              📊 {detailData.stat_name}
            </h2>
            <p className="text-gray-600 mb-3">
              {detailData.metadata.title} - {detailData.metadata.department}
            </p>

            {/* 키워드 */}
            {detailData.metadata.keywords && detailData.metadata.keywords.length > 0 && (
              <div className="flex flex-wrap gap-1 mb-4">
                {detailData.metadata.keywords.map((keyword, idx) => (
                  <span
                    key={idx}
                    className="bg-blue-100 text-blue-800 text-sm px-3 py-1 rounded-full"
                  >
                    {keyword}
                  </span>
                ))}
              </div>
            )}
          </div>

          <div className="flex space-x-3">
            <button
              onClick={() => onViewDistribution(statName)}
              className="bg-purple-600 text-white px-4 py-2 rounded-md hover:bg-purple-700"
            >
              분포 특성 분석
            </button>
            <button
              onClick={() => onViewSummary(statName)}
              className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700"
            >
              객관적 현황 요약
            </button>
            <button
              onClick={onBack}
              className="bg-gray-500 text-white px-4 py-2 rounded-md hover:bg-gray-600"
            >
              뒤로 가기
            </button>
          </div>
        </div>
      </div>

      {/* 메타데이터 정보 */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">📋 메타데이터 정보</h3>

        {/* 기본 정보 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
          <div className="space-y-3">
            <div>
              <span className="text-sm font-medium text-gray-600">제목:</span>
              <p className="text-gray-900">{detailData.metadata?.title || '정보 없음'}</p>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-600">작성기관:</span>
              <p className="text-gray-700">{detailData.metadata?.department || '정보 없음'}</p>
            </div>
          </div>
          <div className="space-y-3">
            <div>
              <span className="text-sm font-medium text-gray-600">키워드:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {(detailData.metadata?.keywords || []).map((keyword, index) => (
                  <span key={index} className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs">
                    {keyword}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* 관련용어 정보 */}
        {((detailData.metadata?.terminology && Object.keys(detailData.metadata.terminology).length > 0) ||
          (detailData.metadata?.related_terms && Object.keys(detailData.metadata.related_terms).length > 0)) && (
          <div className="border-t pt-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">📊 관련용어 정보</h4>

            {/* 수집된 관련용어 탭 정보 (terminology) */}
            {detailData.metadata?.terminology && Object.keys(detailData.metadata.terminology).length > 0 && (
              <div className="mb-6">
                <h5 className="text-md font-medium text-gray-800 mb-3 flex items-center">
                  <span className="bg-orange-100 text-orange-800 px-2 py-1 rounded text-sm mr-2">수집된 관련용어</span>
                </h5>
                <div className="bg-orange-50 rounded-lg p-4">
                  <div className="space-y-2">
                    {Object.entries(detailData.metadata.terminology).map(([key, value], index) => (
                      <div key={index} className="border-b border-orange-200 pb-2 last:border-b-0">
                        <span className="text-sm font-medium text-orange-800">{key}:</span>
                        <span className="text-sm text-orange-700 ml-2">{value || '-'}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* 기존 관련용어 정보 */}
            {detailData.metadata?.related_terms && Object.keys(detailData.metadata.related_terms).length > 0 && (
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="space-y-2">
                  {Object.entries(detailData.metadata.related_terms).map(([key, value], index) => (
                    <div key={index} className="border-b border-gray-200 pb-2 last:border-b-0">
                      <span className="text-sm font-medium text-gray-800">{key}:</span>
                      <span className="text-sm text-gray-700 ml-2">{value || '-'}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 전체 요약 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-blue-800">총 통계표</h3>
          <p className="text-2xl font-bold text-blue-600">{detailData.total_tables}</p>
        </div>
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-green-800">총 데이터 포인트</h3>
          <p className="text-2xl font-bold text-green-600">{detailData.total_data_points.toLocaleString()}</p>
        </div>
        <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-purple-800">전체 필드 수</h3>
          <p className="text-2xl font-bold text-purple-600">
            {Object.values(detailData.tables_detail).reduce((sum, table) => sum + table.data_fields.total_fields, 0)}
          </p>
        </div>
      </div>

      {/* 테이블 선택 탭 */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">통계표별 상세 정보</h3>
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 overflow-x-auto">
            {Object.keys(detailData.tables_detail).map((tableName) => (
              <button
                key={tableName}
                onClick={() => setSelectedTable(tableName)}
                className={`py-2 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${
                  selectedTable === tableName
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tableName}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* 선택된 테이블 상세 정보 */}
      {selectedTableData && (
        <div className="space-y-6">
          {/* 기본 정보 */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">기본 정보</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <span className="text-gray-500 text-sm">총 레코드:</span>
                <p className="font-semibold text-gray-900">{selectedTableData.total_records.toLocaleString()}개</p>
              </div>
              <div>
                <span className="text-gray-500 text-sm">연도 범위:</span>
                <p className="font-semibold text-gray-900">
                  {selectedTableData.year_range.min_year && selectedTableData.year_range.max_year
                    ? `${selectedTableData.year_range.min_year} - ${selectedTableData.year_range.max_year}`
                    : 'N/A'
                  }
                </p>
              </div>
              <div>
                <span className="text-gray-500 text-sm">총 필드:</span>
                <p className="font-semibold text-gray-900">{selectedTableData.data_fields.total_fields}개</p>
              </div>
              <div>
                <span className="text-gray-500 text-sm">숫자/텍스트:</span>
                <p className="font-semibold text-gray-900">
                  <span className="text-green-600">{selectedTableData.data_fields.numeric_count}</span>
                  /
                  <span className="text-blue-600">{selectedTableData.data_fields.text_count}</span>
                </p>
              </div>
            </div>
          </div>

          {/* 데이터 필드 정보 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* 숫자 필드 */}
            <div className="bg-green-50 border border-green-200 rounded-lg p-6">
              <h4 className="text-lg font-semibold text-green-800 mb-3">
                숫자 데이터 필드 ({selectedTableData.data_fields.numeric_count}개)
              </h4>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {selectedTableData.data_fields.numeric_fields.map((field, idx) => (
                  <span
                    key={idx}
                    className="inline-block bg-green-100 text-green-700 text-sm px-2 py-1 rounded mr-1 mb-1"
                  >
                    {field}
                  </span>
                ))}
              </div>
            </div>

            {/* 텍스트 필드 */}
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
              <h4 className="text-lg font-semibold text-blue-800 mb-3">
                텍스트 데이터 필드 ({selectedTableData.data_fields.text_count}개)
              </h4>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {selectedTableData.data_fields.text_fields.map((field, idx) => (
                  <span
                    key={idx}
                    className="inline-block bg-blue-100 text-blue-700 text-sm px-2 py-1 rounded mr-1 mb-1"
                  >
                    {field}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* 샘플 데이터 */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">샘플 데이터</h4>
            <div className="space-y-4">
              {selectedTableData.sample_data.map((sample, idx) => (
                <div key={idx} className="border border-gray-100 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h5 className="font-medium text-gray-900">
                      샘플 #{sample.sample_index}
                    </h5>
                    <span className="bg-gray-100 text-gray-700 text-sm px-2 py-1 rounded">
                      {sample.year}년
                    </span>
                  </div>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {Object.entries(sample.data_preview).map(([field, info]) => (
                      <div key={field} className="bg-gray-50 p-3 rounded">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium text-gray-700 truncate" title={field}>
                            {field}
                          </span>
                          <span className={`text-xs px-1.5 py-0.5 rounded ${
                            info.type === 'numeric'
                              ? 'bg-green-100 text-green-700'
                              : 'bg-blue-100 text-blue-700'
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
        </div>
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