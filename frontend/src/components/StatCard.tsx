import React, { useState } from 'react';
import { StatItem } from '../services/api';
import {
  MagnifyingGlassIcon,
  ChartBarIcon,
  CalendarIcon,
  TagIcon,
  CheckCircleIcon
} from '@heroicons/react/24/outline';

interface StatCardProps {
  stat: StatItem;
  onSelect: (stat: StatItem) => void;
  disabled?: boolean;
  isCollected?: boolean;
}

export const StatCard: React.FC<StatCardProps> = ({ stat, onSelect, disabled = false, isCollected = false }) => {
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
      'bg-blue-50 text-blue-700 border-blue-200',           // 파란색
      'bg-green-50 text-green-700 border-green-200',        // 초록색
      'bg-yellow-50 text-yellow-700 border-yellow-200',     // 노란색
      'bg-cyan-50 text-cyan-700 border-cyan-200',           // 시안색
      'bg-red-50 text-red-700 border-red-200',              // 빨간색
      'bg-violet-50 text-violet-700 border-violet-200',     // 보라색
      'bg-fuchsia-50 text-fuchsia-700 border-fuchsia-200',  // 자홍색
      'bg-indigo-50 text-indigo-700 border-indigo-200',     // 인디고
      'bg-teal-50 text-teal-700 border-teal-200',           // 청록색
      'bg-orange-50 text-orange-700 border-orange-200',     // 오렌지색
      'bg-rose-50 text-rose-700 border-rose-200',           // 로즈색
      'bg-emerald-50 text-emerald-700 border-emerald-200',  // 에메랄드
      'bg-amber-50 text-amber-700 border-amber-200',        // 호박색
      'bg-sky-50 text-sky-700 border-sky-200',              // 스카이블루
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
            <div className="flex items-center gap-2">
              <span className={`${getCategoryColor(stat.stat_field || '기타')} border px-3 py-1 rounded-md text-xs font-medium flex items-center gap-1.5`}>
                <TagIcon className="w-3.5 h-3.5" />
                {stat.stat_field || '기타'}
              </span>
              {isCollected ? (
                <span className="bg-green-50 text-green-700 px-3 py-1 rounded-md text-xs font-medium flex items-center gap-1.5 border border-green-200">
                  <CheckCircleIcon className="w-3.5 h-3.5" />
                  수집됨
                </span>
              ) : (
                <span className="bg-gray-50 text-gray-600 px-3 py-1 rounded-md text-xs font-medium flex items-center gap-1.5 border border-gray-200">
                  <CheckCircleIcon className="w-3.5 h-3.5" />
                  수집안됨
                </span>
              )}
            </div>
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