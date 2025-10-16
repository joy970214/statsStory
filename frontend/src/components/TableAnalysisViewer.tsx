import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { DocumentArrowDownIcon } from '@heroicons/react/24/outline';

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

    } catch (err) {
      console.error('테이블 분석 로드 오류:', err);
      setError(err instanceof Error ? err.message : '알 수 없는 오류가 발생했습니다');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-white/80 z-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block w-16 h-16 border-4 border-gray-200 border-t-primary-600 rounded-full animate-spin mb-4"></div>
          <h3 className="text-lg font-semibold text-gray-800 mb-2">원본 파일 로딩</h3>
          <p className="text-gray-600">'{statName}' 데이터를 분석하는 중...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6">
        <h3 className="text-lg font-medium text-red-800 mb-2">분석 데이터 로드 실패</h3>
        <p className="text-red-600">{error}</p>
        <div className="mt-4">
          <button
            onClick={loadTableAnalysis}
            className="bg-red-600 text-white px-4 py-2 rounded-md hover:bg-red-700"
          >
            다시 시도
          </button>
        </div>
      </div>
    );
  }

  if (!analysisData) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500">분석 데이터를 찾을 수 없습니다.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 통계표 목록을 카드 형태로 나열 */}
      {Object.keys(analysisData.tables_analysis).map((tableName) => {
        const tableData = analysisData.tables_analysis[tableName];

        return (
          <div key={tableName} className="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center space-x-3 flex-1 min-w-0">
                <div className="flex-shrink-0">
                  <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${
                    tableData.downloaded_file
                      ? 'bg-gradient-to-br from-green-500 to-green-600'
                      : 'bg-gradient-to-br from-gray-400 to-gray-500'
                  }`}>
                    <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900">
                    {tableName}
                  </p>
                  {tableData.downloaded_file ? (
                    <p className="text-xs text-gray-500 mt-1">
                      {tableData.downloaded_file.filename} • {(tableData.downloaded_file.size / 1024).toFixed(2)} KB
                    </p>
                  ) : (
                    <p className="text-xs text-gray-500 mt-1">
                      다운로드 파일 없음
                    </p>
                  )}
                </div>
              </div>

              {tableData.downloaded_file && (
                <button
                  onClick={async (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    const downloadUrl = `/api/download-file?file_path=${encodeURIComponent(tableData.downloaded_file!.path)}`;

                    try {
                      const response = await fetch(downloadUrl);
                      if (!response.ok) {
                        throw new Error(`다운로드 실패: ${response.status}`);
                      }

                      const blob = await response.blob();
                      const blobUrl = window.URL.createObjectURL(blob);

                      const link = document.createElement('a');
                      link.href = blobUrl;
                      link.download = tableData.downloaded_file!.filename;
                      document.body.appendChild(link);
                      link.click();
                      document.body.removeChild(link);

                      window.URL.revokeObjectURL(blobUrl);
                    } catch (error) {
                      console.error('다운로드 오류:', error);
                      alert('파일 다운로드에 실패했습니다.');
                    }
                  }}
                  className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700 transition-colors flex items-center gap-2 text-sm font-medium"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                  </svg>
                  <span className="font-medium">다운로드</span>
                </button>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default TableAnalysisViewer;
