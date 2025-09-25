import React, { useState, useEffect } from 'react';

interface TableAnalysisData {
  stat_name: string;
  stat_url: string;
  metadata: {
    title: string;
    department: string;
    keywords: string[];
    related_terms: Record<string, string>;
  };
  total_tables: number;
  total_data_points: number;
  analysis_date: string;
  tables_analysis: Record<string, TableAnalysis>;
}

interface TableAnalysis {
  table_name: string;
  data_overview: {
    total_records: number;
    year_range: { min: number | null; max: number | null };
    total_fields: number;
    numeric_fields_count: number;
    text_fields_count: number;
    sample_fields: string[];
  };
  basic_statistics: {
    count?: number;
    mean?: number;
    median?: number;
    std?: number;
    min?: number;
    max?: number;
    sum?: number;
    quartiles?: {
      q1: number;
      q2: number;
      q3: number;
    };
  };
  data_samples: Array<{
    record_index: number;
    year: number;
    sample_data: Record<string, {
      raw: string;
      value: any;
      unit: string;
    }>;
  }>;
  distribution_characteristics: {
    data_types_distribution: {
      numeric_ratio: number;
      text_ratio: number;
    };
    value_ranges: {
      range?: number;
      coefficient_of_variation?: number;
    };
    common_patterns: string[];
  };
  objective_summary: string;
}

interface TableAnalysisViewerProps {
  statName: string;
  onBack: () => void;
}

export const TableAnalysisViewer: React.FC<TableAnalysisViewerProps> = ({ statName, onBack }) => {
  const [analysisData, setAnalysisData] = useState<TableAnalysisData | null>(null);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadTableAnalysis();
  }, [statName]);

  const loadTableAnalysis = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await fetch(`/api/table-analysis/${encodeURIComponent(statName)}`);
      if (!response.ok) {
        throw new Error(`분석 데이터 로드 실패: ${response.status}`);
      }
      
      const data = await response.json();
      setAnalysisData(data);
      
      // 첫 번째 테이블을 기본 선택
      const firstTable = Object.keys(data.tables_analysis)[0];
      if (firstTable) {
        setSelectedTable(firstTable);
      }
      
    } catch (err) {
      console.error('테이블 분석 로드 오류:', err);
      setError(err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/20 backdrop-blur-sm z-50 flex items-center justify-center">
        <div className="bg-white/90 backdrop-blur-md rounded-2xl p-8 shadow-2xl border border-white/20 max-w-md w-full mx-4">
          <div className="text-center">
            <div className="animate-spin rounded-full h-16 w-16 border-4 border-primary-200 border-t-primary-600 mx-auto mb-6"></div>
            <h3 className="text-xl font-semibold text-gray-800 mb-2">통계표별 분석 로딩</h3>
            <p className="text-gray-600">'{statName}' 데이터를 분석하는 중...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-red-800 mb-2">분석 데이터 로드 실패</h3>
        <p className="text-red-600">{error}</p>
        <div className="mt-4 space-x-3">
          <button
            onClick={loadTableAnalysis}
            className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700"
          >
            다시 시도
          </button>
          <button
            onClick={onBack}
            className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700"
          >
            뒤로 가기
          </button>
        </div>
      </div>
    );
  }

  if (!analysisData) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">분석 데이터를 찾을 수 없습니다.</p>
        <button
          onClick={onBack}
          className="mt-4 bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
        >
          뒤로 가기
        </button>
      </div>
    );
  }

  const selectedTableData = selectedTable ? analysisData.tables_analysis[selectedTable] : null;

  return (
    <div className="max-w-7xl mx-auto">
      {/* 헤더 */}
      <div className="mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{analysisData.stat_name}</h1>
            <p className="text-gray-600 mt-1">통계표별 상세 분석</p>
          </div>
          <button
            onClick={onBack}
            className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700"
          >
            ← 뒤로 가기
          </button>
        </div>
        
        <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
            <div>
              <span className="font-medium text-blue-800">총 통계표:</span>
              <span className="ml-2 text-blue-600">{analysisData.total_tables}개</span>
            </div>
            <div>
              <span className="font-medium text-blue-800">총 데이터:</span>
              <span className="ml-2 text-blue-600">{analysisData.total_data_points.toLocaleString()}개</span>
            </div>
            <div>
              <span className="font-medium text-blue-800">작성기관:</span>
              <span className="ml-2 text-blue-600">{analysisData.metadata.department}</span>
            </div>
            <div>
              <span className="font-medium text-blue-800">분석일시:</span>
              <span className="ml-2 text-blue-600">{new Date(analysisData.analysis_date).toLocaleString()}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 왼쪽: 통계표 목록 */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg border shadow-sm">
            <div className="p-4 border-b">
              <h2 className="text-lg font-medium text-gray-900">📊 통계표 목록</h2>
              <p className="text-sm text-gray-500 mt-1">분석할 통계표를 선택하세요</p>
            </div>
            <div className="p-2">
              {Object.keys(analysisData.tables_analysis).map((tableName, index) => {
                const tableData = analysisData.tables_analysis[tableName];
                return (
                  <button
                    key={tableName}
                    onClick={() => setSelectedTable(tableName)}
                    className={`w-full text-left p-3 rounded-lg mb-2 transition-colors ${
                      selectedTable === tableName
                        ? 'bg-blue-100 border-blue-300 text-blue-800'
                        : 'hover:bg-gray-50 border-gray-200 text-gray-700'
                    } border`}
                  >
                    <div className="font-medium text-sm mb-1">{tableName}</div>
                    <div className="text-xs text-gray-500">
                      {tableData.data_overview.total_records}개 레코드 • {tableData.data_overview.total_fields}개 필드
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* 오른쪽: 선택된 통계표 상세 분석 */}
        <div className="lg:col-span-3">
          {selectedTableData ? (
            <TableDetailView tableData={selectedTableData} />
          ) : (
            <div className="bg-white rounded-lg border shadow-sm p-8 text-center">
              <p className="text-gray-500">통계표를 선택하여 상세 분석을 확인하세요.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

interface TableDetailViewProps {
  tableData: TableAnalysis;
}

const TableDetailView: React.FC<TableDetailViewProps> = ({ tableData }) => {
  return (
    <div className="space-y-6">
      {/* 객관적 현황 요약 */}
      <div className="bg-white rounded-lg border shadow-sm">
        <div className="p-4 border-b">
          <h3 className="text-lg font-medium text-gray-900">📋 {tableData.table_name}</h3>
          <p className="text-sm text-gray-500 mt-1">객관적 현황 요약</p>
        </div>
        <div className="p-4">
          <p className="text-gray-700 leading-relaxed">{tableData.objective_summary}</p>
        </div>
      </div>

      {/* 데이터 개요 */}
      <div className="bg-white rounded-lg border shadow-sm">
        <div className="p-4 border-b">
          <h3 className="text-lg font-medium text-gray-900">📊 데이터 개요</h3>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-3 bg-blue-50 rounded-lg">
              <div className="text-2xl font-bold text-blue-600">{tableData.data_overview.total_records}</div>
              <div className="text-sm text-blue-800">총 레코드</div>
            </div>
            <div className="text-center p-3 bg-green-50 rounded-lg">
              <div className="text-2xl font-bold text-green-600">{tableData.data_overview.total_fields}</div>
              <div className="text-sm text-green-800">총 필드</div>
            </div>
            <div className="text-center p-3 bg-purple-50 rounded-lg">
              <div className="text-2xl font-bold text-purple-600">{tableData.data_overview.numeric_fields_count}</div>
              <div className="text-sm text-purple-800">수치형 필드</div>
            </div>
            <div className="text-center p-3 bg-orange-50 rounded-lg">
              <div className="text-2xl font-bold text-orange-600">{tableData.data_overview.text_fields_count}</div>
              <div className="text-sm text-orange-800">텍스트 필드</div>
            </div>
          </div>
          
          {tableData.data_overview.year_range.min && (
            <div className="mt-4 p-3 bg-gray-50 rounded-lg">
              <span className="font-medium">시간 범위: </span>
              <span className="text-gray-700">
                {tableData.data_overview.year_range.min === tableData.data_overview.year_range.max 
                  ? `${tableData.data_overview.year_range.min}년` 
                  : `${tableData.data_overview.year_range.min}년 ~ ${tableData.data_overview.year_range.max}년`}
              </span>
            </div>
          )}
        </div>
      </div>

      {/* 기초통계 */}
      {Object.keys(tableData.basic_statistics).length > 0 && (
        <div className="bg-white rounded-lg border shadow-sm">
          <div className="p-4 border-b">
            <h3 className="text-lg font-medium text-gray-900">📈 기초통계 (수치형 데이터)</h3>
          </div>
          <div className="p-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {tableData.basic_statistics.mean !== undefined && (
                <div className="text-center p-3 bg-blue-50 rounded-lg">
                  <div className="text-xl font-bold text-blue-600">{tableData.basic_statistics.mean.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}</div>
                  <div className="text-sm text-blue-800">평균</div>
                </div>
              )}
              {tableData.basic_statistics.median !== undefined && (
                <div className="text-center p-3 bg-green-50 rounded-lg">
                  <div className="text-xl font-bold text-green-600">{tableData.basic_statistics.median.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}</div>
                  <div className="text-sm text-green-800">중간값</div>
                </div>
              )}
              {tableData.basic_statistics.min !== undefined && (
                <div className="text-center p-3 bg-red-50 rounded-lg">
                  <div className="text-xl font-bold text-red-600">{tableData.basic_statistics.min.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}</div>
                  <div className="text-sm text-red-800">최소값</div>
                </div>
              )}
              {tableData.basic_statistics.max !== undefined && (
                <div className="text-center p-3 bg-purple-50 rounded-lg">
                  <div className="text-xl font-bold text-purple-600">{tableData.basic_statistics.max.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}</div>
                  <div className="text-sm text-purple-800">최대값</div>
                </div>
              )}
            </div>
            
            {tableData.basic_statistics.quartiles && (
              <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                <h4 className="font-medium mb-2">사분위수</h4>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>Q1: {tableData.basic_statistics.quartiles.q1.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}</div>
                  <div>Q2: {tableData.basic_statistics.quartiles.q2.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}</div>
                  <div>Q3: {tableData.basic_statistics.quartiles.q3.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 데이터 샘플 */}
      <div className="bg-white rounded-lg border shadow-sm">
        <div className="p-4 border-b">
          <h3 className="text-lg font-medium text-gray-900">🔍 데이터 샘플</h3>
          <p className="text-sm text-gray-500 mt-1">처음 5개 레코드의 주요 필드</p>
        </div>
        <div className="p-4">
          <div className="space-y-4">
            {tableData.data_samples.map((sample, index) => (
              <div key={index} className="border rounded-lg p-3 bg-gray-50">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-gray-900">레코드 #{sample.record_index}</span>
                  <span className="text-sm text-gray-500">연도: {sample.year}</span>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {Object.entries(sample.sample_data).map(([field, data]) => (
                    <div key={field} className="text-sm">
                      <span className="font-medium text-gray-700">{field}:</span>
                      <span className="ml-2 text-gray-600">{data.raw}</span>
                      {data.unit === 'number' && (
                        <span className="ml-1 text-xs text-blue-600">(수치형)</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 분포 특성 */}
      <div className="bg-white rounded-lg border shadow-sm">
        <div className="p-4 border-b">
          <h3 className="text-lg font-medium text-gray-900">📉 분포 특성</h3>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium mb-3">데이터 타입 분포</h4>
              <div className="space-y-3">
                <div className="flex items-center">
                  <div className="w-20 text-sm">수치형:</div>
                  <div className="flex-1 bg-gray-200 rounded-full h-4 mr-2">
                    <div 
                      className="bg-blue-600 h-4 rounded-full transition-all duration-300" 
                      style={{ width: `${tableData.distribution_characteristics.data_types_distribution.numeric_ratio * 100}%` }}
                    ></div>
                  </div>
                  <div className="text-sm font-medium text-blue-600">
                    {(tableData.distribution_characteristics.data_types_distribution.numeric_ratio * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="flex items-center">
                  <div className="w-20 text-sm">텍스트:</div>
                  <div className="flex-1 bg-gray-200 rounded-full h-4 mr-2">
                    <div 
                      className="bg-green-600 h-4 rounded-full transition-all duration-300" 
                      style={{ width: `${tableData.distribution_characteristics.data_types_distribution.text_ratio * 100}%` }}
                    ></div>
                  </div>
                  <div className="text-sm font-medium text-green-600">
                    {(tableData.distribution_characteristics.data_types_distribution.text_ratio * 100).toFixed(1)}%
                  </div>
                </div>
              </div>
              
              {/* 데이터 타입별 상세 정보 */}
              <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                <div className="text-xs text-gray-600 space-y-1">
                  <div>수치형 필드: {tableData.data_overview.numeric_fields_count}개</div>
                  <div>텍스트 필드: {tableData.data_overview.text_fields_count}개</div>
                  <div>총 필드: {tableData.data_overview.total_fields}개</div>
                </div>
              </div>
            </div>
            
            {tableData.distribution_characteristics.value_ranges.range !== undefined && (
              <div>
                <h4 className="font-medium mb-3">수치 데이터 특성</h4>
                <div className="space-y-3">
                  <div className="p-3 bg-blue-50 rounded-lg">
                    <div className="text-sm font-medium text-blue-800">데이터 범위</div>
                    <div className="text-lg font-bold text-blue-600">
                      {tableData.distribution_characteristics.value_ranges.range.toLocaleString('ko-KR', { maximumFractionDigits: 1 })}
                    </div>
                    <div className="text-xs text-blue-700">최대값 - 최소값</div>
                  </div>
                  
                  {tableData.distribution_characteristics.value_ranges.coefficient_of_variation !== undefined && (
                    <div className="p-3 bg-purple-50 rounded-lg">
                      <div className="text-sm font-medium text-purple-800">변동계수</div>
                      <div className="text-lg font-bold text-purple-600">
                        {(tableData.distribution_characteristics.value_ranges.coefficient_of_variation * 100).toFixed(1)}%
                      </div>
                      <div className="text-xs text-purple-700">표준편차 / 평균</div>
                    </div>
                  )}
                  
                  {/* 데이터 변동성 해석 */}
                  {tableData.distribution_characteristics.value_ranges.coefficient_of_variation !== undefined && (
                    <div className="mt-4 p-3 bg-yellow-50 rounded-lg">
                      <div className="text-xs text-yellow-800">
                        <div className="font-medium mb-1">변동성 해석:</div>
                        {tableData.distribution_characteristics.value_ranges.coefficient_of_variation < 0.1 
                          ? "🟢 낮은 변동성 (10% 미만)" 
                          : tableData.distribution_characteristics.value_ranges.coefficient_of_variation < 0.3 
                            ? "🟡 보통 변동성 (10-30%)" 
                            : "🔴 높은 변동성 (30% 이상)"}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
          
          {/* 추가 분포 정보 */}
          {tableData.basic_statistics.quartiles && 
           tableData.basic_statistics.min !== undefined && 
           tableData.basic_statistics.max !== undefined && 
           tableData.basic_statistics.median !== undefined && (
            <div className="mt-6 pt-6 border-t">
              <h4 className="font-medium mb-3">📊 데이터 분포 시각화</h4>
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="text-sm text-gray-600 mb-3">박스플롯 형태의 분포</div>
                <div className="relative h-8 bg-white rounded border">
                  <div className="absolute top-0 bottom-0 flex items-center w-full px-2">
                    {/* 최소값 */}
                    <div className="relative w-1 h-6 bg-gray-400 rounded-full">
                      <div className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 text-xs text-gray-600">
                        {tableData.basic_statistics.min.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}
                      </div>
                    </div>
                    
                    {/* Q1-Q3 박스 */}
                    <div 
                      className="relative h-6 bg-blue-200 border border-blue-400 mx-1" 
                      style={{ 
                        marginLeft: `${((tableData.basic_statistics.quartiles.q1 - tableData.basic_statistics.min) / (tableData.basic_statistics.max - tableData.basic_statistics.min)) * 80}%`,
                        width: `${((tableData.basic_statistics.quartiles.q3 - tableData.basic_statistics.quartiles.q1) / (tableData.basic_statistics.max - tableData.basic_statistics.min)) * 80}%`
                      }}
                    >
                      {/* 중간값 라인 */}
                      <div 
                        className="absolute top-0 bottom-0 w-0.5 bg-blue-600"
                        style={{ 
                          left: `${((tableData.basic_statistics.median - tableData.basic_statistics.quartiles.q1) / (tableData.basic_statistics.quartiles.q3 - tableData.basic_statistics.quartiles.q1)) * 100}%`
                        }}
                      ></div>
                    </div>
                    
                    {/* 최대값 */}
                    <div className="relative w-1 h-6 bg-gray-400 rounded-full ml-auto">
                      <div className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 text-xs text-gray-600">
                        {tableData.basic_statistics.max.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}
                      </div>
                    </div>
                  </div>
                </div>
                
                <div className="mt-8 grid grid-cols-3 gap-2 text-xs text-center">
                  <div>
                    <div className="font-medium">Q1 (25%)</div>
                    <div className="text-gray-600">{tableData.basic_statistics.quartiles.q1.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}</div>
                  </div>
                  <div>
                    <div className="font-medium">Q2 (50%)</div>
                    <div className="text-gray-600">{tableData.basic_statistics.quartiles.q2.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}</div>
                  </div>
                  <div>
                    <div className="font-medium">Q3 (75%)</div>
                    <div className="text-gray-600">{tableData.basic_statistics.quartiles.q3.toLocaleString('ko-KR', { maximumFractionDigits: 0 })}</div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default TableAnalysisViewer;