import React, { useState, useEffect } from 'react';

interface DataInspectionProps {
  statName: string;
  onBack: () => void;
}

interface ParsedDataItem {
  value: any;
  unit: string;
  raw: string;
  isNumeric: boolean;
}

interface HousingDataRow {
  region: string;
  category: string;
  subcategory: string;
  value: number;
  formattedValue: string;
}

interface CollectedDataStructure {
  cache_key?: string;
  stat_url?: string;
  saved_at?: string;
  data_count?: number;
  statistics?: Array<{
    year: number;
    data: Record<string, string>;
    table_name?: string;
    period_text?: string;
    raw_data_count?: number;
  }>;
}

export const ImprovedDataInspectionViewer: React.FC<DataInspectionProps> = ({ statName, onBack }) => {
  const [activeTab, setActiveTab] = useState<'structured' | 'raw' | 'summary'>('structured');
  const [storedData, setStoredData] = useState<CollectedDataStructure | null>(null);
  const [parsedData, setParsedData] = useState<HousingDataRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const parseIBSheetData = (dataString: string): ParsedDataItem => {
    try {
      const cleanString = dataString.replace(/'/g, '"');
      const parsed = JSON.parse(cleanString);
      return {
        ...parsed,
        isNumeric: parsed.unit === 'number' || (typeof parsed.value === 'number')
      };
    } catch {
      return { 
        value: dataString, 
        unit: 'text', 
        raw: dataString,
        isNumeric: false
      };
    }
  };

  const parseHousingData = (statistics: any[]): HousingDataRow[] => {
    const rows: HousingDataRow[] = [];
    
    // 주택 건설 실적 데이터 구조 파싱
    statistics.forEach((stat, statIndex) => {
      const data = stat.data;
      
      // 지역 정보 추출
      const regions = ['총계', '수도권소계', '서울', '인천', '경기'];
      const categories = ['계', '40㎡이하', '40~60㎡이하', '60~85㎡이하', '85~135㎡이하', '135㎡초과'];
      
      // 숫자 데이터가 있는 셀들을 찾아서 구조화
      Object.entries(data).forEach(([cellKey, cellValue]) => {
        const parsedCell = parseIBSheetData(cellValue as string);
        
        if (parsedCell.isNumeric && parsedCell.value > 0) {
          // 셀 번호를 기반으로 지역과 카테고리 추정
          const cellNum = parseInt(cellKey.replace('ibsheet_cell_', ''));
          
          let region = '기타';
          let category = '기타';
          
          // 대략적인 매핑 (실제 IBSheet 구조에 따라 조정 필요)
          if (cellNum >= 304 && cellNum <= 358) {
            const index = Math.floor((cellNum - 304) / 2);
            
            if (index < 6) {
              region = '총계';
              category = categories[index] || '기타';
            } else if (index < 12) {
              region = '수도권소계';
              category = categories[index - 6] || '기타';
            } else if (index < 18) {
              region = '서울';
              category = categories[index - 12] || '기타';
            } else if (index < 24) {
              region = '인천';
              category = categories[index - 18] || '기타';
            } else {
              region = '경기';
              category = categories[index - 24] || '기타';
            }
          }
          
          rows.push({
            region,
            category,
            subcategory: `2025-07`,
            value: parsedCell.value,
            formattedValue: parsedCell.raw
          });
        }
      });
    });
    
    return rows.sort((a, b) => {
      if (a.region !== b.region) return a.region.localeCompare(b.region);
      return a.category.localeCompare(b.category);
    });
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
      
      // API에서 raw_data를 반환하는 경우 statistics로 변환
      if (data.raw_data && !data.statistics) {
        data.statistics = data.raw_data;
      }
      
      setStoredData(data);
      
      if (data.statistics) {
        const parsed = parseHousingData(data.statistics);
        setParsedData(parsed);
      }
    } catch (error) {
      console.error('Failed to fetch stored data:', error);
      setError(`데이터 로드 실패: ${error instanceof Error ? error.message : '알 수 없는 오류'}`);
    }
  };

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      
      await fetchStoredData();
      
      setLoading(false);
    };

    if (statName) {
      loadData();
    }
  }, [statName]);

  const renderStructuredData = () => {
    if (!parsedData.length) {
      return (
        <div className="text-center py-8">
          <p className="text-gray-500">구조화된 데이터를 생성할 수 없습니다</p>
        </div>
      );
    }

    const groupedData = parsedData.reduce((acc, row) => {
      if (!acc[row.region]) {
        acc[row.region] = [];
      }
      acc[row.region].push(row);
      return acc;
    }, {} as Record<string, HousingDataRow[]>);

    return (
      <div className="space-y-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">주택건설실적통계 (2025년 7월)</h3>
          
          {Object.entries(groupedData).map(([region, rows]) => (
            <div key={region} className="mb-6">
              <h4 className="text-md font-semibold mb-3 text-blue-600 border-b pb-2">
                📍 {region}
              </h4>
              
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 border-b">
                      <th className="text-left p-3">구분</th>
                      <th className="text-right p-3">건수</th>
                      <th className="text-right p-3">비율(%)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((row, index) => {
                      const total = rows.find(r => r.category === '계')?.value || 1;
                      const percentage = row.category !== '계' ? ((row.value / total) * 100).toFixed(1) : '100.0';
                      
                      return (
                        <tr key={index} className={`border-b hover:bg-gray-50 ${
                          row.category === '계' ? 'font-semibold bg-blue-50' : ''
                        }`}>
                          <td className="p-3">
                            {row.category === '계' ? '🏠 전체' : `📊 ${row.category}`}
                          </td>
                          <td className="text-right p-3 font-mono">
                            {row.formattedValue}
                          </td>
                          <td className="text-right p-3 text-gray-600">
                            {row.category !== '계' ? `${percentage}%` : '-'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  };

  const renderRawData = () => {
    if (!storedData) {
      return (
        <div className="text-center py-8">
          <p className="text-gray-500">원시 데이터를 찾을 수 없습니다</p>
        </div>
      );
    }

    return (
      <div className="space-y-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">원시 데이터 정보</h3>
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div>
              <p className="text-sm font-medium text-gray-600">캐시 키</p>
              <p className="text-sm font-mono">{storedData.cache_key || 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">저장 시간</p>
              <p className="text-sm">{storedData.saved_at ? new Date(storedData.saved_at).toLocaleString() : 'N/A'}</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">데이터셋 개수</p>
              <p className="text-sm">{storedData.data_count || 0}개</p>
            </div>
            <div>
              <p className="text-sm font-medium text-gray-600">원본 URL</p>
              <p className="text-sm text-blue-600 break-all">{storedData.stat_url || 'N/A'}</p>
            </div>
          </div>
        </div>

        {storedData.statistics?.map((stat: any, index: number) => (
          <div key={index} className="bg-white p-6 rounded-lg shadow">
            <h4 className="text-lg font-semibold mb-4">
              📊 데이터셋 {index + 1} ({stat.year}년)
            </h4>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(stat.data || {}).slice(0, 15).map(([key, value]) => {
                const parsedData = parseIBSheetData(value as string);
                
                return (
                  <div 
                    key={key} 
                    className={`p-4 rounded border ${
                      parsedData.isNumeric 
                        ? 'bg-green-50 border-green-200' 
                        : 'bg-gray-50 border-gray-200'
                    }`}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <span className="text-xs font-mono text-gray-500">{key}</span>
                      <span className={`text-xs px-2 py-1 rounded ${
                        parsedData.isNumeric 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {parsedData.unit}
                      </span>
                    </div>
                    <div className={`text-sm ${
                      parsedData.isNumeric 
                        ? 'font-semibold text-green-800' 
                        : 'text-gray-700'
                    }`}>
                      {parsedData.isNumeric ? parsedData.raw : String(parsedData.value).substring(0, 50)}
                      {!parsedData.isNumeric && String(parsedData.value).length > 50 && '...'}
                    </div>
                  </div>
                );
              })}
            </div>
            
            {Object.keys(stat.data || {}).length > 15 && (
              <div className="mt-4 text-center text-gray-500">
                ... 및 {Object.keys(stat.data || {}).length - 15}개 필드 더 있음
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  const renderSummary = () => {
    if (!storedData || !parsedData.length) return null;

    const totalValue = parsedData.reduce((sum, row) => sum + (row.value || 0), 0);
    const numericCount = parsedData.length;
    const avgValue = numericCount > 0 ? totalValue / numericCount : 0;
    const maxValue = Math.max(...parsedData.map(row => row.value));
    const minValue = Math.min(...parsedData.map(row => row.value));

    const regions = Array.from(new Set(parsedData.map(row => row.region)));
    const categories = Array.from(new Set(parsedData.map(row => row.category)));

    return (
      <div className="space-y-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">📈 데이터 요약</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-blue-50 rounded">
              <p className="text-sm font-medium text-blue-600">총 건수</p>
              <p className="text-2xl font-bold text-blue-800">{totalValue.toLocaleString()}</p>
            </div>
            <div className="text-center p-4 bg-green-50 rounded">
              <p className="text-sm font-medium text-green-600">평균값</p>
              <p className="text-2xl font-bold text-green-800">{Math.round(avgValue).toLocaleString()}</p>
            </div>
            <div className="text-center p-4 bg-orange-50 rounded">
              <p className="text-sm font-medium text-orange-600">최댓값</p>
              <p className="text-2xl font-bold text-orange-800">{maxValue.toLocaleString()}</p>
            </div>
            <div className="text-center p-4 bg-purple-50 rounded">
              <p className="text-sm font-medium text-purple-600">최솟값</p>
              <p className="text-2xl font-bold text-purple-800">{minValue.toLocaleString()}</p>
            </div>
          </div>
        </div>

        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="text-lg font-semibold mb-4">📊 데이터 분포</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium mb-3">지역별 분포</h4>
              <div className="space-y-2">
                {regions.map((region) => {
                  const regionData = parsedData.filter(row => row.region === region);
                  const regionTotal = regionData.reduce((sum, row) => sum + row.value, 0);
                  const percentage = totalValue > 0 ? ((regionTotal / totalValue) * 100).toFixed(1) : '0';
                  
                  return (
                    <div key={region} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                      <span className="font-medium">{region}</span>
                      <div className="text-right">
                        <span className="font-mono text-sm">{regionTotal.toLocaleString()}</span>
                        <span className="text-xs text-gray-500 ml-2">({percentage}%)</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            
            <div>
              <h4 className="font-medium mb-3">규모별 분포</h4>
              <div className="space-y-2">
                {categories.slice(0, 6).map((category) => {
                  const categoryData = parsedData.filter(row => row.category === category);
                  const categoryTotal = categoryData.reduce((sum, row) => sum + row.value, 0);
                  const percentage = totalValue > 0 ? ((categoryTotal / totalValue) * 100).toFixed(1) : '0';
                  
                  return (
                    <div key={category} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                      <span className="font-medium">{category}</span>
                      <div className="text-right">
                        <span className="font-mono text-sm">{categoryTotal.toLocaleString()}</span>
                        <span className="text-xs text-gray-500 ml-2">({percentage}%)</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
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
            <p className="mt-4 text-gray-600">데이터를 분석하는 중...</p>
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
            <h1 className="text-2xl font-bold">🔍 데이터 분석: {statName}</h1>
          </div>
          
          {error && (
            <div className="mt-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
              ⚠️ {error}
            </div>
          )}
        </div>

        <div className="mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('structured')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'structured'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                📊 구조화된 데이터
              </button>
              <button
                onClick={() => setActiveTab('raw')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'raw'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                🗂️ 원시 데이터
              </button>
              <button
                onClick={() => setActiveTab('summary')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'summary'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                📈 요약 통계
              </button>
            </nav>
          </div>
        </div>

        <div className="tab-content">
          {activeTab === 'structured' && renderStructuredData()}
          {activeTab === 'raw' && renderRawData()}
          {activeTab === 'summary' && renderSummary()}
        </div>
      </div>
    </div>
  );
};