import React, { useState, useEffect } from 'react';
import { API_ORIGIN } from '../services/api';

interface BasicStatistics {
  count: number;
  mean: number;
  median: number;
  std: number;
  min: number;
  max: number;
  quartiles: {
    q1: number;
    q2: number;
    q3: number;
  };
  skewness: number;
}

interface FieldStatistics {
  type: 'numeric' | 'text';
  count: number;
  mean?: number;
  std?: number;
  min?: number;
  max?: number;
  range?: number;
  coefficient_of_variation?: number;
  unique_count?: number;
  most_common?: string;
  sample_values?: string[];
}

interface DataQuality {
  completeness: number;
  consistency: number;
  numeric_ratio: number;
}

interface DistributionCharacteristics {
  total_numeric_values: number;
  data_variability: string;
  distribution_type: string;
}

interface TableDistributionAnalysis {
  basic_statistics: BasicStatistics;
  field_statistics: Record<string, FieldStatistics>;
  data_quality: DataQuality;
  distribution_characteristics: DistributionCharacteristics;
}

interface StatDistributionResponse {
  stat_name: string;
  analysis_type: string;
  total_tables: number;
  analysis_date: string;
  distribution_analysis: Record<string, TableDistributionAnalysis>;
}

interface Props {
  statName: string;
  onBack: () => void;
}

export const StatDistributionViewer: React.FC<Props> = ({ statName, onBack }) => {
  const [loading, setLoading] = useState(true);
  const [distributionData, setDistributionData] = useState<StatDistributionResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);

  useEffect(() => {
    loadDistributionAnalysis();
  }, [statName]);

  const loadDistributionAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log(`분포 특성 분석 API 호출: ${statName}`);

      const response = await fetch(`${API_ORIGIN}/api/stats-distribution/${encodeURIComponent(statName)}`);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('분포 특성 분석 응답:', data);
      setDistributionData(data);

      // 첫 번째 테이블을 기본 선택
      const tableNames = Object.keys(data.distribution_analysis);
      if (tableNames.length > 0) {
        setSelectedTable(tableNames[0]);
      }
    } catch (err) {
      console.error('분포 특성 분석 로드 오류:', err);
      setError(`분포 특성 분석을 불러오는데 실패했습니다: ${err instanceof Error ? err.message : '알 수 없는 오류'}`);
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num: number, decimals: number = 2): string => {
    return num.toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals
    });
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-white/80 z-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block w-16 h-16 border-4 border-gray-200 border-t-primary-600 rounded-full animate-spin mb-4"></div>
          <h3 className="text-lg font-semibold text-gray-800 mb-2">분포 특성 분석 로딩</h3>
          <p className="text-gray-600">'{statName}' 데이터를 분석하는 중...</p>
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
            onClick={loadDistributionAnalysis}
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

  if (!distributionData) return null;

  const selectedTableData = selectedTable ? distributionData.distribution_analysis[selectedTable] : null;

  return (
    <div>
      {/* 헤더 */}
      <div className="mb-8">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">
              데이터 분포 특성 분석
            </h2>
            <p className="text-gray-600 mb-2">
              <strong>{distributionData.stat_name}</strong>
            </p>
            <p className="text-sm text-gray-500">
              분석 일시: {new Date(distributionData.analysis_date).toLocaleString('ko-KR')}
            </p>
          </div>
          <button
            onClick={onBack}
            className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-50 transition-colors text-sm font-medium"
          >
            뒤로 가기
          </button>
        </div>
      </div>

      {/* 테이블 선택 탭 */}
      <div className="mb-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-3">
          통계표별 분포 분석 ({distributionData.total_tables}개 테이블)
        </h3>
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex space-x-8 overflow-x-auto">
            {Object.keys(distributionData.distribution_analysis).map((tableName) => (
              <button
                key={tableName}
                onClick={() => setSelectedTable(tableName)}
                className={`py-2 px-1 border-b-2 font-medium text-sm whitespace-nowrap ${
                  selectedTable === tableName
                    ? 'border-purple-500 text-purple-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tableName}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {/* 선택된 테이블 분포 분석 */}
      {selectedTableData && (
        <div className="space-y-6">
          {/* 기초 통계 */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">기초 통계량</h4>
            {Object.keys(selectedTableData.basic_statistics).length > 0 ? (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <h5 className="text-sm font-medium text-blue-800">데이터 개수</h5>
                  <p className="text-xl font-bold text-blue-600">
                    {selectedTableData.basic_statistics.count.toLocaleString()}
                  </p>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <h5 className="text-sm font-medium text-green-800">평균</h5>
                  <p className="text-xl font-bold text-green-600">
                    {formatNumber(selectedTableData.basic_statistics.mean)}
                  </p>
                </div>
                <div className="bg-yellow-50 p-4 rounded-lg">
                  <h5 className="text-sm font-medium text-yellow-800">중앙값</h5>
                  <p className="text-xl font-bold text-yellow-600">
                    {formatNumber(selectedTableData.basic_statistics.median)}
                  </p>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <h5 className="text-sm font-medium text-purple-800">표준편차</h5>
                  <p className="text-xl font-bold text-purple-600">
                    {formatNumber(selectedTableData.basic_statistics.std)}
                  </p>
                </div>
                <div className="bg-red-50 p-4 rounded-lg">
                  <h5 className="text-sm font-medium text-red-800">최솟값</h5>
                  <p className="text-xl font-bold text-red-600">
                    {formatNumber(selectedTableData.basic_statistics.min)}
                  </p>
                </div>
                <div className="bg-indigo-50 p-4 rounded-lg">
                  <h5 className="text-sm font-medium text-indigo-800">최댓값</h5>
                  <p className="text-xl font-bold text-indigo-600">
                    {formatNumber(selectedTableData.basic_statistics.max)}
                  </p>
                </div>
                <div className="bg-pink-50 p-4 rounded-lg">
                  <h5 className="text-sm font-medium text-pink-800">왜도</h5>
                  <p className="text-xl font-bold text-pink-600">
                    {formatNumber(selectedTableData.basic_statistics.skewness, 3)}
                  </p>
                </div>
                <div className="bg-gray-50 p-4 rounded-lg">
                  <h5 className="text-sm font-medium text-gray-800">사분위수 범위</h5>
                  <p className="text-sm font-bold text-gray-600">
                    Q1: {formatNumber(selectedTableData.basic_statistics.quartiles.q1)}<br/>
                    Q3: {formatNumber(selectedTableData.basic_statistics.quartiles.q3)}
                  </p>
                </div>
              </div>
            ) : (
              <p className="text-gray-500">기초 통계량 데이터가 없습니다.</p>
            )}
          </div>

          {/* 분포 특성 */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">분포 특성</h4>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                <h5 className="font-medium text-amber-800 mb-2">데이터 변동성</h5>
                <p className="text-lg font-bold text-amber-600">
                  {selectedTableData.distribution_characteristics.data_variability}
                </p>
                <p className="text-sm text-amber-700 mt-1">
                  총 {selectedTableData.distribution_characteristics.total_numeric_values.toLocaleString()}개 수치 데이터
                </p>
              </div>
              <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
                <h5 className="font-medium text-teal-800 mb-2">분포 형태</h5>
                <p className="text-lg font-bold text-teal-600">
                  {selectedTableData.distribution_characteristics.distribution_type}
                </p>
              </div>
              <div className="bg-cyan-50 border border-cyan-200 rounded-lg p-4">
                <h5 className="font-medium text-cyan-800 mb-2">데이터 품질</h5>
                <div className="space-y-1">
                  <p className="text-sm">
                    완성도: <span className="font-bold text-cyan-600">
                      {selectedTableData.data_quality.completeness.toFixed(1)}%
                    </span>
                  </p>
                  <p className="text-sm">
                    일관성: <span className="font-bold text-cyan-600">
                      {selectedTableData.data_quality.consistency.toFixed(1)}%
                    </span>
                  </p>
                  <p className="text-sm">
                    수치 비율: <span className="font-bold text-cyan-600">
                      {selectedTableData.data_quality.numeric_ratio.toFixed(1)}%
                    </span>
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* 필드별 통계 */}
          <div className="bg-white border border-gray-200 rounded-lg p-6">
            <h4 className="text-lg font-semibold text-gray-900 mb-4">필드별 상세 통계</h4>
            <div className="space-y-4 max-h-96 overflow-y-auto">
              {Object.entries(selectedTableData.field_statistics).map(([fieldName, fieldStats]) => (
                <div key={fieldName} className="border border-gray-100 rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h5 className="font-medium text-gray-900">{fieldName}</h5>
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      fieldStats.type === 'numeric'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-blue-100 text-blue-800'
                    }`}>
                      {fieldStats.type}
                    </span>
                  </div>

                  {fieldStats.type === 'numeric' ? (
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                      <div>
                        <span className="text-xs text-gray-500">개수</span>
                        <p className="font-medium">{fieldStats.count}</p>
                      </div>
                      <div>
                        <span className="text-xs text-gray-500">평균</span>
                        <p className="font-medium">{formatNumber(fieldStats.mean || 0)}</p>
                      </div>
                      <div>
                        <span className="text-xs text-gray-500">범위</span>
                        <p className="font-medium">{formatNumber(fieldStats.range || 0)}</p>
                      </div>
                      <div>
                        <span className="text-xs text-gray-500">변동계수</span>
                        <p className="font-medium">{formatNumber(fieldStats.coefficient_of_variation || 0, 3)}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                      <div>
                        <span className="text-xs text-gray-500">총 개수</span>
                        <p className="font-medium">{fieldStats.count}</p>
                      </div>
                      <div>
                        <span className="text-xs text-gray-500">고유값 개수</span>
                        <p className="font-medium">{fieldStats.unique_count}</p>
                      </div>
                      <div>
                        <span className="text-xs text-gray-500">최빈값</span>
                        <p className="font-medium text-sm truncate" title={fieldStats.most_common}>
                          {fieldStats.most_common || 'N/A'}
                        </p>
                      </div>
                      {fieldStats.sample_values && fieldStats.sample_values.length > 0 && (
                        <div className="col-span-full">
                          <span className="text-xs text-gray-500">샘플 값들</span>
                          <div className="flex flex-wrap gap-1 mt-1">
                            {fieldStats.sample_values.slice(0, 5).map((value, idx) => (
                              <span
                                key={idx}
                                className="bg-gray-100 text-gray-700 text-xs px-2 py-1 rounded"
                                title={value}
                              >
                                {value.length > 20 ? `${value.substring(0, 20)}...` : value}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default StatDistributionViewer;