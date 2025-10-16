import React, { useState } from 'react';
import { StatItem } from '../services/api';
import {
  MagnifyingGlassIcon,
  ChartBarIcon,
  CalendarIcon,
  TagIcon
} from '@heroicons/react/24/outline';

interface StatCardProps {
  stat: StatItem;
  onSelect: (stat: StatItem) => void;
  disabled?: boolean;
}

export const StatCard: React.FC<StatCardProps> = ({ stat, onSelect, disabled = false }) => {
  const [isProcessing, setIsProcessing] = useState(false);

  const handleAnalysisClick = () => {
    if (disabled || isProcessing) return;

    // 🚀 즉시 버튼 비활성화
    setIsProcessing(true);
    onSelect(stat);
  };

  const isButtonDisabled = disabled || isProcessing;

  // 카테고리별 색상 매핑 (해시 기반으로 고정된 색상 할당)
  const getCategoryColor = (category: string) => {
    const colors = [
      'bg-primary-50 text-primary-700',      // 파란색
      'bg-success-50 text-success-700',      // 초록색
      'bg-warning-50 text-warning-700',      // 주황색
      'bg-info-50 text-info-700',            // 하늘색
      'bg-danger-50 text-danger-700',        // 빨간색
      'bg-secondary-50 text-secondary-700',  // 회색
      'bg-primary-100 text-primary-800',     // 진한 파란색
      'bg-success-100 text-success-700',     // 진한 초록색
      'bg-warning-100 text-warning-700',     // 진한 주황색
      'bg-danger-100 text-danger-700',       // 진한 빨간색
    ];
    
    // 카테고리 문자열을 해시화하여 일관된 색상 인덱스 생성
    let hash = 0;
    for (let i = 0; i < category.length; i++) {
      hash = category.charCodeAt(i) + ((hash << 5) - hash);
    }
    const index = Math.abs(hash) % colors.length;
    
    return colors[index];
  };

  return (
    <div className="bg-white rounded-lg shadow hover:shadow-md transition-shadow border border-gray-200">
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-3 line-clamp-2">
          {stat.title}
        </h3>
        
        <div className="text-sm text-gray-600 mb-4">
          <div className="flex justify-between items-center mb-3">
            <span className={`${getCategoryColor(stat.stat_field || '기타')} px-3 py-1 rounded-md text-xs font-medium flex items-center gap-1.5`}>
              <TagIcon className="w-3.5 h-3.5" />
              {stat.stat_field || '기타'}
            </span>
            <span className="text-gray-500 flex items-center gap-1.5">
              <CalendarIcon className="w-3.5 h-3.5" />
              {stat.publish_date}
            </span>
          </div>
        </div>
        
        <div className="flex gap-2 mt-6">
          <button
            className={`flex-1 py-2.5 px-4 rounded-md transition-colors flex items-center justify-center gap-2 font-medium text-sm ${
              isButtonDisabled
                ? 'bg-gray-300 text-gray-500 cursor-not-allowed'
                : 'bg-primary-600 text-white hover:bg-primary-700'
            }`}
            onClick={handleAnalysisClick}
            disabled={isButtonDisabled}
          >
            <MagnifyingGlassIcon className="w-4 h-4" />
            {disabled ? '취소 중...' : isProcessing ? '처리 중...' : '분석하기'}
          </button>

          {stat.url && (
            <button
              className="bg-white border border-gray-300 text-gray-700 py-2.5 px-4 rounded-md hover:bg-gray-50 transition-colors flex items-center gap-2 text-sm font-medium"
              onClick={(e) => {
                e.stopPropagation();
                window.open(stat.url, '_blank', 'noopener,noreferrer');
              }}
              title="통계누리에서 원본 데이터 확인"
            >
              <ChartBarIcon className="w-4 h-4" />
              원본
            </button>
          )}
        </div>
      </div>
    </div>
  );
};