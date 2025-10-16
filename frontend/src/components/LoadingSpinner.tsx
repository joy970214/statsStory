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
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-50/95 backdrop-blur-sm">
        <div className="bg-white rounded-lg shadow-md border border-gray-200 p-8">
          <div className="text-center">
            <div className="inline-block w-12 h-12 border-4 border-primary-100 border-t-primary-600 rounded-full animate-spin"></div>
            <p className="mt-4 text-gray-900">{message}</p>
          </div>
        </div>
      </div>
    );
  }

  // 인라인 로딩
  return (
    <div className="flex flex-col items-center justify-center p-8">
      <div className="inline-block w-12 h-12 border-4 border-primary-100 border-t-primary-600 rounded-full animate-spin"></div>
      <p className="mt-4 text-gray-900">{message}</p>
    </div>
  );
};