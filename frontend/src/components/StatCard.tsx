import React from 'react';
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

  return (
    <div className="bg-white rounded-xl shadow-lg hover:shadow-2xl transition-all duration-300 border border-gray-100 hover:border-primary-200 group">
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-3 line-clamp-2 group-hover:text-primary-700 transition-colors duration-200">
          {stat.title}
        </h3>
        
        <div className="text-sm text-gray-600 mb-4">
          <div className="flex justify-between items-center mb-3">
            <span className="bg-gradient-to-r from-primary-100 to-primary-200 text-primary-800 px-3 py-1.5 rounded-full text-xs font-medium flex items-center gap-1">
              <TagIcon className="w-3 h-3" />
              {stat.stat_field || '기타'}
            </span>
            <span className="text-gray-500 flex items-center gap-1">
              <CalendarIcon className="w-3 h-3" />
              {stat.publish_date}
            </span>
          </div>
        </div>
        
        <div className="flex gap-3 mt-6">
          <button
            className={`flex-1 py-3 px-4 rounded-lg transition-all duration-200 flex items-center justify-center gap-2 font-medium ${
              disabled
                ? 'bg-gray-400 text-gray-600 cursor-not-allowed'
                : 'bg-gradient-to-r from-primary-500 to-primary-600 text-white hover:from-primary-600 hover:to-primary-700 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5'
            }`}
            onClick={() => !disabled && onSelect(stat)}
            disabled={disabled}
          >
            <MagnifyingGlassIcon className="w-4 h-4" />
            {disabled ? '취소 중...' : '분석하기'}
          </button>

          {stat.url && (
            <button
              className="bg-gradient-to-r from-secondary-500 to-secondary-600 text-white py-3 px-4 rounded-lg hover:from-secondary-600 hover:to-secondary-700 transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 flex items-center gap-2"
              onClick={(e) => {
                e.stopPropagation();
                window.open(stat.url, '_blank', 'noopener,noreferrer');
              }}
              title="통계누리에서 원본 데이터 확인"
            >
              <ChartBarIcon className="w-4 h-4" />
              원본보기
            </button>
          )}
        </div>
      </div>
    </div>
  );
};