import React from 'react';

interface LoadingSpinnerProps {
  message?: string;
  fullScreen?: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  message = "로딩 중...",
  fullScreen = false
}) => {
  if (fullScreen) {
    return (
      <div className="fixed inset-0 bg-white/80 z-50 flex items-center justify-center">
        <div className="text-center">
          <div className="inline-block w-16 h-16 border-4 border-gray-200 border-t-primary-600 rounded-full animate-spin mb-4"></div>
          <h3 className="text-lg font-semibold text-gray-800 mb-2">로딩 중</h3>
          <p className="text-gray-600">{message}</p>
        </div>
      </div>
    );
  }

  // 인라인 로딩
  return (
    <div className="flex flex-col items-center justify-center p-8">
      <div className="inline-block w-16 h-16 border-4 border-gray-200 border-t-primary-600 rounded-full animate-spin mb-4"></div>
      <p className="text-gray-600">{message}</p>
    </div>
  );
};