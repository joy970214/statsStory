import React from 'react';
import { StatItem } from '../services/api';

interface StatCardProps {
  stat: StatItem;
  onSelect: (stat: StatItem) => void;
}

export const StatCard: React.FC<StatCardProps> = ({ stat, onSelect }) => {

  return (
    <div className="bg-white rounded-lg shadow-md hover:shadow-lg transition-shadow border border-gray-200">
      <div className="p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">
          {stat.title}
        </h3>
        
        <div className="text-sm text-gray-600 mb-3">
          <div className="flex justify-between items-center mb-2">
            <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded-full text-xs">
              {stat.stat_field || '기타'}
            </span>
            <span className="text-gray-500">{stat.publish_date}</span>
          </div>
        </div>
        
        <div className="flex gap-2 mt-4">
          <button
            className="flex-1 bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 transition-colors"
            onClick={() => onSelect(stat)}
          >
            🔍 분석하기
          </button>

          {stat.url && (
            <button
              className="bg-green-600 text-white py-2 px-4 rounded-md hover:bg-green-700 transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                window.open(stat.url, '_blank', 'noopener,noreferrer');
              }}
              title="통계누리에서 원본 데이터 확인"
            >
              📊 원본보기
            </button>
          )}
        </div>
      </div>
    </div>
  );
};