import React, { useState, useEffect } from 'react';

interface DataInspectionProps {
  statName: string;
  onBack: () => void;
}

interface IBSheetTableData {
  stat_name: string;
  stat_url: string;
  tables: Array<{
    table_name: string;
    form_id: string;
    period: string;
    columns: Array<{
      id: string;
      name: string;
      data_type: string;
    }>;
    rows: Array<{
      row_id: string;
      cells: Record<string, any>;
    }>;
    total_rows: number;
    collection_method: string;
  }>;
  total_tables: number;
  total_data_points: number;
  collection_success: boolean;
  errors: string[];
  inspected_at: string;
}

interface CollectedDataStructure {
  [key: string]: any;
}

export const EnhancedDataInspectionViewer: React.FC<DataInspectionProps> = ({ statName, onBack }) => {
  const [activeTab, setActiveTab] = useState<'enhanced' | 'stored' | 'summary'>('enhanced');
  const [enhancedData, setEnhancedData] = useState<IBSheetTableData | null>(null);
  const [storedData, setStoredData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const parseIBSheetData = (dataString: string) => {
    try {
      const cleanString = dataString.replace(/'/g, '"');
      return JSON.parse(cleanString);
    } catch {
      return { value: dataString, unit: 'text', raw: dataString };
    }
  };

  const fetchEnhancedData = async () => {
    try {
      const encodedStatName = encodeURIComponent(statName);
      const response = await fetch(`http://localhost:8001/api/inspect-enhanced/${encodedStatName}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      setEnhancedData(data);
    } catch (error) {
      console.error('Failed to fetch enhanced data:', error);
      setError(`Enhanced data fetch failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const fetchStoredData = async () => {
    try {
      const response = await fetch('http://localhost:8001/api/data/inspect', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stat_name: statName })
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      setStoredData(data);
    } catch (error) {
      console.error('Failed to fetch stored data:', error);
      setError(`Stored data fetch failed: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      
      await Promise.all([fetchEnhancedData(), fetchStoredData()]);
      
      setLoading(false);
    };

    if (statName) {
      loadData();
    }
  }, [statName]);

  const renderEnhancedData = () => {
    if (!enhancedData) {
      return (
        <div className="text-center py-8">
          <p className="text-gray-500">Enhanced data not available</p>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">데이터 검사 결과</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-gray-600">통계명</p>
              <p className="text-sm">{enhancedData.stat_name}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">총 테이블 수</p>
              <p className="text-sm">{enhancedData.total_tables}개</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">총 데이터 포인트</p>
              <p className="text-sm">{enhancedData.total_data_points.toLocaleString()}개</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">수집 성공</p>
              <p className={`text-sm ${enhancedData.collection_success ? 'text-green-600' : 'text-red-600'}`}>
                {enhancedData.collection_success ? '성공' : '실패'}
              </p>
            </div>
            <div className="col-span-2">
              <p className="text-sm font-medium text-gray-600">원본 URL</p>
              <p className="text-sm text-blue-600 break-all">{enhancedData.stat_url}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">검사 시간</p>
              <p className="text-sm">{new Date(enhancedData.inspected_at).toLocaleString()}</p>
            </div>
          </div>

          {enhancedData.errors && enhancedData.errors.length > 0 && (
            <div className="mt-4">
              <p className="text-sm font-medium text-red-600 mb-2">오류:</p>
              <ul className="list-disc list-inside space-y-1">
                {enhancedData.errors.map((error, index) => (
                  <li key={index} className="text-sm text-red-600">{error}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {enhancedData.tables?.map((table, index) => (
          <div key={index} className="bg-white p-6 rounded-lg shadow">
            <h4 className="text-lg font-semibold mb-4">{table.table_name}</h4>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <p className="text-sm font-medium text-gray-600">Form ID</p>
                <p className="text-sm">{table.form_id}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">기간</p>
                <p className="text-sm">{table.period}</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">행 개수</p>
                <p className="text-sm">{table.total_rows}개</p>
              </div>
              <div>
                <p className="text-sm font-medium text-gray-600">수집 방법</p>
                <p className="text-sm">{table.collection_method}</p>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-sm border-collapse border border-gray-300">
                <thead>
                  <tr className="bg-gray-50">
                    {table.columns.map(column => (
                      <th key={column.id} className="border border-gray-300 px-2 py-1 text-left">
                        {column.name}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {table.rows.slice(0, 10).map((row, rowIndex) => (
                    <tr key={rowIndex}>
                      {table.columns.map(column => (
                        <td key={column.id} className="border border-gray-300 px-2 py-1">
                          {row.cells[column.id] || ''}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {table.rows.length > 10 && (
                <p className="text-sm text-gray-500 mt-2">
                  ... 및 {table.rows.length - 10}개 행 더 있음
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderStoredData = () => {
    if (!storedData) {
      return (
        <div className="text-center py-8">
          <p className="text-gray-500">저장된 데이터를 찾을 수 없습니다</p>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">저장된 데이터 정보</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-gray-600">캐시 키</p>
              <p className="text-sm">{(storedData as any).cache_key || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">저장 시간</p>
              <p className="text-sm">{(storedData as any).saved_at ? new Date((storedData as any).saved_at).toLocaleString() : 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">통계 개수</p>
              <p className="text-sm">{(storedData as any).data_count || 0}개</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">원본 URL</p>
              <p className="text-sm text-blue-600 break-all">{(storedData as any).stat_url || 'N/A'}</p>
            </div>
          </div>
        </div>

        {((storedData as any).statistics || []).map((stat: any, index: number) => (
          <div key={index} className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-lg font-semibold">
                {stat.table_name || `데이터셋 ${index + 1}`} (연도: {stat.year})
              </h4>
              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-500">
                  {Object.keys(stat.data || {}).length}개 필드
                </span>
              </div>
            </div>
            <div className="mt-2 text-sm text-gray-600">
              연도: {stat.year} | 기간: {stat.period_text || '정보 없음'}
            </div>

            <div className="mt-4">
              <h5 className="text-md font-medium mb-3">데이터 내용 (처음 20개 필드)</h5>
              <div className="space-y-2">
                {Object.entries(stat.data).slice(0, 20).map(([key, value]) => {
                  const parsedData = parseIBSheetData(value as string);
                  const isNumeric = parsedData.unit === 'number';
                  
                  return (
                    <div key={key} className={`p-3 rounded border ${isNumeric ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'}`}>
                      <div className="flex justify-between items-start">
                        <span className="text-sm font-mono text-gray-600">{key}</span>
                        <span className={`text-xs px-2 py-1 rounded ${
                          isNumeric ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {parsedData.unit}
                        </span>
                      </div>
                      <div className="mt-1">
                        <span className={`text-sm ${isNumeric ? 'font-semibold text-blue-800' : 'text-gray-700'}`}>
                          {String(parsedData.value)}
                        </span>
                      </div>
                    </div>
                  );
                })}
                {Object.keys(stat.data || {}).length > 20 && (
                  <div className="text-center py-4 text-gray-500">
                    ... 및 {Object.keys(stat.data || {}).length - 20}개 필드 더 있음
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    );
  };

  const renderSummary = () => {
    if (!storedData) return null;

    const totalDataPoints = ((storedData as any).statistics || []).reduce((sum: number, stat: any) => 
      sum + Object.keys(stat.data).length, 0
    );

    const numericFields = ((storedData as any).statistics || []).flatMap((stat: any) => 
      Object.values(stat.data).filter((value: any) => {
        const parsed = parseIBSheetData(value as string);
        return parsed.unit === 'number';
      })
    );

    const numericValues = numericFields.map((field: any) => {
      const parsed = parseIBSheetData(field as string);
      return typeof parsed.value === 'number' ? parsed.value : parseFloat(parsed.value) || 0;
    }).filter((val: number) => !isNaN(val));

    const summary = {
      total: numericValues.reduce((sum: number, val: number) => sum + val, 0),
      mean: numericValues.length > 0 ? numericValues.reduce((sum: number, val: number) => sum + val, 0) / numericValues.length : 0,
      max: numericValues.length > 0 ? Math.max(...numericValues) : 0,
      min: numericValues.length > 0 ? Math.min(...numericValues) : 0,
      count: numericValues.length
    };

    return (
      <div className="space-y-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">데이터 요약</h3>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <p className="text-sm font-medium text-gray-600">총 데이터 포인트</p>
              <p className="text-lg font-semibold">{totalDataPoints.toLocaleString()}개</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">숫자형 데이터</p>
              <p className="text-lg font-semibold">{summary.count.toLocaleString()}개</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">숫자 합계</p>
              <p className="text-lg font-semibold">{summary.total.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">평균값</p>
              <p className="text-lg font-semibold">{summary.mean.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">최댓값</p>
              <p className="text-lg font-semibold">{summary.max.toLocaleString()}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">최솟값</p>
              <p className="text-lg font-semibold">{summary.min.toLocaleString()}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">수집된 데이터 분포</h3>
          <div className="space-y-4">
            {(((storedData as any).statistics || [])).map((stat: any, index: number) => (
              <div key={index} className="border rounded p-4">
                <div className="flex justify-between items-center">
                  <h4 className="font-medium">{stat.table_name || `데이터셋 ${index + 1}`}</h4>
                  <span className="text-sm text-gray-500">
                    {Object.keys(stat.data || {}).length}개 필드
                  </span>
                </div>
                <div className="mt-2 text-sm text-gray-600">
                  연도: {stat.year} | 기간: {stat.period_text || '정보 없음'}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">데이터를 불러오는 중...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <div className="flex items-center space-x-4">
            <button
              onClick={onBack}
              className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded-lg transition-colors"
            >
              ← 뒤로
            </button>
            <h1 className="text-2xl font-bold">데이터 검사: {statName}</h1>
          </div>
          
          {error && (
            <div className="mt-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
              {error}
            </div>
          )}
        </div>

        <div className="mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('enhanced')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'enhanced'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                구조화된 테이블
              </button>
              <button
                onClick={() => setActiveTab('stored')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'stored'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                저장된 원본데이터
              </button>
              <button
                onClick={() => setActiveTab('summary')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'summary'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                요약 통계
              </button>
            </nav>
          </div>
        </div>

        <div className="tab-content">
          {activeTab === 'enhanced' && renderEnhancedData()}
          {activeTab === 'stored' && renderStoredData()}
          {activeTab === 'summary' && renderSummary()}
        </div>
      </div>
    </div>
  );
};