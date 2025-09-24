import React from 'react';
import { motion } from 'framer-motion';
import { SparklesIcon } from '@heroicons/react/24/outline';

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
      <motion.div 
        className="fixed inset-0 z-50 flex items-center justify-center"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
      >
        {/* 백드롭 블러 */}
        <div className="absolute inset-0 bg-black/20 backdrop-blur-sm"></div>
        
        {/* 로딩 컨텐츠 */}
        <motion.div 
          className="relative bg-white/90 backdrop-blur-md rounded-2xl p-8 shadow-2xl border border-white/20"
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.3 }}
        >
          <div className="flex flex-col items-center space-y-4">
            {/* 메인 스피너 */}
            <div className="relative">
              <motion.div 
                className="w-16 h-16 rounded-full border-4 border-primary-200"
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
              />
              <motion.div 
                className="absolute top-0 left-0 w-16 h-16 rounded-full border-4 border-transparent border-t-primary-600"
                animate={{ rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
              />
              {/* 중앙 아이콘 */}
              <motion.div 
                className="absolute inset-0 flex items-center justify-center"
                animate={{ 
                  scale: [1, 1.2, 1],
                  rotate: [0, 180, 360]
                }}
                transition={{ 
                  duration: 2, 
                  repeat: Infinity, 
                  ease: "easeInOut" 
                }}
              >
                <SparklesIcon className="w-6 h-6 text-primary-600" />
              </motion.div>
            </div>
            
            {/* 메시지 */}
            <motion.p 
              className="text-gray-700 font-medium text-lg"
              animate={{ opacity: [0.7, 1, 0.7] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              {message}
            </motion.p>
            
            {/* 점 애니메이션 */}
            <div className="flex space-x-1">
              {[0, 1, 2].map((i) => (
                <motion.div
                  key={i}
                  className="w-2 h-2 bg-primary-600 rounded-full"
                  animate={{
                    scale: [1, 1.5, 1],
                    opacity: [0.5, 1, 0.5]
                  }}
                  transition={{
                    duration: 1.5,
                    repeat: Infinity,
                    delay: i * 0.2
                  }}
                />
              ))}
            </div>
          </div>
        </motion.div>
      </motion.div>
    );
  }

  // 기존 인라인 로딩 (콘텐츠 영역 내)
  return (
    <motion.div 
      className="flex flex-col items-center justify-center p-8"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="relative">
        <motion.div 
          className="w-12 h-12 rounded-full border-4 border-primary-200"
          animate={{ rotate: 360 }}
          transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
        />
        <motion.div 
          className="absolute top-0 left-0 w-12 h-12 rounded-full border-4 border-transparent border-t-primary-600"
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
        />
        <motion.div 
          className="absolute inset-0 flex items-center justify-center"
          animate={{ 
            scale: [1, 1.1, 1],
          }}
          transition={{ 
            duration: 1.5, 
            repeat: Infinity, 
            ease: "easeInOut" 
          }}
        >
          <SparklesIcon className="w-4 h-4 text-primary-600" />
        </motion.div>
      </div>
      <motion.p 
        className="mt-4 text-gray-600 font-medium"
        animate={{ opacity: [0.7, 1, 0.7] }}
        transition={{ duration: 2, repeat: Infinity }}
      >
        {message}
      </motion.p>
    </motion.div>
  );
};