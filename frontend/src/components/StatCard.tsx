import React, { useState } from 'react';
import { StatItem } from '../services/api';

interface StatCardProps {
  stat: StatItem;
  onSelect: (stat: StatItem, type: 'comprehensive' | 'advanced-cardnews') => void;
}

export const StatCard: React.FC<StatCardProps> = ({ stat, onSelect }) => {
  const [showOptions, setShowOptions] = useState(false);

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
        
        {!showOptions ? (
          <div className="flex gap-2 mt-4">
            <button 
              className="flex-1 bg-purple-600 text-white py-2 px-4 rounded-md hover:bg-purple-700 transition-colors"
              onClick={() => setShowOptions(true)}
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
        ) : (
          <div className="space-y-2 mt-4">
            <h4 className="text-sm font-medium text-gray-700 mb-3">분석 유형을 선택하세요:</h4>
            
            {/* 기본통계현황분석 (최적화됨) */}
            <button 
              className="w-full bg-blue-600 text-white py-3 px-4 rounded-md hover:bg-blue-700 transition-colors text-left"
              onClick={() => onSelect(stat, 'advanced-cardnews')}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">📊 기본통계현황분석</div>
                  <div className="text-sm opacity-90">메타데이터, 데이터정리, 기초통계 지표 계산 (실시간 진행률)</div>
                </div>
                <div className="text-xs bg-blue-500 px-2 py-1 rounded">추천</div>
              </div>
            </button>

            {/* 종합 분석 (최적화됨) */}
            <button 
              className="w-full bg-indigo-600 text-white py-3 px-4 rounded-md hover:bg-indigo-700 transition-colors text-left"
              onClick={() => onSelect(stat, 'comprehensive')}
            >
              <div className="flex items-center justify-between">
                <div>
                  <div className="font-medium">🔍 종합 분석</div>
                  <div className="text-sm opacity-90">로컬 LLM 기반 고급 통계 분석 (실시간 진행률)</div>
                </div>
                <div className="text-xs bg-indigo-500 px-2 py-1 rounded">전문</div>
              </div>
            </button>

            {/* 취소 버튼 */}
            <button 
              className="w-full bg-gray-200 text-gray-700 py-2 px-4 rounded-md hover:bg-gray-300 transition-colors"
              onClick={() => setShowOptions(false)}
            >
              취소
            </button>
          </div>
        )}
      </div>
    </div>
  );
};