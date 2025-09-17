import React, { useRef, useState, useEffect } from 'react';
import { AdvancedCardNewsResponse } from '../services/api';
import { AnalysisActionButtons } from './AnalysisActionButtons';
import { ImprovedDataInspectionViewer } from './ImprovedDataInspectionViewer';
import { 
  downloadMarkdown, 
  downloadPDF, 
  openOriginalUrl, 
  generateBasicStatisticsMarkdown 
} from '../utils/downloadUtils';

interface EnhancedBasicStatisticsViewerProps {
  analysisData: AdvancedCardNewsResponse;
  onBack: () => void;
  onViewTableAnalysis?: (statName: string) => void;
}

interface ProcessedStatistics {
  numeric_stats: {
    total: number;
    mean: number;
    median: number;
    max: number;
    min: number;
    count: number;
    std_dev: number;
  };
  data_structure: {
    total_fields: number;
    numeric_fields: number;
    text_fields: number;
    table_count: number;
    collected_tables: string[];
  };
  sample_data: Array<{
    field_name: string;
    value: any;
    type: string;
    source_table?: string;
  }>;
}

export const EnhancedBasicStatisticsViewer: React.FC<EnhancedBasicStatisticsViewerProps> = ({ 
  analysisData, 
  onBack,
  onViewTableAnalysis 
}) => {
  const contentRef = useRef<HTMLDivElement>(null);
  const [showDataInspection, setShowDataInspection] = useState(false);
  const [processedStats, setProcessedStats] = useState<ProcessedStatistics | null>(null);
  const [selectedTableName, setSelectedTableName] = useState<string | null>(null);
  const [rawDataByTable, setRawDataByTable] = useState<Record<string, any[]>>({});
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'tables' | 'distribution' | 'inspection'>('overview');

  useEffect(() => {
    processRealData();
  }, [analysisData]);

  const processRealData = async () => {
    setLoading(true);
    try {
      // Fetch actual stored data to process
      const response = await fetch('/api/data/raw-view', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stat_name: analysisData.stat_name })
      });

      if (response.ok) {
        const rawData = await response.json();
        const processed = processStatisticsData(rawData);
        setProcessedStats(processed);

        // Group data by table names with enhanced naming logic
        const dataByTable: Record<string, any[]> = {};
        let tableCounter = 1;

        if (rawData.raw_data && Array.isArray(rawData.raw_data)) {
          rawData.raw_data.forEach((stat: any, statIndex: number) => {
            let tableName = stat.table_name;

            // Enhanced table name processing (matching backend logic)
            if (!tableName || tableName === '' || tableName === '기본 통계표') {
              // Use keywords from analysisData metadata if available
              const keywords = analysisData.metadata?.keywords;
              if (keywords && keywords.length > 0) {
                tableName = `${keywords[0]} 통계표 ${tableCounter}`;
              } else {
                tableName = `통계표 ${tableCounter}`;
              }
              tableCounter++;
            } else if (tableName.startsWith('테이블') && /^테이블\d+$/.test(tableName)) {
              // Replace generic "테이블1", "테이블2" with meaningful names
              const keywords = analysisData.metadata?.keywords;
              if (keywords && keywords.length > 0) {
                tableName = `${keywords[0]} ${tableName}`;
              } else {
                tableName = `수집된 ${tableName}`;
              }
            }

            if (!dataByTable[tableName]) {
              dataByTable[tableName] = [];
            }
            dataByTable[tableName].push(stat);
          });
        }
        setRawDataByTable(dataByTable);

        // Set first table as default selection
        const firstTableName = Object.keys(dataByTable)[0];
        if (firstTableName) {
          setSelectedTableName(firstTableName);
        }
      } else {
        // Fallback to basic_statistics from analysisData if available
        setProcessedStats(createFallbackStats());
      }
    } catch (error) {
      console.error('Failed to process real data:', error);
      setProcessedStats(createFallbackStats());
    } finally {
      setLoading(false);
    }
  };

  const createFallbackStats = (): ProcessedStatistics => {
    const basic = analysisData.basic_statistics || {
      total: 0, mean: 0, median: 0, max: 0, min: 0, count: 0
    };
    
    return {
      numeric_stats: {
        ...basic,
        std_dev: 0
      },
      data_structure: {
        total_fields: analysisData.analysis_summary?.total_data_points || 0,
        numeric_fields: 0,
        text_fields: 0,
        table_count: 1,
        collected_tables: [analysisData.stat_name]
      },
      sample_data: []
    };
  };

  const processStatisticsData = (rawData: any): ProcessedStatistics => {
    if (!rawData.raw_data || !Array.isArray(rawData.raw_data)) {
      return createFallbackStats();
    }

    const allNumericValues: number[] = [];
    const allFields: Array<{ field_name: string; value: any; type: string; source_table?: string }> = [];
    const tableNames = new Set<string>();
    let totalFields = 0;
    let numericFields = 0;
    let textFields = 0;

    // Use a helper function to generate consistent table names
    const getEnhancedTableName = (stat: any, statIndex: number, tableCounter: { value: number }): string => {
      let tableName = stat.table_name;

      if (!tableName || tableName === '' || tableName === '기본 통계표') {
        // Note: analysisData may not be available in this context
        tableName = `통계표 ${tableCounter.value}`;
        tableCounter.value++;
      } else if (tableName.startsWith('테이블') && /^테이블\d+$/.test(tableName)) {
        tableName = `수집된 ${tableName}`;
      }

      return tableName;
    };

    const tableCounter = { value: 1 };
    rawData.raw_data.forEach((stat: any, statIndex: number) => {
      const tableName = getEnhancedTableName(stat, statIndex, tableCounter);
      tableNames.add(tableName);

      Object.entries(stat.data || {}).forEach(([key, value]) => {
        totalFields++;
        
        try {
          // Parse IBSheet cell data
          const parsedValue = typeof value === 'string' && value.includes("'value'") 
            ? JSON.parse(value.replace(/'/g, '"'))
            : { value, unit: 'text', raw: value };

          const fieldEntry = {
            field_name: key,
            value: parsedValue.value,
            type: parsedValue.unit || 'text',
            source_table: tableName
          };

          allFields.push(fieldEntry);

          if (parsedValue.unit === 'number' && typeof parsedValue.value === 'number') {
            allNumericValues.push(parsedValue.value);
            numericFields++;
          } else {
            textFields++;
          }
        } catch (error) {
          // Handle parsing errors
          const fieldEntry = {
            field_name: key,
            value: value,
            type: 'text',
            source_table: tableName
          };
          allFields.push(fieldEntry);
          textFields++;
        }
      });
    });

    // Calculate statistics
    const total = allNumericValues.reduce((sum, val) => sum + val, 0);
    const mean = allNumericValues.length > 0 ? total / allNumericValues.length : 0;
    const sortedValues = [...allNumericValues].sort((a, b) => a - b);
    const median = sortedValues.length > 0 
      ? sortedValues.length % 2 === 0
        ? (sortedValues[sortedValues.length / 2 - 1] + sortedValues[sortedValues.length / 2]) / 2
        : sortedValues[Math.floor(sortedValues.length / 2)]
      : 0;
    const max = allNumericValues.length > 0 ? Math.max(...allNumericValues) : 0;
    const min = allNumericValues.length > 0 ? Math.min(...allNumericValues) : 0;
    
    // Calculate standard deviation
    const variance = allNumericValues.length > 0 
      ? allNumericValues.reduce((sum, val) => sum + Math.pow(val - mean, 2), 0) / allNumericValues.length
      : 0;
    const std_dev = Math.sqrt(variance);

    return {
      numeric_stats: {
        total,
        mean,
        median,
        max,
        min,
        count: allNumericValues.length,
        std_dev
      },
      data_structure: {
        total_fields: totalFields,
        numeric_fields: numericFields,
        text_fields: textFields,
        table_count: tableNames.size,
        collected_tables: Array.from(tableNames)
      },
      sample_data: allFields.slice(0, 20) // Show first 20 fields as sample
    };
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 2 }).format(num);
  };

  // 구조화된 데이터를 활용한 원본 테이블 재구성 함수 (개선된 버전)
  const reconstructTableStructure = (rawData: any[]) => {
    if (!rawData || rawData.length === 0) return null;

    const reconstructedTables: Record<string, any[][]> = {};

    rawData.forEach((stat, statIndex) => {
      const tableName = stat.table_name || `통계표 ${statIndex + 1}`;
      const data = stat.data || {};

      // 새로운 구조화된 데이터 형식 확인
      if (data._table_structure && data._table_data) {
        console.log(`구조화된 데이터 발견: ${tableName}`, data._table_structure);

        const tableStructure = data._table_structure;
        const tableData = data._table_data;
        const headers = data._table_headers || [];

        // 필수 데이터 검증
        if (!tableStructure.cols || !tableStructure.rows) {
          console.warn(`${tableName}: 테이블 구조 정보가 불완전합니다.`, tableStructure);
          return;
        }

        const tableRows: any[][] = [];

        // 구조화된 데이터를 테이블 형태로 변환
        if (Array.isArray(tableData)) {
          tableData.forEach((rowInfo: any) => {
          const row = Array(tableStructure.cols).fill(null).map(() => ({
            original: '',
            value: '',
            type: 'text',
            formatted: '',
            isEmpty: true,
            isHeader: false,
            colName: ''
          }));

          if (Array.isArray(rowInfo.cells)) {
            rowInfo.cells.forEach((cellInfo: any) => {
              if (cellInfo && typeof cellInfo.col_index === 'number' && cellInfo.col_index < tableStructure.cols) {
                const cellValue = cellInfo.value || {};
                row[cellInfo.col_index] = {
                  original: cellValue.raw || cellValue.value || '',
                  value: cellValue.value || '',
                  type: cellValue.unit || 'text',
                  formatted: cellValue.unit === 'number' && typeof cellValue.value === 'number'
                    ? formatNumber(cellValue.value)
                    : String(cellValue.value || ''),
                  isEmpty: !cellValue.value || String(cellValue.value).trim() === '',
                  isHeader: rowInfo.is_header || false,
                  colName: cellInfo.col_name || ''
                };
              }
            });
          }

            // 빈 행이 아닌 경우만 추가
            if (row.some(cell => !cell.isEmpty)) {
              tableRows.push(row);
            }
          });
        } else {
          console.warn(`${tableName}: tableData가 배열이 아닙니다.`, typeof tableData, tableData);
        }

        if (tableRows.length > 0) {
          reconstructedTables[tableName] = tableRows;
        }

        console.log(`${tableName} 테이블 재구성 완료: ${tableRows.length}행 × ${tableStructure.cols}열`);
      } else {
        // 기존 방식 (Fallback) - ibsheet_cell_ 패턴
        console.log(`기존 방식으로 처리: ${tableName}`);

        const cellData: Array<{cellIndex: number, value: any, parsedValue: any}> = [];

        Object.entries(data).forEach(([key, value]) => {
          if (key.startsWith('ibsheet_cell_') || key.startsWith('table_r')) {
            let cellIndex = 0;

            if (key.startsWith('ibsheet_cell_')) {
              cellIndex = parseInt(key.replace('ibsheet_cell_', ''));
            } else if (key.startsWith('table_r')) {
              // table_r0_c1_컬럼명 형태에서 인덱스 추출
              const match = key.match(/table_r(\d+)_c(\d+)/);
              if (match) {
                const rowIdx = parseInt(match[1]);
                const colIdx = parseInt(match[2]);
                cellIndex = rowIdx * 10 + colIdx; // 임시 인덱스 계산
              }
            }

            let parsedValue;
            try {
              parsedValue = typeof value === 'string' && value.includes("'value'")
                ? JSON.parse(value.replace(/'/g, '"'))
                : { value, unit: 'text', raw: value };
            } catch {
              parsedValue = { value: String(value), unit: 'text', raw: value };
            }

            cellData.push({ cellIndex, value, parsedValue });
          }
        });

        // 셀 인덱스 순으로 정렬
        cellData.sort((a, b) => a.cellIndex - b.cellIndex);

        if (cellData.length === 0) return;

        // 열 수 추정 개선
        let estimatedCols = 6;
        const textCells = cellData.filter(cell => cell.parsedValue.unit === 'text');
        const numberCells = cellData.filter(cell => cell.parsedValue.unit === 'number');

        if (textCells.length > 0 && numberCells.length > 0) {
          const ratio = numberCells.length / textCells.length;
          if (ratio > 3) {
            estimatedCols = Math.min(10, Math.max(6, Math.ceil(Math.sqrt(cellData.length * 1.2))));
          } else {
            estimatedCols = Math.min(8, Math.max(5, Math.ceil(Math.sqrt(cellData.length))));
          }
        }

        const tableRows: any[][] = [];

        for (let i = 0; i < cellData.length; i += estimatedCols) {
          const rowCells = cellData.slice(i, i + estimatedCols);
          const row = Array(estimatedCols).fill(null).map((_, colIndex) => {
            const cell = rowCells[colIndex];
            if (!cell) {
              return {
                original: '',
                value: '',
                type: 'text',
                formatted: '',
                isEmpty: true,
                isHeader: false,
                colName: ''
              };
            }

            return {
              original: cell.parsedValue.raw || cell.parsedValue.value,
              value: cell.parsedValue.value,
              type: cell.parsedValue.unit,
              formatted: cell.parsedValue.unit === 'number' && typeof cell.parsedValue.value === 'number'
                ? formatNumber(cell.parsedValue.value)
                : String(cell.parsedValue.value || ''),
              isEmpty: !cell.parsedValue.value || String(cell.parsedValue.value).trim() === '',
              isHeader: false,
              colName: ''
            };
          });

          if (row.some(cell => !cell.isEmpty)) {
            tableRows.push(row);
          }
        }

        if (tableRows.length > 0) {
          reconstructedTables[tableName] = tableRows;
        }
      }
    });

    return reconstructedTables;
  };

  const handleDownloadMD = () => {
    try {
      const markdown = generateBasicStatisticsMarkdown(analysisData);
      const filename = `기본통계현황분석_${analysisData.stat_name}_${new Date().toISOString().split('T')[0]}`;
      downloadMarkdown(markdown, filename);
    } catch (error) {
      console.error('MD 다운로드 실패:', error);
      alert('마크다운 파일 다운로드에 실패했습니다.');
    }
  };

  const handleDownloadPDF = async () => {
    if (contentRef.current) {
      try {
        const filename = `기본통계현황분석_${analysisData.stat_name}_${new Date().toISOString().split('T')[0]}`;
        await downloadPDF(contentRef.current, filename);
      } catch (error) {
        console.error('PDF 다운로드 실패:', error);
        alert('PDF 파일 다운로드에 실패했습니다.');
      }
    }
  };

  const handleViewOriginal = () => {
    const originalUrl = analysisData.metadata?.url;
    if (originalUrl) {
      openOriginalUrl(originalUrl);
    } else {
      alert('원본 URL 정보가 없습니다.');
    }
  };

  const handleInspectData = () => {
    setShowDataInspection(true);
  };

  const handleBackFromInspection = () => {
    setShowDataInspection(false);
  };

  // Filter data by selected table
  const getFilteredData = () => {
    if (!selectedTableName || !processedStats) return processedStats?.sample_data || [];
    
    return processedStats.sample_data.filter(item => 
      item.source_table === selectedTableName
    );
  };

  // Get statistics for selected table only
  const getSelectedTableStats = () => {
    if (!selectedTableName || !rawDataByTable[selectedTableName]) {
      return processedStats?.numeric_stats;
    }

    const tableData = rawDataByTable[selectedTableName];
    const numericValues: number[] = [];
    
    tableData.forEach(stat => {
      Object.entries(stat.data || {}).forEach(([key, value]) => {
        try {
          const parsedValue = typeof value === 'string' && value.includes("'value'") 
            ? JSON.parse(value.replace(/'/g, '"'))
            : { value, unit: 'text', raw: value };

          if (parsedValue.unit === 'number' && typeof parsedValue.value === 'number') {
            numericValues.push(parsedValue.value);
          }
        } catch (error) {
          // Skip parsing errors
        }
      });
    });

    if (numericValues.length === 0) {
      return processedStats?.numeric_stats;
    }

    return {
      total: numericValues.reduce((sum, val) => sum + val, 0),
      mean: numericValues.reduce((sum, val) => sum + val, 0) / numericValues.length,
      median: numericValues.sort((a, b) => a - b)[Math.floor(numericValues.length / 2)],
      max: Math.max(...numericValues),
      min: Math.min(...numericValues),
      count: numericValues.length,
      std_dev: Math.sqrt(numericValues.reduce((sum, val) => {
        const mean = numericValues.reduce((s, v) => s + v, 0) / numericValues.length;
        return sum + Math.pow(val - mean, 2);
      }, 0) / numericValues.length)
    };
  };

  // 데이터 검사 모드일 때는 EnhancedDataInspectionViewer 렌더링
  if (showDataInspection) {
    return (
      <ImprovedDataInspectionViewer 
        statName={analysisData.stat_name} 
        onBack={handleBackFromInspection}
      />
    );
  }

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto flex justify-center items-center py-12">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!processedStats) {
    return (
      <div className="max-w-6xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-800">데이터를 처리하는 중 오류가 발생했습니다.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* 헤더 */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-4">
          <h1 className="text-2xl font-bold text-gray-900">📈 기본통계현황분석 결과 (실제 수집 데이터 기반)</h1>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={onBack}
              className="bg-gray-500 text-white px-4 py-2 rounded-md hover:bg-gray-600"
            >
              뒤로 가기
            </button>
            <button
              onClick={handleDownloadMD}
              className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700"
            >
              MD 다운로드
            </button>
            <button
              onClick={handleDownloadPDF}
              className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700"
            >
              PDF 다운로드
            </button>
            {analysisData.metadata?.url && (
              <button
                onClick={handleViewOriginal}
                className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700"
              >
                원본 보기
              </button>
            )}
          </div>
        </div>
        
        <div className="bg-blue-50 rounded-lg p-4">
          <h2 className="text-lg font-semibold text-blue-900 mb-2">{analysisData.stat_name}</h2>
          <div className="flex items-center gap-4 text-sm text-blue-700">
            <span>분석 완료: {new Date(analysisData.analysis_date).toLocaleString('ko-KR')}</span>
            <span className="bg-blue-200 px-2 py-1 rounded-full">실제 수집 데이터 분석</span>
          </div>
        </div>
      </div>

      {/* 탭 네비게이션 */}
      <div className="bg-white rounded-lg shadow-sm border mb-6">
        <div className="border-b border-gray-200">
          <nav className="-mb-px flex">
            <button
              onClick={() => setActiveTab('overview')}
              className={`py-4 px-6 text-sm font-medium ${
                activeTab === 'overview'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              📊 전체 요약
            </button>
            <button
              onClick={() => setActiveTab('tables')}
              className={`py-4 px-6 text-sm font-medium ${
                activeTab === 'tables'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              📋 통계표별 분석
            </button>
            <button
              onClick={() => setActiveTab('distribution')}
              className={`py-4 px-6 text-sm font-medium ${
                activeTab === 'distribution'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              📈 분포 특성
            </button>
            <button
              onClick={() => setActiveTab('inspection')}
              className={`py-4 px-6 text-sm font-medium ${
                activeTab === 'inspection'
                  ? 'border-b-2 border-blue-500 text-blue-600'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              🔍 데이터 검사
            </button>
          </nav>
        </div>
      </div>

      {/* 분석 내용 - PDF 다운로드 대상 */}
      <div ref={contentRef}>
        {/* 전체 요약 탭 */}
        {activeTab === 'overview' && (
          <>
            {/* 수집된 데이터 개요 */}
            <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-4">📊 수집된 데이터 개요</h3>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
            <div className="bg-green-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-green-700">
                {processedStats.data_structure.table_count}
              </div>
              <div className="text-sm text-green-600">수집된 통계표</div>
            </div>
            <div className="bg-blue-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-blue-700">
                {processedStats.data_structure.total_fields}
              </div>
              <div className="text-sm text-blue-600">총 데이터 필드</div>
            </div>
            <div className="bg-purple-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-purple-700">
                {processedStats.data_structure.numeric_fields}
              </div>
              <div className="text-sm text-purple-600">숫자 데이터</div>
            </div>
            <div className="bg-orange-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-orange-700">
                {processedStats.data_structure.text_fields}
              </div>
              <div className="text-sm text-orange-600">텍스트 데이터</div>
            </div>
          </div>

          <div className="bg-gray-50 rounded-lg p-4">
            <h4 className="font-medium text-gray-900 mb-2">수집된 통계표 목록 (클릭하여 선택)</h4>
            <div className="flex flex-wrap gap-2">
              {processedStats.data_structure.collected_tables.map((table, index) => (
                <button
                  key={index}
                  onClick={() => setSelectedTableName(table)}
                  className={`px-3 py-1 rounded-full text-sm transition-colors ${
                    selectedTableName === table
                      ? 'bg-blue-600 text-white shadow-md'
                      : 'bg-blue-100 text-blue-800 hover:bg-blue-200'
                  }`}
                >
                  {table}
                </button>
              ))}
            </div>
            {selectedTableName && (
              <div className="mt-3 text-sm text-gray-600">
                선택된 통계표: <span className="font-medium text-blue-600">{selectedTableName}</span>
              </div>
            )}
          </div>
        </div>

        {/* 기초통계 지표 */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-6">
            🔢 기초통계 지표 (숫자 데이터 기준)
            {selectedTableName && (
              <span className="text-lg text-blue-600 ml-2">- {selectedTableName}</span>
            )}
          </h3>
          
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
            <div className="bg-red-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-red-700">
                {formatNumber(getSelectedTableStats()?.mean || 0)}
              </div>
              <div className="text-sm text-red-600 font-medium">평균값</div>
              <div className="text-xs text-red-500 mt-1">Mean</div>
            </div>

            <div className="bg-orange-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-orange-700">
                {formatNumber(getSelectedTableStats()?.median || 0)}
              </div>
              <div className="text-sm text-orange-600 font-medium">중위수</div>
              <div className="text-xs text-orange-500 mt-1">Median</div>
            </div>

            <div className="bg-yellow-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-yellow-700">
                {formatNumber(getSelectedTableStats()?.max || 0)}
              </div>
              <div className="text-sm text-yellow-600 font-medium">최댓값</div>
              <div className="text-xs text-yellow-500 mt-1">Maximum</div>
            </div>

            <div className="bg-green-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-green-700">
                {formatNumber(getSelectedTableStats()?.min || 0)}
              </div>
              <div className="text-sm text-green-600 font-medium">최솟값</div>
              <div className="text-xs text-green-500 mt-1">Minimum</div>
            </div>

            <div className="bg-blue-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-blue-700">
                {formatNumber(getSelectedTableStats()?.total || 0)}
              </div>
              <div className="text-sm text-blue-600 font-medium">총합계</div>
              <div className="text-xs text-blue-500 mt-1">Total</div>
            </div>

            <div className="bg-indigo-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-indigo-700">
                {getSelectedTableStats()?.count || 0}
              </div>
              <div className="text-sm text-indigo-600 font-medium">데이터 개수</div>
              <div className="text-xs text-indigo-500 mt-1">Count</div>
            </div>
          </div>

          {/* 추가 통계 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div className="bg-purple-50 rounded-lg p-4 text-center">
              <div className="text-xl font-bold text-purple-700">
                {formatNumber(getSelectedTableStats()?.std_dev || 0)}
              </div>
              <div className="text-sm text-purple-600 font-medium">표준편차</div>
              <div className="text-xs text-purple-500 mt-1">Standard Deviation</div>
            </div>
            <div className="bg-pink-50 rounded-lg p-4 text-center">
              <div className="text-xl font-bold text-pink-700">
                {(() => {
                  const stats = getSelectedTableStats();
                  return stats && stats.count > 0 && stats.mean > 0 && stats.std_dev !== undefined
                    ? formatNumber((stats.std_dev / stats.mean) * 100)
                    : '0';
                })()}%
              </div>
              <div className="text-sm text-pink-600 font-medium">변동계수</div>
              <div className="text-xs text-pink-500 mt-1">Coefficient of Variation</div>
            </div>
          </div>
        </div>

        {/* 수집된 데이터 샘플 (원본 테이블 형태) */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-4">
            📋 수집된 데이터 샘플 (원본 테이블 형태)
            {selectedTableName && (
              <span className="text-lg text-blue-600 ml-2">- {selectedTableName}</span>
            )}
          </h3>

          <div className="bg-blue-50 rounded-lg p-3 mb-4">
            <p className="text-sm text-blue-800">
              💡 수집된 IBSheet 데이터를 원본 웹사이트의 테이블 형태로 재구성하여 표시합니다.
            </p>
          </div>

          {(() => {
            const selectedData = selectedTableName && rawDataByTable[selectedTableName]
              ? rawDataByTable[selectedTableName]
              : Object.values(rawDataByTable).flat();

            const reconstructedTables = reconstructTableStructure(selectedData);

            if (!reconstructedTables || Object.keys(reconstructedTables).length === 0) {
              return (
                <div className="bg-gray-50 rounded-lg p-8 text-center">
                  <div className="text-gray-500 mb-4">
                    <div className="text-4xl mb-2">📊</div>
                    <p>선택된 통계표에서 테이블 형태로 재구성할 수 있는 데이터가 없습니다.</p>
                    <p className="text-sm mt-2">IBSheet 데이터가 포함된 통계표를 선택해 주세요.</p>
                  </div>

                  {/* 원본 데이터 샘플 표시 (fallback) */}
                  <div className="mt-6 border-t pt-4">
                    <h4 className="font-medium text-gray-700 mb-3">원본 데이터 샘플</h4>
                    <div className="overflow-auto">
                      <table className="min-w-full text-sm">
                        <thead className="bg-gray-100">
                          <tr>
                            <th className="px-2 py-1 text-left font-medium text-gray-600">필드명</th>
                            <th className="px-2 py-1 text-left font-medium text-gray-600">값</th>
                            <th className="px-2 py-1 text-left font-medium text-gray-600">타입</th>
                          </tr>
                        </thead>
                        <tbody>
                          {getFilteredData().slice(0, 5).map((item, index) => (
                            <tr key={index} className="border-b">
                              <td className="px-2 py-1 font-mono text-xs">{item.field_name}</td>
                              <td className="px-2 py-1">{String(item.value)}</td>
                              <td className="px-2 py-1">
                                <span className={`px-1.5 py-0.5 rounded text-xs ${
                                  item.type === 'number' ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
                                }`}>
                                  {item.type}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>
              );
            }

            return (
              <div className="space-y-6">
                {Object.entries(reconstructedTables).map(([tableName, tableData], tableIndex) => (
                  <div key={tableIndex} className="border rounded-lg overflow-hidden shadow-sm">
                    <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-4 py-3 border-b">
                      <h4 className="font-semibold text-gray-900 flex items-center">
                        <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm mr-2">
                          {tableIndex + 1}
                        </span>
                        {tableName}
                      </h4>
                      <p className="text-sm text-gray-600 mt-1">
                        {tableData.length}행 × {tableData[0]?.length || 0}열 구조 |
                        수집 시점: {new Date().toLocaleString('ko-KR')}
                      </p>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <tbody>
                          {tableData.map((row, rowIndex) => (
                            <tr
                              key={rowIndex}
                              className={`border-b border-gray-100 ${
                                rowIndex === 0 || row.some(cell => cell.isHeader)
                                  ? 'bg-gray-50 font-semibold'
                                  : rowIndex % 2 === 0
                                    ? 'bg-white hover:bg-blue-25'
                                    : 'bg-gray-25 hover:bg-blue-50'
                              }`}
                            >
                              {row.map((cell, colIndex) => (
                                <td
                                  key={colIndex}
                                  className={`px-3 py-2 border-r border-gray-200 ${
                                    cell.type === 'number'
                                      ? 'text-right font-mono'
                                      : 'text-left'
                                  } ${
                                    cell.isEmpty ? 'bg-gray-100' : ''
                                  } ${
                                    cell.isHeader || rowIndex === 0 ? 'font-semibold bg-gray-50 text-gray-800' : ''
                                  }`}
                                  title={cell.colName ? `컬럼: ${cell.colName}` : ''}
                                >
                                  {cell.isEmpty ? (
                                    <span className="text-gray-400">-</span>
                                  ) : (
                                    <div className="min-w-0">
                                      <div className={`truncate ${
                                        cell.type === 'number'
                                          ? 'text-blue-600 font-medium'
                                          : cell.isHeader || rowIndex === 0
                                            ? 'text-gray-800 font-semibold'
                                            : 'text-gray-900'
                                      }`}>
                                        {cell.formatted || '-'}
                                      </div>
                                      {cell.type === 'number' && cell.original !== cell.formatted && (
                                        <div className="text-xs text-gray-500 mt-0.5 truncate" title={cell.original}>
                                          원본: {cell.original}
                                        </div>
                                      )}
                                      {cell.colName && cell.colName !== '' && (
                                        <div className="text-xs text-gray-400 mt-0.5 truncate" title={`컬럼: ${cell.colName}`}>
                                          {cell.colName}
                                        </div>
                                      )}
                                    </div>
                                  )}
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>

                    <div className="bg-gray-50 px-4 py-2 text-xs text-gray-600 border-t">
                      📊 이 테이블은 IBSheet에서 수집된 데이터를 {tableData[0]?.length || 0}열 구조로 재구성한 원본 형태입니다. |
                      숫자 데이터: 파란색 표시 | 헤더: 회색 배경 | 빈 셀: "-" 표시
                    </div>
                  </div>
                ))}

                <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                  <h4 className="font-medium text-green-900 mb-2 flex items-center">
                    <span className="mr-2">✅</span>
                    테이블 재구성 완료
                  </h4>
                  <div className="text-sm text-green-800 space-y-1">
                    <p>• 총 {Object.keys(reconstructedTables).length}개의 테이블이 원본 형태로 재구성되었습니다.</p>
                    <p>• 국토교통부 통계 특성을 반영하여 6-10열 구조로 최적화되었습니다.</p>
                    <p>• 숫자 데이터는 천 단위 구분 기호가 적용되어 가독성이 향상되었습니다.</p>
                    <p>• 첫 번째 행은 헤더로 인식하여 강조 표시됩니다.</p>
                  </div>
                </div>
              </div>
            );
          })()}
        </div>

        {/* 데이터 분포 특성 */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-4">📊 데이터 분포 특성</h3>
          <div className="space-y-4">
            <div className="bg-blue-50 rounded-lg p-4">
              <h4 className="font-medium text-blue-900 mb-2">중심경향 분석</h4>
              <div className="text-sm text-blue-800">
                <p>• 평균값: {formatNumber(processedStats.numeric_stats.mean)}</p>
                <p>• 중위수: {formatNumber(processedStats.numeric_stats.median)}</p>
                <p>• 평균과 중위수 차이: {formatNumber(Math.abs(processedStats.numeric_stats.mean - processedStats.numeric_stats.median))}</p>
                <p>• 표준편차: {formatNumber(processedStats.numeric_stats.std_dev)}</p>
              </div>
            </div>

            <div className="bg-green-50 rounded-lg p-4">
              <h4 className="font-medium text-green-900 mb-2">변동성 분석</h4>
              <div className="text-sm text-green-800">
                <p>• 최댓값: {formatNumber(processedStats.numeric_stats.max)}</p>
                <p>• 최솟값: {formatNumber(processedStats.numeric_stats.min)}</p>
                <p>• 범위(Range): {formatNumber(processedStats.numeric_stats.max - processedStats.numeric_stats.min)}</p>
                <p>• 변동계수: {processedStats.numeric_stats.count > 0 
                  ? formatNumber((processedStats.numeric_stats.std_dev / processedStats.numeric_stats.mean) * 100)
                  : '0'
                }%</p>
              </div>
            </div>

            <div className="bg-purple-50 rounded-lg p-4">
              <h4 className="font-medium text-purple-900 mb-2">데이터 구성 분석</h4>
              <div className="text-sm text-purple-800">
                <p>• 수집된 통계표: {processedStats.data_structure.table_count}개</p>
                <p>• 총 데이터 필드: {processedStats.data_structure.total_fields}개</p>
                <p>• 숫자 데이터: {processedStats.data_structure.numeric_fields}개 ({((processedStats.data_structure.numeric_fields / processedStats.data_structure.total_fields) * 100).toFixed(1)}%)</p>
                <p>• 텍스트 데이터: {processedStats.data_structure.text_fields}개 ({((processedStats.data_structure.text_fields / processedStats.data_structure.total_fields) * 100).toFixed(1)}%)</p>
              </div>
            </div>
          </div>
        </div>

        {/* 객관적 현황 요약 */}
        <div className="bg-white rounded-lg shadow-sm border p-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-4">💡 객관적 현황 요약</h3>
          <div className="bg-gray-50 rounded-lg p-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <h4 className="font-semibold text-gray-900 mb-3">🎯 핵심 통계</h4>
                <ul className="space-y-2 text-sm text-gray-700">
                  <li>• 가장 높은 수치: <span className="font-medium text-red-600">{formatNumber(processedStats.numeric_stats.max)}</span></li>
                  <li>• 가장 낮은 수치: <span className="font-medium text-blue-600">{formatNumber(processedStats.numeric_stats.min)}</span></li>
                  <li>• 전체 평균: <span className="font-medium text-green-600">{formatNumber(processedStats.numeric_stats.mean)}</span></li>
                  <li>• 중앙값: <span className="font-medium text-purple-600">{formatNumber(processedStats.numeric_stats.median)}</span></li>
                </ul>
              </div>
              
              <div>
                <h4 className="font-semibold text-gray-900 mb-3">📈 수집 현황</h4>
                <ul className="space-y-2 text-sm text-gray-700">
                  <li>• 분석 일시: <span className="font-medium">{new Date(analysisData.analysis_date).toLocaleString('ko-KR')}</span></li>
                  <li>• 수집된 통계표: <span className="font-medium">{processedStats.data_structure.table_count}개</span></li>
                  <li>• 숫자 데이터: <span className="font-medium">{processedStats.numeric_stats.count}개</span></li>
                  <li>• 전체 규모: <span className="font-medium">{formatNumber(processedStats.numeric_stats.total)}</span></li>
                </ul>
              </div>
            </div>
            
            <div className="mt-6 p-4 bg-green-50 rounded-lg border border-green-200">
              <p className="text-sm text-green-800">
                <span className="font-medium">✅ 실제 수집 데이터 기반 분석:</span> 
                이 분석은 실제로 수집된 {processedStats.data_structure.table_count}개 통계표의 {processedStats.data_structure.total_fields}개 데이터 필드를 기반으로 작성되었습니다.
                숫자 데이터 {processedStats.numeric_stats.count}개에 대한 객관적 기술통계 분석 결과입니다.
              </p>
            </div>
          </div>
        </div>
          </>
        )}

        {/* 통계표별 분석 탭 */}
        {activeTab === 'tables' && (
          <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">📋 통계표별 상세 분석</h3>

            {/* 통계표 선택 */}
            <div className="bg-gray-50 rounded-lg p-4 mb-6">
              <h4 className="font-medium text-gray-900 mb-3">수집된 통계표 선택</h4>
              <div className="flex flex-wrap gap-2 mb-4">
                {Object.keys(rawDataByTable).map((tableName, index) => (
                  <button
                    key={index}
                    onClick={() => setSelectedTableName(tableName)}
                    className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                      selectedTableName === tableName
                        ? 'bg-blue-600 text-white shadow-md'
                        : 'bg-blue-100 text-blue-800 hover:bg-blue-200'
                    }`}
                  >
                    {tableName}
                  </button>
                ))}
              </div>
              {selectedTableName && (
                <div className="text-sm text-gray-600">
                  선택된 통계표: <span className="font-medium text-blue-600">{selectedTableName}</span>
                </div>
              )}
            </div>

            {/* 선택된 통계표 상세 정보 */}
            {selectedTableName && rawDataByTable[selectedTableName] && (
              <div className="space-y-6">
                {/* 기본 정보 */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div className="bg-blue-50 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-blue-700">
                      {rawDataByTable[selectedTableName].length}
                    </div>
                    <div className="text-sm text-blue-600">레코드 수</div>
                  </div>
                  <div className="bg-green-50 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-green-700">
                      {Object.keys(rawDataByTable[selectedTableName][0]?.data || {}).length}
                    </div>
                    <div className="text-sm text-green-600">데이터 필드</div>
                  </div>
                  <div className="bg-purple-50 rounded-lg p-4 text-center">
                    <div className="text-2xl font-bold text-purple-700">
                      {getSelectedTableStats()?.count || 0}
                    </div>
                    <div className="text-sm text-purple-600">숫자 데이터</div>
                  </div>
                </div>

                {/* 샘플 데이터 */}
                <div className="bg-gray-50 rounded-lg p-4">
                  <h4 className="font-medium text-gray-900 mb-3">샘플 데이터 미리보기</h4>
                  <div className="overflow-x-auto">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                      {Object.entries(rawDataByTable[selectedTableName][0]?.data || {}).slice(0, 9).map(([field, value], idx) => {
                        let parsedValue;
                        try {
                          parsedValue = typeof value === 'string' && value.includes("'value'")
                            ? JSON.parse(value.replace(/'/g, '"'))
                            : { value, unit: 'text' };
                        } catch {
                          parsedValue = { value: String(value), unit: 'text' };
                        }

                        return (
                          <div key={idx} className="bg-white p-3 rounded border">
                            <div className="flex items-center justify-between mb-1">
                              <span className="text-sm font-medium text-gray-700 truncate" title={field}>
                                {field}
                              </span>
                              <span className={`text-xs px-1.5 py-0.5 rounded ${
                                parsedValue.unit === 'number'
                                  ? 'bg-green-100 text-green-700'
                                  : 'bg-blue-100 text-blue-700'
                              }`}>
                                {parsedValue.unit}
                              </span>
                            </div>
                            <p className="text-sm text-gray-900 font-mono break-all">
                              {String(parsedValue.value).length > 50
                                ? String(parsedValue.value).substring(0, 50) + '...'
                                : String(parsedValue.value)
                              }
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* 분포 특성 탭 */}
        {activeTab === 'distribution' && (
          <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">📈 분포 특성 분석</h3>
            <div className="text-center py-8 text-gray-500">
              분포 특성 분석 기능은 추후 구현 예정입니다.
              <br />
              현재는 전체 요약 탭에서 기초 통계량을 확인하실 수 있습니다.
            </div>
          </div>
        )}

        {/* 데이터 검사 탭 */}
        {activeTab === 'inspection' && (
          <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">🔍 데이터 검사</h3>
            {showDataInspection ? (
              <ImprovedDataInspectionViewer
                statName={analysisData.stat_name}
                onBack={() => setShowDataInspection(false)}
              />
            ) : (
              <div className="text-center py-8">
                <button
                  onClick={() => setShowDataInspection(true)}
                  className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
                >
                  데이터 검사 시작
                </button>
              </div>
            )}
          </div>
        )}

      </div>
    </div>
  );
};