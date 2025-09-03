import React, { useState, useEffect } from 'react';

interface DataInspectionProps {
  statName: string;
  onBack: () => void;
}

interface DataStructure {
  total_records: number;
  data_fields: {
    numeric_fields: string[];
    text_fields: string[];
    mixed_fields: string[];
    total_numeric: number;
    total_text: number;
    total_mixed: number;
  };
  year_range: {
    min_year: number | null;
    max_year: number | null;
  };
  sample_data: Array<{
    year: number;
    data: Record<string, any>;
  }>;
}

interface DataInspectionResult {
  collection_info: {
    source_url: string | null;
    collection_time: string;
    stat_name: string;
    keywords: string[];
    related_terms: Record<string, string>;
  };
  data_structure: DataStructure;
  data_quality: {
    completeness: number;
    consistency_check: string;
    recommendations: string[];
  };
}

interface ErrorResponse {
  message: string;
  suggestion?: string;
  available_data?: boolean;
}

interface DataSummary {
  summary: {
    total_records: number;
    year_coverage: string;
    data_fields: number;
    numeric_summary: {
      count: number;
      min: number;
      max: number;
      average: number;
      total: number;
    };
  };
  field_preview: Record<string, any[]>;
}

export const DataInspectionViewer: React.FC<DataInspectionProps> = ({ statName, onBack }) => {
  const [activeTab, setActiveTab] = useState<'inspect' | 'summary' | 'raw'>('inspect');
  const [inspectionData, setInspectionData] = useState<DataInspectionResult | ErrorResponse | null>(null);
  const [summaryData, setSummaryData] = useState<DataSummary | ErrorResponse | null>(null);
  const [rawData, setRawData] = useState<any | ErrorResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDataInspection = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/data/inspect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stat_name: statName })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setInspectionData(data);
    } catch (err) {
      setError(`데이터 검사 실패: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchDataSummary = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/data/summary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stat_name: statName })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setSummaryData(data);
    } catch (err) {
      setError(`데이터 요약 실패: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  const fetchRawData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/data/raw-view', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stat_name: statName })
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      const data = await response.json();
      setRawData(data);
    } catch (err) {
      setError(`원시 데이터 조회 실패: ${err instanceof Error ? err.message : String(err)}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'inspect' && !inspectionData) {
      fetchDataInspection();
    } else if (activeTab === 'summary' && !summaryData) {
      fetchDataSummary();
    } else if (activeTab === 'raw' && !rawData) {
      fetchRawData();
    }
  }, [activeTab, statName, inspectionData, summaryData, rawData]); // eslint-disable-line react-hooks/exhaustive-deps

  const renderInspectionTab = () => {
    if (!inspectionData) return null;

    // Handle case where API returns error message instead of inspection data
    if ('message' in inspectionData) {
      return (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
          <div className="flex">
            <svg className="h-5 w-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">데이터를 찾을 수 없습니다</h3>
              <div className="mt-2 text-sm text-yellow-700">
                {(inspectionData as ErrorResponse).message}
                {(inspectionData as ErrorResponse).suggestion && (
                  <p className="mt-1">{(inspectionData as ErrorResponse).suggestion}</p>
                )}
              </div>
            </div>
          </div>
        </div>
      );
    }

    const { collection_info, data_structure, data_quality } = inspectionData;

    return (
      <div className="space-y-6">
        {/* Collection Info */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 1.79 4 4 4h8c2.21 0 4-1.79 4-4V7M4 7V4c0-1.1.9-2 2-2h12c1.1 0 2 .9 2 2v3M4 7h16m-8 4v6" />
            </svg>
            수집 정보
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-gray-600">통계명</p>
              <p className="text-sm">{collection_info.stat_name}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">수집 시간</p>
              <p className="text-sm">{new Date(collection_info.collection_time).toLocaleString()}</p>
            </div>
            {collection_info.source_url && (
              <div>
                <p className="text-sm font-medium text-gray-600">원본 URL</p>
                <p className="text-sm text-blue-600">{collection_info.source_url}</p>
              </div>
            )}
          </div>
        </div>

        {/* Data Structure */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            데이터 구조
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="text-center p-4 bg-blue-50 rounded">
              <p className="text-2xl font-bold text-blue-600">{data_structure.total_records}</p>
              <p className="text-sm text-gray-600">총 레코드</p>
            </div>
            <div className="text-center p-4 bg-green-50 rounded">
              <p className="text-2xl font-bold text-green-600">{data_structure.data_fields.total_numeric}</p>
              <p className="text-sm text-gray-600">숫자 필드</p>
            </div>
            <div className="text-center p-4 bg-orange-50 rounded">
              <p className="text-2xl font-bold text-orange-600">{data_structure.data_fields.total_text}</p>
              <p className="text-sm text-gray-600">텍스트 필드</p>
            </div>
          </div>

          {data_structure.year_range.min_year && (
            <div className="mb-4">
              <p className="text-sm font-medium text-gray-600 mb-2">연도 범위</p>
              <div className="flex items-center gap-2 text-sm">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3a1 1 0 011-1h6a1 1 0 011 1v4h3a1 1 0 011 1v13a1 1 0 01-1 1H5a1 1 0 01-1-1V8a1 1 0 011-1h3z" />
                </svg>
                {data_structure.year_range.min_year} - {data_structure.year_range.max_year}
              </div>
            </div>
          )}

          {data_structure.sample_data.length > 0 && (
            <div>
              <p className="text-sm font-medium text-gray-600 mb-2">샘플 데이터</p>
              <div className="bg-gray-50 p-3 rounded text-xs overflow-auto">
                <pre>{JSON.stringify(data_structure.sample_data, null, 2)}</pre>
              </div>
            </div>
          )}
        </div>

        {/* Data Quality */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            데이터 품질
          </h3>
          <div className="space-y-4">
            <div>
              <p className="text-sm font-medium text-gray-600">완성도</p>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                <div 
                  className="bg-blue-600 h-2 rounded-full" 
                  style={{ width: `${data_quality.completeness}%` }}
                ></div>
              </div>
              <p className="text-xs text-gray-500 mt-1">{data_quality.completeness.toFixed(1)}%</p>
            </div>
            
            <div>
              <p className="text-sm font-medium text-gray-600">일관성 검사</p>
              <p className="text-sm">{data_quality.consistency_check}</p>
            </div>

            <div>
              <p className="text-sm font-medium text-gray-600 mb-2">권장사항</p>
              <ul className="space-y-1">
                {data_quality.recommendations.map((rec, index) => (
                  <li key={index} className="text-sm text-gray-700 flex items-start gap-2">
                    <svg className="h-4 w-4 mt-0.5 text-yellow-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                    </svg>
                    {rec}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    );
  };

  const renderSummaryTab = () => {
    if (!summaryData) return null;

    // Handle case where API returns error message instead of summary data
    if ('message' in summaryData) {
      return (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
          <div className="flex">
            <svg className="h-5 w-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">데이터를 찾을 수 없습니다</h3>
              <div className="mt-2 text-sm text-yellow-700">
                {(summaryData as ErrorResponse).message}
                {(summaryData as ErrorResponse).suggestion && (
                  <p className="mt-1">{(summaryData as ErrorResponse).suggestion}</p>
                )}
              </div>
            </div>
          </div>
        </div>
      );
    }

    const { summary, field_preview } = summaryData;

    return (
      <div className="space-y-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">데이터 요약</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-blue-50 rounded">
              <p className="text-2xl font-bold text-blue-600">{summary.total_records}</p>
              <p className="text-sm text-gray-600">총 레코드</p>
            </div>
            <div className="text-center p-4 bg-green-50 rounded">
              <p className="text-2xl font-bold text-green-600">{summary.data_fields}</p>
              <p className="text-sm text-gray-600">데이터 필드</p>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded">
              <p className="text-lg font-bold text-purple-600">{summary.year_coverage}</p>
              <p className="text-sm text-gray-600">연도 범위</p>
            </div>
            {summary.numeric_summary.count > 0 && (
              <div className="text-center p-4 bg-orange-50 rounded">
                <p className="text-2xl font-bold text-orange-600">{summary.numeric_summary.count}</p>
                <p className="text-sm text-gray-600">숫자 값</p>
              </div>
            )}
          </div>
        </div>

        {Object.keys(field_preview).length > 0 && (
          <div className="bg-white p-6 rounded-lg shadow">
            <h3 className="text-lg font-semibold mb-4">필드 미리보기</h3>
            <div className="space-y-4">
              {Object.entries(field_preview).map(([field, values]) => (
                <div key={field}>
                  <p className="text-sm font-medium text-gray-600 mb-1">{field}</p>
                  <div className="flex flex-wrap gap-2">
                    {values.slice(0, 5).map((value, index) => (
                      <span key={index} className="px-2 py-1 bg-gray-100 rounded text-sm">
                        {String(value)}
                      </span>
                    ))}
                    {values.length > 5 && (
                      <span className="px-2 py-1 bg-gray-200 rounded text-sm text-gray-500">
                        +{values.length - 5}개 더
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderRawTab = () => {
    if (!rawData) return null;

    // Handle case where API returns error message instead of raw data
    if ('message' in rawData) {
      return (
        <div className="bg-yellow-50 border border-yellow-200 rounded-md p-4">
          <div className="flex">
            <svg className="h-5 w-5 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">데이터를 찾을 수 없습니다</h3>
              <div className="mt-2 text-sm text-yellow-700">
                {(rawData as ErrorResponse).message}
                {(rawData as ErrorResponse).suggestion && (
                  <p className="mt-1">{(rawData as ErrorResponse).suggestion}</p>
                )}
              </div>
            </div>
          </div>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">원시 데이터</h3>
          <div className="bg-gray-50 p-4 rounded-lg overflow-auto max-h-96">
            <pre className="text-xs">{JSON.stringify(rawData, null, 2)}</pre>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <div className="flex items-center justify-between">
            <div>
              <button onClick={onBack} className="flex items-center gap-2 text-blue-600 hover:text-blue-800 mb-2">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                뒤로가기
              </button>
              <h1 className="text-2xl font-bold text-gray-900">데이터 검사</h1>
              <p className="text-gray-600">{statName}</p>
            </div>
            <svg className="h-8 w-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          </div>
        </div>

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex">
              <button
                onClick={() => setActiveTab('inspect')}
                className={`py-4 px-6 border-b-2 font-medium text-sm ${
                  activeTab === 'inspect'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                상세 검사
              </button>
              <button
                onClick={() => setActiveTab('summary')}
                className={`py-4 px-6 border-b-2 font-medium text-sm ${
                  activeTab === 'summary'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                요약 정보
              </button>
              <button
                onClick={() => setActiveTab('raw')}
                className={`py-4 px-6 border-b-2 font-medium text-sm ${
                  activeTab === 'raw'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                원시 데이터
              </button>
            </nav>
          </div>
        </div>

        {/* Content */}
        {loading && (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
            <div className="flex">
              <svg className="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
              </svg>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">오류가 발생했습니다</h3>
                <div className="mt-2 text-sm text-red-700">{error}</div>
              </div>
            </div>
          </div>
        )}

        {!loading && !error && (
          <div>
            {activeTab === 'inspect' && renderInspectionTab()}
            {activeTab === 'summary' && renderSummaryTab()}
            {activeTab === 'raw' && renderRawTab()}
          </div>
        )}
      </div>
    </div>
  );
};