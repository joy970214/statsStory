import React from 'react';
import { StoryResponse, StatItem } from '../services/api';

interface StoryViewerProps {
  story: StoryResponse;
  selectedStat: StatItem | null;
  onBack: () => void;
}

export const StoryViewer: React.FC<StoryViewerProps> = ({ story, selectedStat, onBack }) => {
  const downloadMarkdown = () => {
    const markdown = generateMarkdownContent(story);
    const blob = new Blob([markdown], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${story.title}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const generateMarkdownContent = (story: StoryResponse): string => {
    let markdown = `# ${story.title}\n\n`;
    markdown += `> ${story.summary}\n\n`;
    markdown += `**생성일시**: ${new Date(story.generated_at).toLocaleString('ko-KR')}\n\n`;
    markdown += `---\n\n`;

    story.sections.forEach((section, index) => {
      markdown += `## 📱 카드 ${index + 1}: ${section.title}\n\n`;
      markdown += `${section.content}\n\n`;
      
      if (section.chart_data) {
        markdown += `### 차트 데이터\n`;
        markdown += `\`\`\`json\n${JSON.stringify(section.chart_data, null, 2)}\n\`\`\`\n\n`;
      }
      
      markdown += `---\n\n`;
    });

    return markdown;
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      {/* 헤더 */}
      <div className="flex justify-between items-center mb-8">
        <button
          onClick={onBack}
          className="flex items-center text-blue-600 hover:text-blue-800 transition-colors"
        >
          ← 목록으로 돌아가기
        </button>
        
        <div className="flex gap-2">
          {selectedStat?.url && (
            <button
              onClick={() => window.open(selectedStat.url, '_blank', 'noopener,noreferrer')}
              className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
              title="통계누리에서 원본 데이터 확인"
            >
              📊 통계표 확인하기
            </button>
          )}
          <button
            onClick={downloadMarkdown}
            className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 transition-colors"
          >
            📄 다운로드
          </button>
          <button
            onClick={() => navigator.share && navigator.share({
              title: story.title,
              text: story.summary,
            })}
            className="bg-gray-600 text-white px-4 py-2 rounded-md hover:bg-gray-700 transition-colors"
          >
            🔗 공유하기
          </button>
        </div>
      </div>

      {/* 제목 및 요약 */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 text-white p-8 rounded-lg mb-8">
        <h1 className="text-3xl font-bold mb-4">{story.title}</h1>
        <p className="text-blue-100 text-lg">{story.summary}</p>
        <p className="text-blue-200 text-sm mt-4">
          생성일시: {new Date(story.generated_at).toLocaleString('ko-KR')}
        </p>
      </div>

      {/* 카드뉴스 섹션들 */}
      <div className="space-y-8">
        {story.sections.map((section, index) => (
          <div key={index} className="bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden">
            <div className="bg-gray-50 px-6 py-4 border-b">
              <div className="flex items-center">
                <span className="bg-blue-600 text-white text-sm font-bold px-3 py-1 rounded-full mr-3">
                  {index + 1}
                </span>
                <h2 className="text-xl font-semibold text-gray-900">{section.title}</h2>
              </div>
            </div>
            
            <div className="p-6">
              <div 
                className="prose max-w-none text-gray-700"
                dangerouslySetInnerHTML={{ 
                  __html: section.content.replace(/\n/g, '<br>') 
                }}
              />
              
              {section.chart_data && (
                <div className="mt-6 p-4 bg-gray-50 rounded-md">
                  <h4 className="text-sm font-semibold text-gray-600 mb-2">차트 데이터</h4>
                  <pre className="text-xs text-gray-600 overflow-x-auto">
                    {JSON.stringify(section.chart_data, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* 메타정보 */}
      <div className="mt-12 bg-gray-50 rounded-lg p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">📋 통계 정보</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <span className="font-medium text-gray-600">작성목적:</span>
            <p className="text-gray-800 mt-1">{story.metadata.purpose || 'N/A'}</p>
          </div>
          <div>
            <span className="font-medium text-gray-600">작성주기:</span>
            <p className="text-gray-800 mt-1">{story.metadata.frequency || 'N/A'}</p>
          </div>
          <div>
            <span className="font-medium text-gray-600">담당부서:</span>
            <p className="text-gray-800 mt-1">{story.metadata.department || 'N/A'}</p>
          </div>
          <div>
            <span className="font-medium text-gray-600">키워드:</span>
            <p className="text-gray-800 mt-1">
              {story.metadata.keywords.length > 0 ? story.metadata.keywords.join(', ') : 'N/A'}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};