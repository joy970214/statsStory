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
  onBack 
}) => {
  const contentRef = useRef<HTMLDivElement>(null);
  const [showDataInspection, setShowDataInspection] = useState(false);
  const [processedStats, setProcessedStats] = useState<ProcessedStatistics | null>(null);
  const [loading, setLoading] = useState(true);

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

    rawData.raw_data.forEach((stat: any, statIndex: number) => {
      const tableName = stat.table_name || `테이블 ${statIndex + 1}`;
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
          <AnalysisActionButtons
            onBack={onBack}
            onDownloadMD={handleDownloadMD}
            onDownloadPDF={handleDownloadPDF}
            onViewOriginal={handleViewOriginal}
            onInspectData={handleInspectData}
            originalUrl={analysisData.metadata?.url}
            analysisTitle={analysisData.stat_name}
          />
        </div>
        
        <div className="bg-blue-50 rounded-lg p-4">
          <h2 className="text-lg font-semibold text-blue-900 mb-2">{analysisData.stat_name}</h2>
          <div className="flex items-center gap-4 text-sm text-blue-700">
            <span>분석 완료: {new Date(analysisData.analysis_date).toLocaleString('ko-KR')}</span>
            <span className="bg-blue-200 px-2 py-1 rounded-full">실제 수집 데이터 분석</span>
          </div>
        </div>
      </div>

      {/* 분석 내용 - PDF 다운로드 대상 */}
      <div ref={contentRef}>
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
            <h4 className="font-medium text-gray-900 mb-2">수집된 통계표 목록</h4>
            <div className="flex flex-wrap gap-2">
              {processedStats.data_structure.collected_tables.map((table, index) => (
                <span key={index} className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm">
                  {table}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* 기초통계 지표 */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-6">🔢 기초통계 지표 (숫자 데이터 기준)</h3>
          
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
            <div className="bg-red-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-red-700">
                {formatNumber(processedStats.numeric_stats.mean)}
              </div>
              <div className="text-sm text-red-600 font-medium">평균값</div>
              <div className="text-xs text-red-500 mt-1">Mean</div>
            </div>

            <div className="bg-orange-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-orange-700">
                {formatNumber(processedStats.numeric_stats.median)}
              </div>
              <div className="text-sm text-orange-600 font-medium">중위수</div>
              <div className="text-xs text-orange-500 mt-1">Median</div>
            </div>

            <div className="bg-yellow-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-yellow-700">
                {formatNumber(processedStats.numeric_stats.max)}
              </div>
              <div className="text-sm text-yellow-600 font-medium">최댓값</div>
              <div className="text-xs text-yellow-500 mt-1">Maximum</div>
            </div>

            <div className="bg-green-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-green-700">
                {formatNumber(processedStats.numeric_stats.min)}
              </div>
              <div className="text-sm text-green-600 font-medium">최솟값</div>
              <div className="text-xs text-green-500 mt-1">Minimum</div>
            </div>

            <div className="bg-blue-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-blue-700">
                {formatNumber(processedStats.numeric_stats.total)}
              </div>
              <div className="text-sm text-blue-600 font-medium">총합계</div>
              <div className="text-xs text-blue-500 mt-1">Total</div>
            </div>

            <div className="bg-indigo-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-indigo-700">
                {processedStats.numeric_stats.count}
              </div>
              <div className="text-sm text-indigo-600 font-medium">데이터 개수</div>
              <div className="text-xs text-indigo-500 mt-1">Count</div>
            </div>
          </div>

          {/* 추가 통계 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div className="bg-purple-50 rounded-lg p-4 text-center">
              <div className="text-xl font-bold text-purple-700">
                {formatNumber(processedStats.numeric_stats.std_dev)}
              </div>
              <div className="text-sm text-purple-600 font-medium">표준편차</div>
              <div className="text-xs text-purple-500 mt-1">Standard Deviation</div>
            </div>
            <div className="bg-pink-50 rounded-lg p-4 text-center">
              <div className="text-xl font-bold text-pink-700">
                {processedStats.numeric_stats.count > 0 
                  ? formatNumber((processedStats.numeric_stats.std_dev / processedStats.numeric_stats.mean) * 100)
                  : '0'
                }%
              </div>
              <div className="text-sm text-pink-600 font-medium">변동계수</div>
              <div className="text-xs text-pink-500 mt-1">Coefficient of Variation</div>
            </div>
          </div>
        </div>

        {/* 수집된 데이터 샘플 */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-4">📋 수집된 데이터 샘플</h3>
          <div className="overflow-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">필드명</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">값</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">타입</th>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">출처</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {processedStats.sample_data.map((item, index) => (
                  <tr key={index} className="hover:bg-gray-50">
                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900 font-mono">
                      {item.field_name}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-900">
                      <span className={item.type === 'number' ? 'font-medium text-blue-600' : ''}>
                        {String(item.value)}
                      </span>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-xs">
                      <span className={`px-2 py-1 rounded-full ${
                        item.type === 'number' 
                          ? 'bg-blue-100 text-blue-800' 
                          : 'bg-gray-100 text-gray-800'
                      }`}>
                        {item.type}
                      </span>
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap text-sm text-gray-600">
                      {item.source_table}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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
      </div>
    </div>
  );
};