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
  total_records: number;
  year_range: {
    min_year: number | null;
    max_year: number | null;
  };
  field_count: number;
  statistics: {
    count?: number;
    mean?: number;
    median?: number;
    std?: number;
    min?: number;
    max?: number;
  };
  data_quality: {
    completeness: number;
  };
  downloaded_file?: {
    filename: string;
    path: string;
    size: number;
    modified: string;
  };
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
            <h3 className="text-xl font-semibold text-gray-800 mb-2">원본 파일 로딩</h3>
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
            <p className="text-gray-600 mt-1">통계표별 원본 파일</p>
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
              <p className="text-sm text-gray-500 mt-1">다운로드할 통계표를 선택하세요</p>
            </div>
            <div className="p-2">
              {Object.keys(analysisData.tables_analysis).map((tableName) => {
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
                      {tableData.downloaded_file ? '파일 있음' : '파일 없음'}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* 오른쪽: 다운로드 파일 */}
        <div className="lg:col-span-3">
          {selectedTableData ? (
            <TableDetailView tableData={selectedTableData} />
          ) : (
            <div className="bg-white rounded-lg border shadow-sm p-8 text-center">
              <p className="text-gray-500">통계표를 선택하여 파일을 확인하세요.</p>
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
  if (!tableData.downloaded_file) {
    return (
      <div className="bg-white rounded-lg border shadow-sm p-8 text-center">
        <div className="flex flex-col items-center justify-center">
          <svg className="w-16 h-16 text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          <h3 className="text-lg font-medium text-gray-900 mb-2">다운로드 파일 없음</h3>
          <p className="text-sm text-gray-500">
            이 통계표는 파일 다운로드 방식으로 수집되지 않았습니다.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg border shadow-sm">
      <div className="p-4 border-b">
        <h3 className="text-lg font-medium text-gray-900">📥 {tableData.table_name}</h3>
        <p className="text-sm text-gray-500 mt-1">실제로 수집된 원본 파일</p>
      </div>
      <div className="p-4">
        <div className="flex items-center justify-between p-4 bg-blue-50 rounded-lg border border-blue-200">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <svg className="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 truncate">
                {tableData.downloaded_file.filename}
              </p>
              <p className="text-sm text-gray-500">
                {(tableData.downloaded_file.size / 1024).toFixed(2)} KB • {new Date(tableData.downloaded_file.modified).toLocaleString('ko-KR')}
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              const downloadUrl = `/api/download-file?file_path=${encodeURIComponent(tableData.downloaded_file!.path)}`;
              window.open(downloadUrl, '_blank');
            }}
            className="ml-4 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center space-x-2"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            <span>다운로드</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default TableAnalysisViewer;
