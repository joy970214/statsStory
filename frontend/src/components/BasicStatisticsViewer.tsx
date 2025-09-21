import React, { useRef, useState } from 'react';
import { AdvancedCardNewsResponse } from '../services/api';
import { AnalysisActionButtons } from './AnalysisActionButtons';
import { DataInspectionViewer } from './DataInspectionViewer';
import { 
  downloadMarkdown, 
  downloadPDF, 
  openOriginalUrl, 
  generateBasicStatisticsMarkdown 
} from '../utils/downloadUtils';

interface BasicStatisticsViewerProps {
  analysisData: AdvancedCardNewsResponse;
  onBack: () => void;
}

export const BasicStatisticsViewer: React.FC<BasicStatisticsViewerProps> = ({ analysisData, onBack }) => {
  const { basic_statistics } = analysisData;
  const contentRef = useRef<HTMLDivElement>(null);
  const [showDataInspection, setShowDataInspection] = useState(false);

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
          <h1 className="text-2xl font-bold text-gray-900">📈 기본통계현황분석 결과</h1>
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
        
        <div className="bg-pink-50 rounded-lg p-4">
          <h2 className="text-lg font-semibold text-pink-900 mb-2">{analysisData.stat_name}</h2>
          <div className="flex items-center gap-4 text-sm text-pink-700">
            <span>분석 완료: {new Date(analysisData.analysis_date).toLocaleString('ko-KR')}</span>
            <span className="bg-pink-200 px-2 py-1 rounded-full">{analysisData.analysis_type}</span>
          </div>
        </div>
      </div>

      {/* 분석 내용 - PDF 다운로드 대상 */}
      <div ref={contentRef}>

        {/* 데이터 구조 분석 */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
          <h3 className="text-xl font-semibold text-gray-900 mb-4">🔍 데이터 구조 분석</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="bg-green-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-green-700">
                {analysisData.analysis_summary.total_data_points}
              </div>
              <div className="text-sm text-green-600">수집된 데이터</div>
            </div>
            <div className="bg-blue-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-blue-700">
                {Object.keys(basic_statistics).length}
              </div>
              <div className="text-sm text-blue-600">분석 필드</div>
            </div>
            <div className="bg-purple-50 rounded-lg p-4 text-center">
              <div className="text-lg font-bold text-purple-700">
                {analysisData.analysis_summary.analysis_period}
              </div>
              <div className="text-sm text-purple-600">분석 기간</div>
            </div>
          </div>
        </div>

        {/* 분석 요약 */}
        <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">📊 분석 개요</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-blue-50 rounded-lg p-4 text-center">
            <div className="text-lg font-semibold text-blue-700">
              {analysisData.analysis_summary.analysis_period}
            </div>
            <div className="text-sm text-blue-600">분석 기간</div>
          </div>
          <div className="bg-green-50 rounded-lg p-4 text-center">
            <div className="text-lg font-semibold text-green-700">
              {analysisData.analysis_summary.total_data_points}개
            </div>
            <div className="text-sm text-green-600">데이터 포인트</div>
          </div>
          <div className="bg-purple-50 rounded-lg p-4 text-center">
            <div className="text-xs font-semibold text-purple-700">
              {analysisData.analysis_summary.analysis_focus}
            </div>
            <div className="text-sm text-purple-600">분석 초점</div>
          </div>
        </div>
      </div>

      {/* 기초통계 지표 */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-6">🔢 기초통계 지표</h3>
        
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
          <div className="bg-red-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-red-700">
              {formatNumber(basic_statistics.mean)}
            </div>
            <div className="text-sm text-red-600 font-medium">평균값</div>
            <div className="text-xs text-red-500 mt-1">Mean</div>
          </div>

          <div className="bg-orange-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-orange-700">
              {formatNumber(basic_statistics.median)}
            </div>
            <div className="text-sm text-orange-600 font-medium">중위수</div>
            <div className="text-xs text-orange-500 mt-1">Median</div>
          </div>

          <div className="bg-yellow-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-yellow-700">
              {formatNumber(basic_statistics.max)}
            </div>
            <div className="text-sm text-yellow-600 font-medium">최댓값</div>
            <div className="text-xs text-yellow-500 mt-1">Maximum</div>
          </div>

          <div className="bg-green-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-green-700">
              {formatNumber(basic_statistics.min)}
            </div>
            <div className="text-sm text-green-600 font-medium">최솟값</div>
            <div className="text-xs text-green-500 mt-1">Minimum</div>
          </div>

          <div className="bg-blue-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-blue-700">
              {formatNumber(basic_statistics.total)}
            </div>
            <div className="text-sm text-blue-600 font-medium">총합계</div>
            <div className="text-xs text-blue-500 mt-1">Total</div>
          </div>

          <div className="bg-indigo-50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-indigo-700">
              {basic_statistics.count}
            </div>
            <div className="text-sm text-indigo-600 font-medium">데이터 개수</div>
            <div className="text-xs text-indigo-500 mt-1">Count</div>
          </div>
        </div>

        {/* 통계 해석 */}
        <div className="bg-gray-50 rounded-lg p-6">
          <h4 className="text-lg font-semibold text-gray-900 mb-3">📋 통계 지표 해석</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <span className="font-medium text-gray-700">평균값:</span>
              <span className="text-gray-600 ml-2">전체 데이터의 중심 경향을 나타냅니다.</span>
            </div>
            <div>
              <span className="font-medium text-gray-700">중위수:</span>
              <span className="text-gray-600 ml-2">데이터의 중앙값으로 극값의 영향을 덜 받습니다.</span>
            </div>
            <div>
              <span className="font-medium text-gray-700">최댓값/최솟값:</span>
              <span className="text-gray-600 ml-2">데이터의 범위와 변동폭을 보여줍니다.</span>
            </div>
            <div>
              <span className="font-medium text-gray-700">총합계:</span>
              <span className="text-gray-600 ml-2">전체 규모와 크기를 나타냅니다.</span>
            </div>
          </div>
        </div>
      </div>

      {/* 데이터 분포 특성 */}
      <div className="bg-white rounded-lg shadow-sm border p-6 mb-6">
        <h3 className="text-xl font-semibold text-gray-900 mb-4">📊 데이터 분포 특성</h3>
        <div className="space-y-4">
          <div className="bg-blue-50 rounded-lg p-4">
            <h4 className="font-medium text-blue-900 mb-2">중심경향 분석</h4>
            <div className="text-sm text-blue-800">
              <p>• 평균값: {formatNumber(basic_statistics.mean)}</p>
              <p>• 중위수: {formatNumber(basic_statistics.median)}</p>
              <p>• 평균과 중위수 차이: {formatNumber(Math.abs(basic_statistics.mean - basic_statistics.median))}</p>
            </div>
          </div>

          <div className="bg-green-50 rounded-lg p-4">
            <h4 className="font-medium text-green-900 mb-2">변동성 분석</h4>
            <div className="text-sm text-green-800">
              <p>• 최댓값: {formatNumber(basic_statistics.max)}</p>
              <p>• 최솟값: {formatNumber(basic_statistics.min)}</p>
              <p>• 범위(Range): {formatNumber(basic_statistics.max - basic_statistics.min)}</p>
            </div>
          </div>

          <div className="bg-purple-50 rounded-lg p-4">
            <h4 className="font-medium text-purple-900 mb-2">규모 분석</h4>
            <div className="text-sm text-purple-800">
              <p>• 총 데이터 수: {basic_statistics.count}개</p>
              <p>• 총합계: {formatNumber(basic_statistics.total)}</p>
              <p>• 데이터 당 평균: {formatNumber(basic_statistics.total / basic_statistics.count)}</p>
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
              <h4 className="font-semibold text-gray-900 mb-3">🎯 핵심 수치</h4>
              <ul className="space-y-2 text-sm text-gray-700">
                <li>• 가장 높은 수치: <span className="font-medium text-red-600">{formatNumber(basic_statistics.max)}</span></li>
                <li>• 가장 낮은 수치: <span className="font-medium text-blue-600">{formatNumber(basic_statistics.min)}</span></li>
                <li>• 전체 평균: <span className="font-medium text-green-600">{formatNumber(basic_statistics.mean)}</span></li>
                <li>• 중앙값: <span className="font-medium text-purple-600">{formatNumber(basic_statistics.median)}</span></li>
              </ul>
            </div>
            
            <div>
              <h4 className="font-semibold text-gray-900 mb-3">📈 데이터 현황</h4>
              <ul className="space-y-2 text-sm text-gray-700">
                <li>• 분석 기간: <span className="font-medium">{analysisData.analysis_summary.analysis_period}</span></li>
                <li>• 총 데이터 수: <span className="font-medium">{basic_statistics.count}개</span></li>
                <li>• 전체 규모: <span className="font-medium">{formatNumber(basic_statistics.total)}</span></li>
                <li>• 분석 유형: <span className="font-medium">기본통계현황분석</span></li>
              </ul>
            </div>
          </div>
          
          <div className="mt-6 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
            <p className="text-sm text-yellow-800">
              <span className="font-medium">📋 분석 특징:</span> 
              주관적 해석을 배제하고 수집된 데이터의 객관적 사실만을 바탕으로 한 기술통계 분석 결과입니다.
              기초통계 지표를 통해 현황을 파악하고 데이터 분포 특성을 확인할 수 있습니다.
            </p>
          </div>
        </div>
      </div>
    </div>
    </div>
  );
};