import React from 'react';

interface AnalysisActionButtonsProps {
  onBack: () => void;
  onDownloadMD: () => void;
  onDownloadPDF: () => void;
  onViewOriginal: () => void;
  onInspectData?: () => void;
  onViewTableAnalysis?: () => void;
  originalUrl?: string;
  analysisTitle?: string;
}

export const AnalysisActionButtons: React.FC<AnalysisActionButtonsProps> = ({
  onBack,
  onDownloadMD,
  onDownloadPDF,
  onViewOriginal,
  onInspectData,
  onViewTableAnalysis,
  originalUrl,
  analysisTitle = "분석 결과"
}) => {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {/* 뒤로가기 버튼 */}
      <button
        onClick={onBack}
        className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-50 transition-colors flex items-center gap-2 text-sm font-medium"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
        목록으로
      </button>

      {/* MD 파일 다운로드 */}
      <button
        onClick={onDownloadMD}
        className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700 transition-colors flex items-center gap-2 text-sm font-medium"
        title="마크다운 파일로 다운로드"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        MD
      </button>

      {/* PDF 파일 다운로드 */}
      <button
        onClick={onDownloadPDF}
        className="bg-primary-600 text-white px-4 py-2 rounded-md hover:bg-primary-700 transition-colors flex items-center gap-2 text-sm font-medium"
        title="PDF 파일로 다운로드"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
        PDF
      </button>

      {/* 원본 보기 */}
      <button
        onClick={onViewOriginal}
        className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-50 transition-colors flex items-center gap-2 text-sm font-medium"
        title={originalUrl ? `원본 페이지 보기: ${originalUrl}` : "원본 데이터 보기"}
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
        </svg>
        원본
      </button>

      {/* 데이터 검사 */}
      {onInspectData && (
        <button
          onClick={onInspectData}
          className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-50 transition-colors flex items-center gap-2 text-sm font-medium"
          title="수집된 데이터를 상세 검사합니다"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          데이터 검사
        </button>
      )}

      {/* 원본 파일 다운로드 */}
      {onViewTableAnalysis && (
        <button
          onClick={onViewTableAnalysis}
          className="bg-white border border-gray-300 text-gray-700 px-4 py-2 rounded-md hover:bg-gray-50 transition-colors flex items-center gap-2 text-sm font-medium"
          title="통계표별 원본 파일을 다운로드합니다"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
          </svg>
          원본 파일
        </button>
      )}
    </div>
  );
};