import React, { useRef, useState } from 'react';
import { BasicAnalysisResponse } from '../services/api';
import { AnalysisActionButtons } from './AnalysisActionButtons';
import { DataInspectionViewer } from './DataInspectionViewer';
import { 
  downloadMarkdown, 
  downloadPDF, 
  openOriginalUrl, 
  generateBasicAnalysisMarkdown 
} from '../utils/downloadUtils';

interface BasicAnalysisViewerProps {
  analysisData: BasicAnalysisResponse;
  onBack: () => void;
}

export const BasicAnalysisViewer: React.FC<BasicAnalysisViewerProps> = ({ analysisData, onBack }) => {
  const contentRef = useRef<HTMLDivElement>(null);
  const [showDataInspection, setShowDataInspection] = useState(false);

  const handleDownloadMD = () => {
    try {
      const markdown = generateBasicAnalysisMarkdown(analysisData);
      const filename = `기본분석_${analysisData.stat_name}_${new Date().toISOString().split('T')[0]}`;
      downloadMarkdown(markdown, filename);
    } catch (error) {
      console.error('MD 다운로드 실패:', error);
      alert('마크다운 파일 다운로드에 실패했습니다.');
    }
  };

  const handleDownloadPDF = async () => {
    if (contentRef.current) {
      try {
        const filename = `기본분석_${analysisData.stat_name}_${new Date().toISOString().split('T')[0]}`;
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

  // 데이터 검사 모드일 때는 DataInspectionViewer 렌더링
  if (showDataInspection) {
    return (
      <DataInspectionViewer 
        statName={analysisData.stat_name} 
        onBack={handleBackFromInspection}
      />
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* 헤더 */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-4">
          <h1 className="text-2xl font-bold text-gray-900">📊 기본 분석 결과</h1>
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
          <p className="text-blue-700 text-sm">
            분석 완료: {new Date(analysisData.analysis_date).toLocaleString('ko-KR')}
          </p>
        </div>
      </div>

      {/* 분석 내용 - PDF 다운로드 대상 */}
      <div ref={contentRef}>
        {/* 메타데이터 정보 */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">📋 메타데이터 정보</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-3">
            <div>
              <span className="text-sm font-medium text-gray-600">제목:</span>
              <p className="text-gray-900">{analysisData.metadata.title}</p>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-600">목적:</span>
              <p className="text-gray-700">{analysisData.metadata.purpose || '정보 없음'}</p>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-600">주기:</span>
              <p className="text-gray-700">{analysisData.metadata.frequency || '정보 없음'}</p>
            </div>
          </div>
          <div className="space-y-3">
            <div>
              <span className="text-sm font-medium text-gray-600">담당부서:</span>
              <p className="text-gray-700">{analysisData.metadata.department || '정보 없음'}</p>
            </div>
            <div>
              <span className="text-sm font-medium text-gray-600">키워드:</span>
              <div className="flex flex-wrap gap-1 mt-1">
                {analysisData.metadata.keywords.map((keyword, index) => (
                  <span key={index} className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs">
                    {keyword}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 데이터 구조 분석 */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">🔍 데이터 구조 분석</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
          <div className="bg-green-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-green-700">
              {analysisData.data_structure.total_years}
            </div>
            <div className="text-sm text-green-600">수집된 연도</div>
          </div>
          <div className="bg-blue-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-blue-700">
              {analysisData.data_structure.data_keys.length}
            </div>
            <div className="text-sm text-blue-600">데이터 필드</div>
          </div>
          <div className="bg-purple-50 rounded-lg p-4 text-center">
            <div className="text-lg font-bold text-purple-700">
              {analysisData.data_structure.year_range.start} - {analysisData.data_structure.year_range.end}
            </div>
            <div className="text-sm text-purple-600">데이터 범위</div>
          </div>
        </div>

        <div className="bg-gray-50 rounded-lg p-4">
          <h4 className="font-medium text-gray-900 mb-2">수집된 데이터 필드:</h4>
          <div className="flex flex-wrap gap-2">
            {analysisData.data_structure.data_keys.map((key, index) => (
              <span key={index} className="bg-gray-200 text-gray-800 px-3 py-1 rounded-md text-sm">
                {key}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* 수집 현황 요약 */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">📈 수집 현황 요약</h3>
        <div className="space-y-4">
          <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
            <span className="text-green-800 font-medium">수집 상태</span>
            <span className="text-green-700 bg-green-200 px-3 py-1 rounded-full text-sm">
              {analysisData.basic_analysis.collection_summary.status}
            </span>
          </div>
          
          <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
            <span className="text-blue-800 font-medium">메타데이터 품질</span>
            <span className="text-blue-700 bg-blue-200 px-3 py-1 rounded-full text-sm">
              {analysisData.basic_analysis.collection_summary.metadata_quality}
            </span>
          </div>
          
          <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
            <span className="text-purple-800 font-medium">데이터 완성도</span>
            <span className="text-purple-700 bg-purple-200 px-3 py-1 rounded-full text-sm">
              {analysisData.basic_analysis.collection_summary.data_completeness}
            </span>
          </div>
        </div>
      </div>

      {/* 데이터 해석 */}
      <div className="bg-white rounded-lg shadow-sm border p-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">💡 데이터 해석</h3>
        <div className="bg-gray-50 rounded-lg p-4">
          <pre className="whitespace-pre-wrap text-gray-700 text-sm leading-relaxed">
            {analysisData.basic_analysis.data_interpretation}
          </pre>
        </div>
      </div>
    </div>
    </div>
  );
};