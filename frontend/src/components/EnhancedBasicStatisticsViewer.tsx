import React, { useRef, useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { AdvancedCardNewsResponse, API_ORIGIN } from '../services/api';
import {
  downloadMarkdown,
  downloadPDF,
  openOriginalUrl,
  generateAIInsightsMarkdown
} from '../utils/downloadUtils';
import { motion } from 'framer-motion';
import {
  ArrowLeftIcon,
  ChartBarIcon,
  DocumentArrowDownIcon,
  ArrowTopRightOnSquareIcon,
  TableCellsIcon,
  SparklesIcon,
  DocumentTextIcon,
  TagIcon,
  ChevronDownIcon,
  ChevronUpIcon
} from '@heroicons/react/24/outline';
import { TableAnalysisViewer } from './TableAnalysisViewer';

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
  const aiInsightsRef = useRef<HTMLDivElement>(null);

  // 마크다운 커스텀 렌더러
  const mdComponents: any = {
    table: ({ children }: any) => (
      <div style={{ overflowX: 'auto', margin: '0.75rem 0' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem', border: '1px solid #94a3b8' }}>
          {children}
        </table>
      </div>
    ),
    thead: ({ children }: any) => (
      <thead style={{ backgroundColor: '#0284c7' }}>{children}</thead>
    ),
    tbody: ({ children }: any) => (
      <tbody>{children}</tbody>
    ),
    tr: ({ children, ...props }: any) => (
      <tr style={{ borderBottom: '1px solid #cbd5e1' }} {...props}>{children}</tr>
    ),
    th: ({ children }: any) => (
      <th style={{
        padding: '8px 12px',
        color: '#ffffff',
        fontWeight: 600,
        textAlign: 'left',
        border: '1px solid #0369a1',
        whiteSpace: 'nowrap',
        backgroundColor: '#0284c7',
      }}>{children}</th>
    ),
    td: ({ children }: any) => (
      <td style={{
        padding: '6px 12px',
        border: '1px solid #cbd5e1',
        color: '#1e293b',
        verticalAlign: 'middle',
      }}>{children}</td>
    ),
    h3: ({ children }: any) => (
      <h3 style={{ fontSize: '0.875rem', fontWeight: 700, color: '#075985', margin: '0.75rem 0 0.25rem', borderBottom: '1px solid #bae6fd', paddingBottom: '2px' }}>{children}</h3>
    ),
    h4: ({ children }: any) => (
      <h4 style={{ fontSize: '0.825rem', fontWeight: 600, color: '#0369a1', margin: '0.5rem 0 0.2rem' }}>{children}</h4>
    ),
    strong: ({ children }: any) => (
      <strong style={{ fontWeight: 700, color: '#1e293b' }}>{children}</strong>
    ),
    p: ({ children }: any) => (
      <p style={{ margin: '0.4rem 0', color: '#374151', lineHeight: 1.7 }}>{children}</p>
    ),
    ul: ({ children }: any) => (
      <ul style={{ margin: '0.3rem 0', paddingLeft: '1.2rem', listStyleType: 'disc' }}>{children}</ul>
    ),
    ol: ({ children }: any) => (
      <ol style={{ margin: '0.3rem 0', paddingLeft: '1.2rem', listStyleType: 'decimal' }}>{children}</ol>
    ),
    li: ({ children }: any) => (
      <li style={{ margin: '0.2rem 0', color: '#374151', lineHeight: 1.6 }}>{children}</li>
    ),
  };
  const [processedStats, setProcessedStats] = useState<ProcessedStatistics | null>(null);
  const [selectedTableName, setSelectedTableName] = useState<string | null>(null);
  const [rawDataByTable, setRawDataByTable] = useState<Record<string, any[]>>({});
  const [loading, setLoading] = useState(true);
  const [isFileDownloadOpen, setIsFileDownloadOpen] = useState(false);
  const [isMetadataOpen, setIsMetadataOpen] = useState(false);

  // 채팅 관련 상태
  const [chatMessages, setChatMessages] = useState<Array<{role: string, content: string}>>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    processRealData();
  }, [analysisData]);

  const processRealData = async () => {
    setLoading(true);
    try {
      // Fetch actual stored data to process
      const response = await fetch(`${API_ORIGIN}/api/data/raw-view`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ stat_name: analysisData.stat_name })
      });

      if (response.ok) {
        const rawData = await response.json();

        // 백엔드에서 데이터 없음 메시지를 보낸 경우 확인
        if (rawData.message && rawData.suggestion) {
          // 사용자에게 알리고 수집 필요함을 표시
          alert(`${rawData.message}\n\n${rawData.suggestion}`);
          setLoading(false);
          return;
        }

        const processed = processStatisticsData(rawData);
        setProcessedStats(processed);

        // Group data by table names with enhanced naming logic
        let dataByTable: Record<string, any[]> = {};

        // Use raw_data_by_table if available (more organized)
        if (rawData.raw_data_by_table) {
          dataByTable = rawData.raw_data_by_table;
        } else if (rawData.raw_data && Array.isArray(rawData.raw_data)) {
          // Fallback: group raw_data by table name
          let tableCounter = 1;

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

  // 채팅 관련 함수
  const handleSendMessage = async () => {
    if (!chatInput.trim() || chatLoading) return;

    const userMessage = chatInput.trim();
    setChatInput('');

    // 사용자 메시지 추가
    const newMessages = [...chatMessages, { role: 'user', content: userMessage }];
    setChatMessages(newMessages);
    setChatLoading(true);

    try {
      const response = await fetch(`${API_ORIGIN}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          stat_name: analysisData.stat_name,
          message: userMessage,
          chat_history: chatMessages
        })
      });

      if (!response.ok) {
        throw new Error('채팅 응답 실패');
      }

      const data = await response.json();

      // AI 응답 추가
      setChatMessages([...newMessages, { role: 'assistant', content: data.response }]);

      // 채팅 끝으로 스크롤
      setTimeout(() => {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      }, 100);

    } catch (error) {
      console.error('채팅 오류:', error);
      setChatMessages([...newMessages, {
        role: 'assistant',
        content: '죄송합니다. 응답을 생성하는 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
      }]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // IBSheet 원본 완전 재구성 함수 (실제 IBSheet 구조 그대로 재현)
  const reconstructIBSheetTable = (rawData: any[]) => {
    if (!rawData || rawData.length === 0) return null;

    const reconstructedTables: Record<string, any> = {};

    rawData.forEach((item: any, tableIndex: number) => {
      if (item?.data?._table_data && item?.data?._table_structure) {
        try {
          const tableData = JSON.parse(item.data._table_data);
          const tableStructure = JSON.parse(item.data._table_structure);
          const tableName = item.table_name || `테이블 ${tableIndex + 1}`;

          // IBSheet 원본 구조 그대로 재현
          const reconstructTable = () => {
            // 최대 행과 열 크기 계산
            const maxRow = Math.max(...tableData.map((row: any) => row.row_index)) + 1;
            const maxCol = tableStructure.cols || 84;

            // 빈 그리드 초기화 (IBSheet 크기)
            const grid: any[][] = [];
            for (let r = 0; r < maxRow; r++) {
              const row = [];
              for (let c = 0; c < maxCol; c++) {
                row.push({
                  value: '',
                  formatted: '',
                  original: '',
                  type: 'text',
                  isEmpty: true,
                  isHeader: false,
                  isMerged: false,
                  colName: `컬럼${c + 1}`,
                  colspan: 1,
                  rowspan: 1
                });
              }
              grid.push(row);
            }

            // 수집된 데이터를 정확한 위치에 배치
            tableData.forEach((rowInfo: any) => {
              const rowIndex = rowInfo.row_index;
              if (rowIndex < maxRow && Array.isArray(rowInfo.cells)) {

                // 이 행의 셀들을 col_index 순서로 정렬
                const sortedCells = rowInfo.cells.sort((a: any, b: any) => a.col_index - b.col_index);

                sortedCells.forEach((cell: any, cellIndex: number) => {
                  const colIndex = cell.col_index;
                  if (colIndex < maxCol) {

                    // colspan 계산 (다음 셀까지의 거리)
                    let colspan = 1;
                    if (cellIndex < sortedCells.length - 1) {
                      const nextColIndex = sortedCells[cellIndex + 1].col_index;
                      colspan = nextColIndex - colIndex;
                    } else {
                      // 마지막 셀: 헤더 정보를 분석해서 적절한 colspan 결정
                      const cellValue = cell.value?.value || '';
                      if (cellValue.includes('승용 승합 화물 특수') || cellValue.includes('관용 자가용 영업용')) {
                        // 복합 헤더의 경우 더 넓은 병합
                        colspan = Math.min(20, maxCol - colIndex);
                      } else {
                        colspan = 1;
                      }
                    }

                    // 셀 데이터 설정
                    const cellData = {
                      value: cell.value?.value || '',
                      formatted: cell.value?.value || '',
                      original: cell.value?.raw || '',
                      type: cell.value?.unit === 'number' ? 'number' : 'text',
                      isEmpty: false,
                      isHeader: cell.is_header || rowInfo.is_header,
                      isMerged: false,
                      colName: cell.col_name || `컬럼${colIndex + 1}`,
                      colspan: colspan,
                      rowspan: 1
                    };

                    // 기본 셀 설정
                    grid[rowIndex][colIndex] = cellData;

                    // 병합된 셀들을 isMerged로 표시
                    for (let c = colIndex + 1; c < colIndex + colspan && c < maxCol; c++) {
                      grid[rowIndex][c] = {
                        ...grid[rowIndex][c],
                        isMerged: true,
                        mergedTo: { row: rowIndex, col: colIndex }
                      };
                    }
                  }
                });
              }
            });

            return grid;
          };

          const grid = reconstructTable();

          reconstructedTables[tableName] = {
            grid: grid,
            structure: {
              rows: grid.length,
              cols: grid[0]?.length || 0
            },
            mergeInfo: {}, // 이미 grid에 병합 정보가 포함됨
            isAdvanced: true,
            source: 'IBSheet_Original'
          };
        } catch (error) {
          console.error('IBSheet 테이블 재구성 오류:', error);
        }
      }
    });

    return reconstructedTables;
  };



  const handleDownloadMD = () => {
    try {
      // AI 인사이트만 마크다운으로 변환
      const markdown = generateAIInsightsMarkdown(analysisData);
      const filename = `AI분석인사이트_${analysisData.stat_name}_${new Date().toISOString().split('T')[0]}`;
      downloadMarkdown(markdown, filename);
    } catch (error) {
      console.error('MD 다운로드 실패:', error);
      alert('마크다운 파일 다운로드에 실패했습니다.');
    }
  };

  const handleDownloadExcel = () => {
    try {
      // 간단한 CSV 형식으로 통계 데이터 생성
      const stats = processedStats?.numeric_stats;
      if (!stats) {
        alert('다운로드할 통계 데이터가 없습니다.');
        return;
      }

      const csvContent = `통계명,${analysisData.stat_name}
분석일시,${new Date(analysisData.analysis_date).toLocaleString('ko-KR')}

기초통계 지표,값
평균값,${stats.mean || 0}
중위수,${stats.median || 0}
최댓값,${stats.max || 0}
최솟값,${stats.min || 0}
총합계,${stats.total || 0}
데이터 개수,${stats.count || 0}`;

      const filename = `기본통계현황분석_${analysisData.stat_name}_${new Date().toISOString().split('T')[0]}.csv`;

      // UTF-8 BOM 추가 (한글 깨짐 방지)
      const BOM = '\uFEFF';
      const csvWithBom = BOM + csvContent;

      const blob = new Blob([csvWithBom], { type: 'text/csv;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('CSV 다운로드 실패:', error);
      alert('CSV 파일 다운로드에 실패했습니다.');
    }
  };

  // 범용적 데이터 패턴 분석 함수
  const analyzeDataPatterns = (tableData: any[]) => {
    if (!tableData || tableData.length === 0) {
      return {
        sample_data: [],
        unique_values: {},
        data_types: {},
        missing_values: 0,
        summary: "데이터 없음",
        hasNumericValues: false,
        numericColumns: [],
        dataClassification: 'general',
        mainCategory: null,
        timePeriod: null,
        hasGeographicData: false,
        hasTimeData: false,
        hasCategoryData: false
      };
    }

    try {
      const allFields: any[] = [];
      const uniqueValues: Record<string, Set<any>> = {};
      const dataTypes: Record<string, string> = {};
      let missingValues = 0;
      const numericColumns: string[] = [];
      let hasGeographicData = false;
      let hasTimeData = false;
      let hasCategoryData = false;

      tableData.forEach((stat: any) => {
        if (stat?.data && typeof stat.data === 'object') {
          Object.entries(stat.data).forEach(([key, value]) => {
            if (typeof value === 'number') {
              allFields.push(value);
              dataTypes[key] = 'number';
              numericColumns.push(key);
            } else if (typeof value === 'string' && value.trim() !== '') {
              allFields.push(value);
              dataTypes[key] = 'string';
              if (!uniqueValues[key]) uniqueValues[key] = new Set();
              uniqueValues[key].add(value);

              // 지역/시간/분류 데이터 감지
              if (value.includes('서울') || value.includes('부산') || value.includes('도') || value.includes('시')) {
                hasGeographicData = true;
              }
              if (value.includes('년') || value.includes('월') || /\d{4}/.test(value)) {
                hasTimeData = true;
              }
              if (value.includes('승용') || value.includes('화물') || value.includes('관용')) {
                hasCategoryData = true;
              }
            } else {
              missingValues++;
            }
          });
        }
      });

      return {
        sample_data: allFields.slice(0, 20),
        unique_values: Object.fromEntries(
          Object.entries(uniqueValues).map(([k, v]) => [k, Array.from(v)])
        ),
        data_types: dataTypes,
        missing_values: missingValues,
        summary: `${allFields.length}개 필드 분석 완료`,
        hasNumericValues: numericColumns.length > 0,
        numericColumns,
        dataClassification: hasTimeData && hasGeographicData ? 'temporal-geographic' :
                          hasGeographicData ? 'geographic' :
                          hasTimeData ? 'temporal' :
                          hasCategoryData ? 'categorical' : 'general',
        mainCategory: analysisData.stat_name?.includes('자동차') ? '도로교통' :
                     analysisData.stat_name?.includes('주택') ? '주택건설' :
                     analysisData.stat_name?.includes('부동산') ? '부동산' : null,
        timePeriod: hasTimeData ? '시계열 데이터 포함' : null,
        hasGeographicData,
        hasTimeData,
        hasCategoryData
      };
    } catch (error) {
      console.warn('데이터 패턴 분석 중 오류:', error);
      return {
        sample_data: [],
        unique_values: {},
        data_types: {},
        missing_values: 0,
        summary: "분석 오류",
        hasNumericValues: false,
        numericColumns: [],
        dataClassification: 'general',
        mainCategory: null,
        timePeriod: null,
        hasGeographicData: false,
        hasTimeData: false,
        hasCategoryData: false
      };
    }
  };

  // 선택된 테이블의 데이터 패턴 분석
  const getSelectedTablePatterns = () => {
    if (!selectedTableName || !rawDataByTable[selectedTableName]) return null;
    return analyzeDataPatterns(rawDataByTable[selectedTableName]);
  };

  // Get statistics for selected table only
  const getSelectedTableStats = () => {
    if (!selectedTableName || !rawDataByTable[selectedTableName]) {
      return processedStats?.numeric_stats;
    }

    const tableData = rawDataByTable[selectedTableName];
    const numericValues: number[] = [];

    tableData.forEach((stat: any) => {
      if (stat?.data?._table_data) {
        try {
          const tableDataStr = typeof stat.data._table_data === 'string'
            ? stat.data._table_data
            : JSON.stringify(stat.data._table_data);

          let parsedData;
          try {
            parsedData = JSON.parse(tableDataStr);
          } catch {
            try {
              parsedData = eval('(' + tableDataStr + ')');
            } catch {
              return;
            }
          }

          if (Array.isArray(parsedData)) {
            parsedData.forEach((row: any) => {
              if (row?.cells && Array.isArray(row.cells)) {
                row.cells.forEach((cell: any) => {
                  if (cell?.value?.value && typeof cell.value.value === 'number') {
                    numericValues.push(cell.value.value);
                  }
                });
              }
            });
          }
        } catch (error) {
          console.warn('_table_data 파싱 오류:', error);
        }
      }

      if (stat?.data && typeof stat.data === 'object') {
        Object.entries(stat.data).forEach(([key, value]) => {
          if (typeof value === 'number' && !isNaN(value)) {
            numericValues.push(value);
          }
        });
      }
    });

    if (numericValues.length === 0) {
      return processedStats?.numeric_stats || {
        total: 0,
        mean: 0,
        median: 0,
        std: 0,
        min: 0,
        max: 0,
        count: 0,
        distribution: []
      };
    }

    const sorted = numericValues.sort((a, b) => a - b);
    const count = numericValues.length;
    const total = numericValues.reduce((a, b) => a + b, 0);
    const mean = total / count;
    const median = count % 2 === 0
      ? (sorted[count/2 - 1] + sorted[count/2]) / 2
      : sorted[Math.floor(count/2)];
    const variance = numericValues.reduce((acc, val) => acc + Math.pow(val - mean, 2), 0) / count;
    const std = Math.sqrt(variance);

    return {
      total,
      mean,
      median,
      std,
      min: Math.min(...numericValues),
      max: Math.max(...numericValues),
      count,
      distribution: sorted
    };
  };

  const handleDownloadPDF = async () => {
    // AI 인사이트 영역만 PDF로 다운로드
    if (aiInsightsRef.current) {
      try {
        const filename = `AI분석인사이트_${analysisData.stat_name}_${new Date().toISOString().split('T')[0]}`;
        await downloadPDF(aiInsightsRef.current, filename);
      } catch (error) {
        console.error('PDF 다운로드 실패:', error);
        alert('PDF 파일 다운로드에 실패했습니다.');
      }
    } else {
      alert('AI 인사이트 영역을 찾을 수 없습니다.');
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



  // Filter data by selected table
  const getFilteredData = () => {
    if (!selectedTableName || !processedStats) return processedStats?.sample_data || [];

    return processedStats.sample_data.filter(item =>
      item.source_table === selectedTableName
    );
  };


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
      <motion.div 
        className="bg-white rounded-lg shadow-lg border border-gray-200 p-6 mb-8"
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900 mb-2 flex items-center gap-3">
              <ChartBarIcon className="w-7 h-7 text-primary-600" />
              통계현황결과
            </h1>
            <p className="text-gray-600">실제 수집 데이터 기반 결과</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={onBack}
              className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-50 transition-colors flex items-center gap-2 text-sm font-medium"
            >
              <ArrowLeftIcon className="w-4 h-4" />
              뒤로 가기
            </button>
            <button
              onClick={handleDownloadMD}
              className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700 transition-colors flex items-center gap-2 text-sm font-medium"
              title="AI 인사이트를 마크다운 파일로 다운로드"
            >
              <DocumentArrowDownIcon className="w-4 h-4" />
              AI 인사이트 MD
            </button>
            <button
              onClick={handleDownloadPDF}
              className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700 transition-colors flex items-center gap-2 text-sm font-medium"
              title="AI 인사이트를 PDF 파일로 다운로드"
            >
              <DocumentArrowDownIcon className="w-4 h-4" />
              AI 인사이트 PDF
            </button>
            {analysisData.metadata?.url && (
              <button
                onClick={handleViewOriginal}
                className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-50 transition-colors flex items-center gap-2 text-sm font-medium"
              >
                <ArrowTopRightOnSquareIcon className="w-4 h-4" />
                원본
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
        <div className="border-t border-gray-200 mt-8"></div>

        {/* 원본 파일 다운로드 - 아코디언 */}
        <div>
          <button
            onClick={() => setIsFileDownloadOpen(!isFileDownloadOpen)}
            className="w-full flex items-center justify-between hover:bg-gray-50 transition-colors duration-200 rounded-lg p-4"
          >
            <h4 className="text-xl font-semibold text-gray-900 flex items-center gap-3">
              <DocumentArrowDownIcon className="w-6 h-6 text-primary-600" />
              원본 파일 다운로드
            </h4>
            {isFileDownloadOpen ? (
              <ChevronUpIcon className="w-6 h-6 text-gray-600" />
            ) : (
              <ChevronDownIcon className="w-6 h-6 text-gray-600" />
            )}
          </button>
          {isFileDownloadOpen && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
              className="mt-4 pb-4"
            >
              <TableAnalysisViewer
                statName={analysisData.stat_name}
                onBack={() => {}}
              />
            </motion.div>
          )}
        </div>

        <div className="border-t border-gray-200"></div>

        {/* 메타데이터 정보 - 아코디언 */}
        <div>
          <button
            onClick={() => setIsMetadataOpen(!isMetadataOpen)}
            className="w-full flex items-center justify-between hover:bg-gray-50 transition-colors duration-200 rounded-lg p-4"
          >
            <h4 className="text-xl font-semibold text-gray-900 flex items-center gap-3">
              <DocumentTextIcon className="w-6 h-6 text-primary-600" />
              메타데이터 정보
            </h4>
            {isMetadataOpen ? (
              <ChevronUpIcon className="w-6 h-6 text-gray-600" />
            ) : (
              <ChevronDownIcon className="w-6 h-6 text-gray-600" />
            )}
          </button>
          {isMetadataOpen && (analysisData.metadata?.statistical_info || analysisData.metadata?.major_items ||
            analysisData.metadata?.meaning_analysis || analysisData.metadata?.terminology) && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.3 }}
              className="mt-4"
            >
              <div>
                {/* 상세 메타정보 */}
                <div className="grid grid-cols-1 lg:grid-cols gap-6">

                  {/* 통계정보 상세 - 콤팩트하게 */}
                  {analysisData.metadata?.statistical_info && Object.keys(analysisData.metadata.statistical_info).length > 0 && (
                    <div className="bg-primary-50 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <ChartBarIcon className="w-5 h-5 text-primary-600" />
                        <h5 className="font-semibold text-primary-700">통계정보 상세</h5>
                      </div>
                      <div className="bg-white rounded-md p-3 space-y-2">
                        {Object.entries(analysisData.metadata.statistical_info).map(([key, value], index) => (
                          <div key={index} className="flex items-start gap-2">
                            <span className="text-sm font-medium text-primary-700 min-w-[120px] flex-shrink-0">{key}:</span>
                            <span className="text-sm text-gray-900 flex-1">{value || '-'}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 주요항목 - 콤팩트하게 */}
                  {analysisData.metadata?.major_items && Object.keys(analysisData.metadata.major_items).length > 0 && (
                    <div className="bg-success-50 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <SparklesIcon className="w-5 h-5 text-success-600" />
                        <h5 className="font-semibold text-success-700">주요항목</h5>
                      </div>
                      <div className="bg-white rounded-md p-3 space-y-2">
                        {Object.entries(analysisData.metadata.major_items).map(([key, value], index) => (
                          <div key={index} className="flex items-start gap-2">
                            <span className="text-sm font-medium text-success-700 min-w-[120px] flex-shrink-0">{key}:</span>
                            <span className="text-sm text-gray-900 flex-1">{value || '-'}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 의미분석 - 콤팩트하게 */}
                  {analysisData.metadata?.meaning_analysis && Object.keys(analysisData.metadata.meaning_analysis).length > 0 && (
                    <div className="bg-info-50 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <SparklesIcon className="w-5 h-5 text-info-600" />
                        <h5 className="font-semibold text-info-700">의미분석</h5>
                      </div>
                      <div className="bg-white rounded-md p-3 space-y-2">
                        {Object.entries(analysisData.metadata.meaning_analysis).map(([key, value], index) => (
                          <div key={index} className="flex items-start gap-2">
                            <span className="text-sm font-medium text-info-700 min-w-[120px] flex-shrink-0">{key}:</span>
                            <span className="text-sm text-gray-900 flex-1">{value || '-'}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 용어정리 - 콤팩트하게 */}
                  {analysisData.metadata?.terminology && Object.keys(analysisData.metadata.terminology).length > 0 && (
                    <div className="bg-warning-50 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <DocumentTextIcon className="w-5 h-5 text-warning-600" />
                        <h5 className="font-semibold text-warning-700">용어정리</h5>
                      </div>
                      <div className="bg-white rounded-md p-3 space-y-2">
                        {Object.entries(analysisData.metadata.terminology).map(([key, value], index) => (
                          <div key={index} className="flex items-start gap-2">
                            <span className="text-sm font-medium text-warning-700 min-w-[120px] flex-shrink-0">{key}:</span>
                            <span className="text-sm text-gray-900 flex-1 whitespace-pre-line">{value || '-'}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* 관련용어 */}
                  {analysisData.metadata?.related_terms && Object.keys(analysisData.metadata.related_terms).length > 0 && (
                    <div className="bg-gray-50 rounded-lg p-6">
                      <div className="flex items-start gap-3 mb-4">
                        <div className="w-10 h-10 bg-gray-600 rounded-lg flex items-center justify-center flex-shrink-0">
                          <TagIcon className="w-5 h-5 text-white" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <h5 className="font-semibold text-gray-900 text-left">관련용어</h5>
                        </div>
                      </div>
                      <div className="space-y-3">
                        {Object.entries(analysisData.metadata.related_terms).map(([key, value], index) => (
                          <div key={index} className="bg-white rounded-lg p-3">
                            <div className="text-left">
                              <div className="text-sm font-medium text-gray-700 mb-1">{key}</div>
                              <div className="text-sm text-gray-900 whitespace-pre-line">{value || '-'}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </motion.div>

      {/* 분석 내용 - PDF 다운로드 대상 */}
      <div ref={contentRef}>
            {/* 통계표별 상세 분석 - 전체를 하나의 카드로 묶음 */}
            <motion.div
              className="bg-white rounded-lg shadow-lg border border-gray-200 p-8 mb-8"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, delay: 0.2 }}
            >
              {/* LLM 분석 결과 영역 */}
              <div>
                <h4 className="text-xl font-semibold text-gray-900 mb-6 flex items-center gap-3">
                  <SparklesIcon className="w-6 h-6 text-primary-600" />
                  AI 분석 결과
                </h4>

                {/* AI 채팅 (AI 인사이트가 있을 때만 표시) */}
                {(analysisData.metadata?.ai_insights?.insights_count ?? 0) > 0 && (
                  <div className="mb-8">
                    <button
                      onClick={() => setIsChatOpen(!isChatOpen)}
                      className="w-full flex items-center justify-between hover:bg-green-50 transition-colors duration-200 rounded-lg p-4 border border-emerald-200"
                    >
                      <h4 className="text-xl font-semibold text-gray-900 flex items-center gap-3">
                        <svg className="w-6 h-6 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                        </svg>
                        AI 채팅 (데이터 기반 질의응답)
                      </h4>
                      {isChatOpen ? (
                        <ChevronUpIcon className="w-6 h-6 text-gray-600" />
                      ) : (
                        <ChevronDownIcon className="w-6 h-6 text-gray-600" />
                      )}
                    </button>

                    {isChatOpen && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.3 }}
                        className="mt-4 bg-emerald-50/40 rounded-lg border-2 border-emerald-300 shadow-inner"
                      >
                        {/* 채팅 메시지 영역 */}
                        <div className="h-96 overflow-y-auto p-6 space-y-4">
                          {chatMessages.length === 0 ? (
                            <div className="text-center text-gray-500 mt-20">
                              <svg className="w-16 h-16 mx-auto mb-4 text-emerald-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                              </svg>
                              <p className="text-lg font-medium mb-2">통계 데이터에 대해 질문해보세요</p>
                            </div>
                          ) : (
                            chatMessages.map((msg, idx) => (
                              <motion.div
                                key={idx}
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                              >
                                <div className={`max-w-[80%] rounded-2xl px-4 py-3 shadow-md ${
                                  msg.role === 'user'
                                    ? 'bg-gradient-to-br from-emerald-500 via-emerald-600 to-teal-600 text-white border border-emerald-400/30'
                                    : 'bg-white text-gray-800 border border-gray-200'
                                }`}>
                                  <div className="leading-relaxed insight-markdown">
                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>{msg.content}</ReactMarkdown>
                  </div>
                                </div>
                              </motion.div>
                            ))
                          )}
                          {chatLoading && (
                            <div className="flex justify-start">
                              <div className="bg-gray-100 rounded-2xl px-4 py-3">
                                <div className="flex gap-2">
                                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.4s'}}></div>
                                </div>
                              </div>
                            </div>
                          )}
                          <div ref={chatEndRef} />
                        </div>

                        {/* 채팅 입력 영역 */}
                        <div className="border-t border-gray-200 bg-white/50 p-4">
                          <div className="flex gap-2">
                            <input
                              type="text"
                              value={chatInput}
                              onChange={(e) => setChatInput(e.target.value)}
                              onKeyPress={handleKeyPress}
                              placeholder="통계 데이터에 대해 질문하세요... (예: 2025년 서울 미분양 현황은?)"
                              className="flex-1 px-4 py-3 border border-emerald-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent bg-white"
                              disabled={chatLoading}
                            />
                            <button
                              onClick={handleSendMessage}
                              disabled={chatLoading || !chatInput.trim()}
                              className="px-6 py-3 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium text-sm"
                            >
                              {chatLoading ? '전송 중...' : '전송'}
                            </button>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </div>
                )}

                {/* AI 분석 결과 (10개 카테고리) - 콤팩트하게 */}
                <div ref={aiInsightsRef}>
                  {(analysisData.metadata?.ai_insights?.insights_count ?? 0) > 0 ? (
                    <div className="bg-blue-50 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <SparklesIcon className="w-5 h-5 text-primary-600" />
                        <h5 className="font-semibold text-primary-700">
                          AI 분석 인사이트 ({analysisData.metadata?.ai_insights?.insights_count}개)
                        </h5>
                      </div>

                      {/* 10개 카테고리 인사이트 */}
                      <div className="bg-white rounded-md p-4 space-y-4">
                        {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((num) => {
                          const insightKey = `insight_${num}`;
                          const insight = analysisData.metadata?.ai_insights?.[insightKey];

                          if (!insight) return null;

                          return (
                            <div
                              key={num}
                              className="border-l-4 border-primary-400 bg-blue-50/50 rounded-r-lg p-4 hover:bg-blue-50 transition-colors duration-200"
                            >
                              <div className="flex items-start gap-4">
                                <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-600 text-white rounded-lg flex items-center justify-center flex-shrink-0 font-bold">
                                  {num}
                                </div>
                                <div className="flex-1 min-w-0">
                                  <h6 className="font-semibold text-primary-800 text-base mb-3">
                                    {insight.title || insight.category}
                                  </h6>
                                  <div className="text-sm text-gray-800 leading-relaxed insight-markdown">
                                    <ReactMarkdown remarkPlugins={[remarkGfm]} components={mdComponents}>{insight.content}</ReactMarkdown>
                                  </div>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-secondary-50 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-3">
                        <SparklesIcon className="w-5 h-5 text-secondary-600" />
                        <h5 className="font-semibold text-secondary-700">AI 인사이트 대기 중</h5>
                      </div>
                      <div className="bg-white rounded-md p-3">
                        <p className="text-sm text-gray-700">
                          이 통계에 대한 AI 분석 인사이트가 아직 생성되지 않았습니다.
                          '분석하기' 버튼을 눌러 새로 분석하면 AI 인사이트가 자동 생성됩니다.
                        </p>
                      </div>
                    </div>
                  )}
                </div>

                {/* 임시로 남겨둔 통계 카드 - 삭제 예정 */}
                <div className="hidden grid-cols-1 md:grid-cols-3 gap-6">
                  <motion.div 
                    className="bg-blue-50 rounded-lg p-6 text-center"
                    whileHover={{ scale: 1.05 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="w-12 h-12 bg-primary-600 rounded-lg flex items-center justify-center mx-auto mb-3">
                      <DocumentTextIcon className="w-6 h-6 text-white" />
                    </div>
                    <div className="text-3xl font-bold text-blue-700 mb-1">
                      {(() => {
                        // 선택된 테이블의 필드 수 계산
                        if (!selectedTableName || !rawDataByTable[selectedTableName]) {
                          return 0;
                        }
                        const tableData = rawDataByTable[selectedTableName];
                        let totalFields = 0;
                        tableData.forEach(stat => {
                          totalFields += Object.keys(stat.data || {}).length;
                        });
                        return totalFields;
                      })()}
                    </div>
                    <div className="text-sm font-medium text-blue-600">총 데이터 필드</div>
                  </motion.div>
                  <motion.div 
                    className="bg-purple-50 rounded-lg p-6 text-center"
                    whileHover={{ scale: 1.05 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="w-12 h-12 bg-purple-600 rounded-lg flex items-center justify-center mx-auto mb-3">
                      <ChartBarIcon className="w-6 h-6 text-white" />
                    </div>
                    <div className="text-3xl font-bold text-purple-700 mb-1">
                      {(() => {
                        // 선택된 테이블의 숫자 데이터 수 계산
                        if (!selectedTableName || !rawDataByTable[selectedTableName]) {
                          return 0;
                        }
                        const tableData = rawDataByTable[selectedTableName];
                        let numericFields = 0;
                        tableData.forEach(stat => {
                          Object.entries(stat.data || {}).forEach(([key, value]) => {
                            try {
                              const parsedValue = typeof value === 'string' && value.includes("'value'")
                                ? JSON.parse(value.replace(/'/g, '"'))
                                : { value, unit: 'text', raw: value };
                              if (parsedValue.unit === 'number') {
                                numericFields++;
                              }
                            } catch (error) {
                              // Skip parsing errors
                            }
                          });
                        });
                        return numericFields;
                      })()}
                    </div>
                    <div className="text-sm font-medium text-purple-600">숫자 데이터</div>
                  </motion.div>
                  <motion.div 
                    className="bg-amber-50 rounded-lg p-6 text-center"
                    whileHover={{ scale: 1.05 }}
                    transition={{ duration: 0.2 }}
                  >
                    <div className="w-12 h-12 bg-amber-600 rounded-lg flex items-center justify-center mx-auto mb-3">
                      <DocumentTextIcon className="w-6 h-6 text-white" />
                    </div>
                    <div className="text-3xl font-bold text-amber-700 mb-1">
                      {(() => {
                        // 선택된 테이블의 텍스트 데이터 수 계산
                        if (!selectedTableName || !rawDataByTable[selectedTableName]) {
                          return 0;
                        }
                        const tableData = rawDataByTable[selectedTableName];
                        let textFields = 0;
                        tableData.forEach(stat => {
                          Object.entries(stat.data || {}).forEach(([key, value]) => {
                            try {
                              const parsedValue = typeof value === 'string' && value.includes("'value'")
                                ? JSON.parse(value.replace(/'/g, '"'))
                                : { value, unit: 'text', raw: value };
                              if (parsedValue.unit !== 'number') {
                                textFields++;
                              }
                            } catch (error) {
                              textFields++;
                            }
                          });
                        });
                        return textFields;
                      })()}
                    </div>
                    <div className="text-sm font-medium text-amber-600">텍스트 데이터</div>
                  </motion.div>
                </div>
                </div>

                {/* 이전 데이터 특성 분석 섹션 삭제됨 - LLM 분석으로 대체 */}

                {/* 구분선 - 삭제 예정 */}
                <div className="hidden border-t border-gray-200 my-8"></div>

                {/* 데이터 특성 분석 - 삭제됨 */}
                <div className="hidden mb-8">
                  <h4 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-3">
                    <ChartBarIcon className="w-6 h-6 text-primary-600" />
                    데이터 특성 분석
                    {selectedTableName && (
                      <span className="text-lg text-blue-600 ml-2 bg-blue-100 px-3 py-1 rounded-lg">
                        {selectedTableName}
                      </span>
                    )}
                  </h4>

                  {(() => {
                    const patterns = analyzeDataPatterns(processedStats?.sample_data || []);
                    if (!patterns) return <div className="text-gray-500">데이터 패턴을 분석할 수 없습니다.</div>;

                    // 비어있는 테이블 체크
                    const isEmpty = !patterns ||
                      (!patterns.hasNumericValues &&
                      patterns.numericColumns.length === 0 &&
                      getSelectedTableStats()?.count === 0);

                    if (isEmpty) {
                      return (
                        <motion.div 
                          className="bg-amber-50 rounded-lg p-8 border border-amber-200"
                          initial={{ opacity: 0, scale: 0.95 }}
                          animate={{ opacity: 1, scale: 1 }}
                          transition={{ duration: 0.3 }}
                        >
                          <div className="flex items-center gap-4 mb-6">
                            <div className="w-12 h-12 bg-amber-600 rounded-lg flex items-center justify-center">
                              <SparklesIcon className="w-6 h-6 text-white" />
                            </div>
                            <h4 className="text-xl font-semibold text-amber-800">데이터 없음</h4>
                          </div>
                          <p className="text-amber-700 mb-6 text-lg">
                            선택된 통계표 <span className="font-bold">"{selectedTableName || '알 수 없음'}"</span>에는 분석 가능한 데이터가 없습니다.
                          </p>
                          <div className="bg-amber-100 rounded-lg p-6">
                            <div className="flex items-start gap-3">
                              <div className="w-6 h-6 bg-amber-600 rounded-full flex items-center justify-center flex-shrink-0 mt-1">
                                <span className="text-white text-xs font-bold">!</span>
                              </div>
                              <div className="text-sm text-amber-800 leading-relaxed">
                                <p className="mb-2"><strong>가능한 원인:</strong></p>
                                <ul className="space-y-1 ml-4">
                                  <li>• 데이터가 수집되지 않았거나</li>
                                  <li>• 해당 기간에 대한 정보가 없거나</li>
                                  <li>• 조회 조건에 맞는 결과가 없을 수 있습니다.</li>
                                </ul>
                              </div>
                            </div>
                          </div>
                        </motion.div>
                      );
                    }

                    return (
                      <div className="space-y-6">
                        {/* 데이터 분류 및 특성 */}
                        <motion.div 
                          className="bg-blue-50 rounded-lg p-6 shadow-lg"
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.3, delay: 0.1 }}
                        >
                          <div className="flex items-center gap-3 mb-4">
                            <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
                              <ChartBarIcon className="w-5 h-5 text-white" />
                            </div>
                            <h4 className="font-semibold text-blue-900">데이터 분류 및 특성</h4>
                          </div>
                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="bg-white rounded-lg p-4 shadow-sm">
                              <div className="flex items-center gap-2 mb-2">
                                <div className="w-6 h-6 bg-primary-600 rounded-lg flex items-center justify-center">
                                  <ChartBarIcon className="w-3 h-3 text-white" />
                                </div>
                                <span className="text-blue-800 font-medium text-sm">데이터 유형</span>
                              </div>
                              <span className="bg-primary-600 text-white px-3 py-1 rounded-lg text-sm font-medium">
                                {patterns.dataClassification === 'temporal-geographic' && '시계열-지역별'}
                                {patterns.dataClassification === 'geographic' && '지역별 통계'}
                                {patterns.dataClassification === 'temporal' && '시계열 통계'}
                                {patterns.dataClassification === 'categorical' && '분류별 통계'}
                                {patterns.dataClassification === 'general' && '일반 통계'}
                              </span>
                            </div>

                            {patterns.mainCategory && (
                              <div className="bg-white rounded-lg p-4 shadow-sm">
                                <div className="flex items-center gap-2 mb-2">
                                  <div className="w-6 h-6 bg-green-600 rounded-lg flex items-center justify-center">
                                    <TagIcon className="w-3 h-3 text-white" />
                                  </div>
                                  <span className="text-green-800 font-medium text-sm">분야</span>
                                </div>
                                <span className="bg-green-600 text-white px-3 py-1 rounded-lg text-sm font-medium">
                                  {patterns.mainCategory}
                                </span>
                              </div>
                            )}

                            {patterns.timePeriod && (
                              <div className="bg-white rounded-lg p-4 shadow-sm">
                                <div className="flex items-center gap-2 mb-2">
                                  <div className="w-6 h-6 bg-purple-600 rounded-lg flex items-center justify-center">
                                    <SparklesIcon className="w-3 h-3 text-white" />
                                  </div>
                                  <span className="text-purple-800 font-medium text-sm">기간</span>
                                </div>
                                <span className="bg-purple-600 text-white px-3 py-1 rounded-lg text-sm font-medium">
                                  {patterns.timePeriod}
                                </span>
                              </div>
                            )}
                          </div>
                        </motion.div>

                        {/* 범용적 기초통계 지표 */}
                        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                          <div className="bg-red-50 rounded-lg p-4 text-center">
                            <div className="text-2xl font-bold text-red-700">
                              {formatNumber(getSelectedTableStats()?.mean || 0)}
                            </div>
                            <div className="text-sm text-red-600 font-medium">평균값</div>
                            <div className="text-xs text-red-500 mt-1">
                              {patterns.mainCategory === '주택건설' && '평균 준공규모'}
                              {patterns.mainCategory === '부동산' && '평균 거래가격'}
                              {patterns.mainCategory === '도로교통' && '평균 도로연장'}
                              {!patterns.mainCategory && '평균값'}
                            </div>
                          </div>

                          <div className="bg-orange-50 rounded-lg p-4 text-center">
                            <div className="text-2xl font-bold text-orange-700">
                              {formatNumber(getSelectedTableStats()?.median || 0)}
                            </div>
                            <div className="text-sm text-orange-600 font-medium">중위수</div>
                            <div className="text-xs text-orange-500 mt-1">중앙값</div>
                          </div>

                          <div className="bg-yellow-50 rounded-lg p-4 text-center">
                            <div className="text-2xl font-bold text-yellow-700">
                              {formatNumber(getSelectedTableStats()?.max || 0)}
                            </div>
                            <div className="text-sm text-yellow-600 font-medium">최댓값</div>
                            <div className="text-xs text-yellow-500 mt-1">
                              {patterns.hasGeographicData && '지역별 최고'}
                              {!patterns.hasGeographicData && '최댓값'}
                            </div>
                          </div>

                          <div className="bg-green-50 rounded-lg p-4 text-center">
                            <div className="text-2xl font-bold text-green-700">
                              {formatNumber(getSelectedTableStats()?.min || 0)}
                            </div>
                            <div className="text-sm text-green-600 font-medium">최솟값</div>
                            <div className="text-xs text-green-500 mt-1">
                              {patterns.hasGeographicData && '지역별 최저'}
                              {!patterns.hasGeographicData && '최솟값'}
                            </div>
                          </div>

                          <div className="bg-blue-50 rounded-lg p-4 text-center">
                            <div className="text-2xl font-bold text-blue-700">
                              {formatNumber(getSelectedTableStats()?.total || 0)}
                            </div>
                            <div className="text-sm text-blue-600 font-medium">총합계</div>
                            <div className="text-xs text-blue-500 mt-1">
                              {patterns.mainCategory === '주택건설' && '전체 준공량'}
                              {patterns.mainCategory === '부동산' && '총 거래규모'}
                              {patterns.mainCategory === '도로교통' && '총 도로연장'}
                              {!patterns.mainCategory && '총합계'}
                            </div>
                          </div>

                          <div className="bg-indigo-50 rounded-lg p-4 text-center">
                            <div className="text-2xl font-bold text-indigo-700">
                              {getSelectedTableStats()?.count || 0}
                            </div>
                            <div className="text-sm text-indigo-600 font-medium">데이터 수</div>
                            <div className="text-xs text-indigo-500 mt-1">
                              {patterns.hasTimeData && '시점 수'}
                              {patterns.hasGeographicData && '지역 수'}
                              {!patterns.hasTimeData && !patterns.hasGeographicData && '항목 수'}
                            </div>
                          </div>
                        </div>
                      </div>
                    );
                  })()}
              </div>

              {/* 원본 테이블 재구성 섹션 삭제됨 - LLM 분석으로 대체 */}
              <div className="hidden border-t border-gray-200 my-8"></div>

              {/* 원본 테이블 재구성 - 삭제됨 */}
              <div className="hidden mb-8">
                <h4 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-3">
                  <TableCellsIcon className="w-6 h-6 text-primary-600" />
                  원본 테이블 재구성
            {selectedTableName && (
              <span className="text-lg text-blue-600 ml-2 bg-blue-100 px-3 py-1 rounded-lg">
                {selectedTableName}
              </span>
            )}
          </h4>

          {(() => {
            const patterns = analyzeDataPatterns(processedStats?.sample_data || []);
            return (
              <div className="bg-green-50 rounded-lg p-4 mb-4">
                <div className="flex items-center gap-4 flex-wrap text-sm">
                  <span className="text-green-800 font-medium">🎯 데이터 특성:</span>
                  <div className="flex flex-wrap gap-2">
                    {patterns?.hasTimeData && (
                      <span className="bg-green-100 text-green-800 px-2 py-1 rounded-full text-xs">시계열</span>
                    )}
                    {patterns?.hasGeographicData && (
                      <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs">지역별</span>
                    )}
                    {patterns?.hasCategoryData && (
                      <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded-full text-xs">분류별</span>
                    )}
                    {patterns?.hasNumericValues && (
                      <span className="bg-orange-100 text-orange-800 px-2 py-1 rounded-full text-xs">숫자데이터</span>
                    )}
                  </div>
                </div>
              </div>
            );
          })()}

          {(() => {
            const selectedData = selectedTableName && rawDataByTable[selectedTableName]
              ? rawDataByTable[selectedTableName]
              : Object.values(rawDataByTable).flat();

            const reconstructedTables = reconstructIBSheetTable(selectedData);

            if (!reconstructedTables || Object.keys(reconstructedTables).length === 0) {
              return (
                <motion.div 
                  className="bg-gray-50 rounded-lg p-8 text-center"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  <div className="flex flex-col items-center gap-4 mb-6">
                    <div className="w-16 h-16 bg-gray-600 rounded-lg flex items-center justify-center">
                      <TableCellsIcon className="w-8 h-8 text-white" />
                    </div>
                    <div>
                      <h4 className="text-lg font-semibold text-gray-700 mb-2">테이블 재구성 불가</h4>
                      <p className="text-gray-600 mb-2">선택된 통계표에서 테이블 형태로 재구성할 수 있는 데이터가 없습니다.</p>
                      <p className="text-sm text-gray-500">IBSheet 데이터가 포함된 통계표를 선택해 주세요.</p>
                    </div>
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
                </motion.div>
              );
            }

            return (
              <div className="space-y-6">
                {Object.entries(reconstructedTables).map(([tableName, tableInfo], tableIndex) => {
                  // 새로운 구조 (고급 기능 포함) vs 기존 구조 호환성
                  const isAdvancedTable = tableInfo.hasAdvancedFeatures;
                  const tableData = isAdvancedTable ? tableInfo.grid : tableInfo;
                  const structure = isAdvancedTable ? tableInfo.structure : null;
                  const mergeInfo = isAdvancedTable ? tableInfo.mergeInfo : {};

                  const rows = structure ? structure.rows : (Array.isArray(tableData) ? tableData.length : 0);
                  const cols = structure ? structure.cols : (Array.isArray(tableData) && tableData[0] ? tableData[0].length : 0);

                  return (
                    <div key={tableIndex} className="border rounded-lg overflow-hidden shadow-sm">
                      <div className="bg-blue-50 px-4 py-3 border-b">
                        <h4 className="font-semibold text-gray-900 flex items-center">
                          <span className="bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm mr-2">
                            {tableIndex + 1}
                          </span>
                          {tableName}
                          {isAdvancedTable && (
                            <span className="ml-2 bg-green-100 text-green-700 px-2 py-1 rounded-full text-xs font-medium">
                              IBSheet 완전 재구성
                            </span>
                          )}
                        </h4>
                        <p className="text-sm text-gray-600 mt-1">
                          {rows}행 × {cols}열 구조
                          {isAdvancedTable && (
                            <span className="ml-2 text-green-600">
                              | {Object.keys(mergeInfo).length}개 병합 셀
                            </span>
                          )}
                          <span className="ml-2">| 수집 시점: {new Date().toLocaleString('ko-KR')}</span>
                        </p>
                    </div>

                    <div className="overflow-x-auto">
                      <table className="w-full text-sm border-collapse">
                        <tbody>
                          {Array.isArray(tableData) && tableData.map((row, rowIndex) => (
                            <tr
                              key={rowIndex}
                              className={`border-b border-gray-200 ${
                                rowIndex === 0 || (Array.isArray(row) && row.some(cell => cell?.isHeader))
                                  ? 'bg-gray-50 font-semibold'
                                  : rowIndex % 2 === 0
                                    ? 'bg-white hover:bg-blue-25'
                                    : 'bg-gray-25 hover:bg-blue-50'
                              }`}
                            >
                              {Array.isArray(row) && row.map((cell, colIndex) => {
                                // 병합된 셀은 렌더링하지 않음
                                if (cell?.isMerged) return null;

                                const cellKey = `${rowIndex}_${colIndex}`;
                                const colspan = isAdvancedTable && mergeInfo[cellKey] ? mergeInfo[cellKey].colspan : (cell?.colspan || 1);
                                const rowspan = isAdvancedTable && mergeInfo[cellKey] ? mergeInfo[cellKey].rowspan : (cell?.rowspan || 1);

                                return (
                                  <td
                                    key={colIndex}
                                    colSpan={colspan}
                                    rowSpan={rowspan}
                                    className={`px-3 py-2 border border-gray-300 ${
                                      cell?.type === 'number'
                                        ? 'text-right font-mono'
                                        : 'text-left'
                                    } ${
                                      cell?.isEmpty ? 'bg-gray-100' : ''
                                    } ${
                                      cell?.isHeader || rowIndex === 0
                                        ? 'font-semibold bg-gradient-to-br from-blue-50 to-indigo-50 text-gray-800 border-blue-200'
                                        : 'border-gray-300'
                                    } ${
                                      colspan > 1 || rowspan > 1
                                        ? 'bg-gradient-to-br from-yellow-50 to-orange-50 border-orange-200'
                                        : ''
                                    }`}
                                    title={
                                      cell?.colName
                                        ? `컬럼: ${cell.colName}${colspan > 1 ? ` (${colspan}열 병합)` : ''}${rowspan > 1 ? ` (${rowspan}행 병합)` : ''}`
                                        : (colspan > 1 || rowspan > 1) ? `병합 셀: ${colspan}×${rowspan}` : ''
                                    }
                                  >
                                    {cell?.isEmpty ? (
                                      <span className="text-gray-400">-</span>
                                    ) : (
                                      <div className="min-w-0">
                                        <div className={`${
                                          cell?.type === 'number'
                                            ? 'text-blue-600 font-medium'
                                            : cell?.isHeader || rowIndex === 0
                                              ? 'text-gray-800 font-semibold'
                                              : 'text-gray-900'
                                        } ${colspan > 1 ? 'text-center' : ''}`}>
                                          {cell?.formatted || cell?.value || '-'}
                                        </div>
                                        {cell?.type === 'number' && cell?.original !== cell?.formatted && (
                                          <div className="text-xs text-gray-500 mt-0.5 truncate" title={cell.original}>
                                            원본: {cell.original}
                                          </div>
                                        )}
                                        {isAdvancedTable && (colspan > 1 || rowspan > 1) && (
                                          <div className="text-xs text-orange-600 mt-0.5">
                                            병합: {colspan}×{rowspan}
                                          </div>
                                        )}
                                        {cell?.colName && cell.colName !== '' && (
                                          <div className="text-xs text-gray-400 mt-0.5 truncate" title={`컬럼: ${cell.colName}`}>
                                            {cell.colName}
                                          </div>
                                        )}
                                    </div>
                                  )}
                                </td>
                                );
                              })}
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
                );
              })}

                <motion.div 
                  className="bg-green-50 rounded-lg p-6 border border-green-200 shadow-lg"
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.3 }}
                >
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 bg-green-600 rounded-lg flex items-center justify-center flex-shrink-0">
                      <SparklesIcon className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <h4 className="font-semibold text-green-900 mb-3 flex items-center gap-2">
                        테이블 재구성 완료
                      </h4>
                      <div className="text-sm text-green-800 space-y-2">
                        <div className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 bg-green-600 rounded-full"></div>
                          <span>총 <strong>{Object.keys(reconstructedTables).length}개</strong>의 테이블이 원본 형태로 재구성되었습니다.</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 bg-green-600 rounded-full"></div>
                          <span>국토교통부 통계 특성을 반영하여 <strong>6-10열 구조</strong>로 최적화되었습니다.</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 bg-green-600 rounded-full"></div>
                          <span>숫자 데이터는 <strong>천 단위 구분 기호</strong>가 적용되어 가독성이 향상되었습니다.</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <div className="w-1.5 h-1.5 bg-green-600 rounded-full"></div>
                          <span><strong>첫 번째 행</strong>은 헤더로 인식하여 강조 표시됩니다.</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </motion.div>
              </div>
            );
          })()}
              </div>

              {/* 데이터 분포 특성 섹션 삭제됨 - LLM 분석으로 대체 */}
              <div className="hidden border-t border-gray-200 my-8"></div>

              {/* 데이터 분포 특성 - 삭제됨 */}
              <div className="hidden mb-8">
                <h4 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-3">
                  <ChartBarIcon className="w-6 h-6 text-primary-600" />
                  데이터 분포 특성
                </h4>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="bg-blue-50 rounded-lg p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-primary-600 rounded-lg flex items-center justify-center">
                  <ChartBarIcon className="w-5 h-5 text-white" />
                </div>
                <h4 className="font-semibold text-blue-900">중심경향 분석</h4>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-blue-700">평균값</span>
                  <span className="font-bold text-blue-900">{formatNumber(processedStats.numeric_stats.mean)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-blue-700">중위수</span>
                  <span className="font-bold text-blue-900">{formatNumber(processedStats.numeric_stats.median)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-blue-700">평균-중위수 차이</span>
                  <span className="font-bold text-blue-900">{formatNumber(Math.abs(processedStats.numeric_stats.mean - processedStats.numeric_stats.median))}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-blue-700">표준편차</span>
                  <span className="font-bold text-blue-900">{formatNumber(processedStats.numeric_stats.std_dev)}</span>
                </div>
              </div>
            </div>

            <div className="bg-green-50 rounded-lg p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-green-600 rounded-lg flex items-center justify-center">
                  <SparklesIcon className="w-5 h-5 text-white" />
                </div>
                <h4 className="font-semibold text-green-900">변동성 분석</h4>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-green-700">최댓값</span>
                  <span className="font-bold text-green-900">{formatNumber(processedStats.numeric_stats.max)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-green-700">최솟값</span>
                  <span className="font-bold text-green-900">{formatNumber(processedStats.numeric_stats.min)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-green-700">범위</span>
                  <span className="font-bold text-green-900">{formatNumber(processedStats.numeric_stats.max - processedStats.numeric_stats.min)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-green-700">변동계수</span>
                  <span className="font-bold text-green-900">
                    {processedStats.numeric_stats.count > 0 
                      ? formatNumber((processedStats.numeric_stats.std_dev / processedStats.numeric_stats.mean) * 100) + '%'
                      : '0%'
                    }
                  </span>
                </div>
              </div>
            </div>

            <div className="bg-purple-50 rounded-lg p-6">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 bg-purple-600 rounded-lg flex items-center justify-center">
                  <TableCellsIcon className="w-5 h-5 text-white" />
                </div>
                <h4 className="font-semibold text-purple-900">데이터 구성</h4>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between items-center">
                  <span className="text-purple-700">수집된 통계표</span>
                  <span className="font-bold text-purple-900">{processedStats.data_structure.table_count}개</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-purple-700">총 데이터 필드</span>
                  <span className="font-bold text-purple-900">{processedStats.data_structure.total_fields}개</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-purple-700">숫자 데이터</span>
                  <span className="font-bold text-purple-900">
                    {processedStats.data_structure.numeric_fields}개 ({((processedStats.data_structure.numeric_fields / processedStats.data_structure.total_fields) * 100).toFixed(1)}%)
                  </span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-purple-700">텍스트 데이터</span>
                  <span className="font-bold text-purple-900">
                    {processedStats.data_structure.text_fields}개 ({((processedStats.data_structure.text_fields / processedStats.data_structure.total_fields) * 100).toFixed(1)}%)
                  </span>
                </div>
              </div>
            </div>
          </div>
              </div>

              {/* 객관적 현황 요약 섹션 삭제됨 - LLM 분석으로 대체 */}
              <div className="hidden border-t border-gray-200 my-8"></div>

              {/* 객관적 현황 요약 - 삭제됨 */}
              <div className="hidden">
                <h4 className="text-xl font-bold text-gray-900 mb-6 flex items-center gap-3">
                  <SparklesIcon className="w-6 h-6 text-primary-600" />
                  객관적 현황 요약
                </h4>
          <div className="bg-gray-50 rounded-lg p-8">
            
            
            <motion.div 
              className="mb-8 p-6 bg-green-50 rounded-lg border border-green-200 shadow-lg"
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: 0.6 }}
            >
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 bg-green-600 rounded-lg flex items-center justify-center flex-shrink-0">
                  <SparklesIcon className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h5 className="font-semibold text-green-900 mb-2">실제 수집 데이터 기반 분석</h5>
                  <p className="text-sm text-green-800 leading-relaxed">
                    이 분석은 실제로 수집된 <span className="font-bold">{processedStats.data_structure.table_count}개 통계표</span>의{' '}
                    <span className="font-bold">{processedStats.data_structure.total_fields}개 데이터 필드</span>를 기반으로 작성되었습니다.
                    숫자 데이터 <span className="font-bold">{processedStats.numeric_stats.count}개</span>에 대한 객관적 기술통계 분석 결과입니다.
                  </p>
                </div>
              </div>
            </motion.div>
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
              <div className="bg-white rounded-lg p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-red-600 rounded-lg flex items-center justify-center">
                    <ChartBarIcon className="w-5 h-5 text-white" />
                  </div>
                  <h4 className="font-semibold text-gray-900">핵심 통계</h4>
                </div>
                <div className="space-y-4">
                  <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
                    <span className="text-red-700 font-medium">가장 높은 수치</span>
                    <span className="font-bold text-red-900 text-lg">{formatNumber(processedStats.numeric_stats.max)}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                    <span className="text-blue-700 font-medium">가장 낮은 수치</span>
                    <span className="font-bold text-blue-900 text-lg">{formatNumber(processedStats.numeric_stats.min)}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                    <span className="text-green-700 font-medium">전체 평균</span>
                    <span className="font-bold text-green-900 text-lg">{formatNumber(processedStats.numeric_stats.mean)}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
                    <span className="text-purple-700 font-medium">중앙값</span>
                    <span className="font-bold text-purple-900 text-lg">{formatNumber(processedStats.numeric_stats.median)}</span>
                  </div>
                </div>
              </div>
              
              <div className="bg-white rounded-lg p-6">
                <div className="flex items-center gap-3 mb-4">
                  <div className="w-10 h-10 bg-teal-600 rounded-lg flex items-center justify-center">
                    <TableCellsIcon className="w-5 h-5 text-white" />
                  </div>
                  <h4 className="font-semibold text-gray-900">수집 현황</h4>
                </div>
                <div className="space-y-4">
                  <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                    <span className="text-gray-700 font-medium">분석 일시</span>
                    <span className="font-bold text-gray-900">{new Date(analysisData.analysis_date).toLocaleString('ko-KR')}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                    <span className="text-blue-700 font-medium">수집된 통계표</span>
                    <span className="font-bold text-blue-900">{processedStats.data_structure.table_count}개</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                    <span className="text-green-700 font-medium">숫자 데이터</span>
                    <span className="font-bold text-green-900">{processedStats.numeric_stats.count}개</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
                    <span className="text-purple-700 font-medium">전체 규모</span>
                    <span className="font-bold text-purple-900">{formatNumber(processedStats.numeric_stats.total)}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
              </div>
            </motion.div>

      </div>
    </div>
  );
};

export default EnhancedBasicStatisticsViewer;