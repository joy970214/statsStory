import React, { useState } from 'react';

interface CardData {
  card_number: number;
  title: string;
  main_text: string;
  key_figure: string;
  sub_text: string;
  visual_suggestion: string;
  hashtags: string[];
}

interface AnalysisData {
  stat_name: string;
  generation_date: string;
  cardnews: {
    cards?: CardData[];
    sections?: any[];
    raw_response?: string;
    status: string;
    error?: string;
  };
}

interface AdvancedCardNewsViewerProps {
  analysisData: AnalysisData;
  onBack: () => void;
}

export const AdvancedCardNewsViewer: React.FC<AdvancedCardNewsViewerProps> = ({ 
  analysisData, 
  onBack 
}) => {
  const [currentCard, setCurrentCard] = useState(0);
  const [viewMode, setViewMode] = useState<'cards' | 'grid'>('cards');

  const cards = analysisData.cardnews.cards || [];
  const hasCards = cards.length > 0;

  const downloadCardNews = () => {
    const content = generateCardNewsContent();
    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${analysisData.stat_name}_카드뉴스.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const generateCardNewsContent = () => {
    let content = `# ${analysisData.stat_name} 카드뉴스\n\n`;
    content += `생성일: ${new Date(analysisData.generation_date).toLocaleDateString('ko-KR')}\n\n`;
    
    if (hasCards) {
      cards.forEach((card, index) => {
        content += `## 📱 카드 ${card.card_number}: ${card.title}\n\n`;
        content += `**핵심 메시지**\n${card.main_text}\n\n`;
        content += `**주요 수치**: ${card.key_figure}\n\n`;
        content += `**보조 설명**\n${card.sub_text}\n\n`;
        content += `**시각화 제안**: ${card.visual_suggestion}\n\n`;
        content += `**해시태그**: ${card.hashtags.join(' ')}\n\n`;
        content += `---\n\n`;
      });
    } else {
      content += `## 원본 응답\n\n${analysisData.cardnews.raw_response || '데이터 없음'}\n\n`;
    }
    
    return content;
  };

  const nextCard = () => {
    setCurrentCard((prev) => (prev + 1) % cards.length);
  };

  const prevCard = () => {
    setCurrentCard((prev) => (prev - 1 + cards.length) % cards.length);
  };

  if (analysisData.cardnews.status === 'error') {
    return (
      <div className="max-w-4xl mx-auto p-6">
        <div className="flex justify-between items-center mb-8">
          <button
            onClick={onBack}
            className="flex items-center text-blue-600 hover:text-blue-800 transition-colors"
          >
            ← 목록으로 돌아가기
          </button>
        </div>
        
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-red-800 mb-2">오류 발생</h2>
          <p className="text-red-600">{analysisData.cardnews.error || '카드뉴스 생성 중 오류가 발생했습니다.'}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* 헤더 */}
      <div className="flex justify-between items-center mb-8">
        <button
          onClick={onBack}
          className="flex items-center text-blue-600 hover:text-blue-800 transition-colors"
        >
          ← 목록으로 돌아가기
        </button>
        
        <div className="flex gap-2">
          <button
            onClick={() => setViewMode(viewMode === 'cards' ? 'grid' : 'cards')}
            className="bg-blue-600 text-white px-4 py-2 rounded-md hover:bg-blue-700 transition-colors"
          >
            {viewMode === 'cards' ? '📊 전체보기' : '📱 카드보기'}
          </button>
          <button
            onClick={downloadCardNews}
            className="bg-green-600 text-white px-4 py-2 rounded-md hover:bg-green-700 transition-colors"
          >
            📄 다운로드
          </button>
        </div>
      </div>

      {/* 제목 */}
      <div className="bg-gradient-to-r from-purple-600 to-purple-800 text-white p-8 rounded-lg mb-8">
        <h1 className="text-3xl font-bold mb-4">📱 {analysisData.stat_name} 카드뉴스</h1>
        <p className="text-purple-100 text-lg">전문적이면서도 이해하기 쉬운 7장의 카드뉴스</p>
        <p className="text-purple-200 text-sm mt-4">
          생성일시: {new Date(analysisData.generation_date).toLocaleString('ko-KR')}
        </p>
      </div>

      {hasCards ? (
        viewMode === 'cards' ? (
          // 카드 뷰 모드
          <div className="relative">
            <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden max-w-lg mx-auto">
              {/* 카드 헤더 */}
              <div className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-6 py-4">
                <div className="flex justify-between items-center">
                  <span className="text-sm font-bold">카드 {cards[currentCard].card_number}</span>
                  <span className="text-xs opacity-80">{currentCard + 1} / {cards.length}</span>
                </div>
                <h2 className="text-xl font-bold mt-2">{cards[currentCard].title}</h2>
              </div>

              {/* 카드 내용 */}
              <div className="p-6">
                {/* 핵심 수치 */}
                <div className="text-center mb-6">
                  <div className="text-4xl font-bold text-purple-600 mb-2">
                    {cards[currentCard].key_figure}
                  </div>
                </div>

                {/* 메인 텍스트 */}
                <div className="text-gray-800 text-lg leading-relaxed mb-4">
                  {cards[currentCard].main_text.split('\n').map((line, i) => (
                    <p key={i} className="mb-2">{line}</p>
                  ))}
                </div>

                {/* 보조 설명 */}
                <div className="text-gray-600 text-sm mb-4">
                  {cards[currentCard].sub_text.split('\n').map((line, i) => (
                    <p key={i} className="mb-1">{line}</p>
                  ))}
                </div>

                {/* 해시태그 */}
                <div className="flex flex-wrap gap-2 mb-4">
                  {cards[currentCard].hashtags.map((tag, i) => (
                    <span 
                      key={i} 
                      className="text-purple-600 text-sm font-medium"
                    >
                      {tag}
                    </span>
                  ))}
                </div>

                {/* 시각화 제안 */}
                <div className="bg-gray-50 rounded-lg p-3">
                  <h4 className="text-xs font-semibold text-gray-600 mb-1">시각화 제안</h4>
                  <p className="text-xs text-gray-600">{cards[currentCard].visual_suggestion}</p>
                </div>
              </div>
            </div>

            {/* 네비게이션 */}
            <div className="flex justify-center items-center mt-6 gap-4">
              <button
                onClick={prevCard}
                className="bg-white border border-gray-300 rounded-full p-3 shadow-md hover:bg-gray-50 transition-colors"
                disabled={cards.length <= 1}
              >
                ←
              </button>
              
              <div className="flex gap-1">
                {cards.map((_, i) => (
                  <button
                    key={i}
                    onClick={() => setCurrentCard(i)}
                    className={`w-3 h-3 rounded-full transition-colors ${
                      i === currentCard ? 'bg-purple-600' : 'bg-gray-300'
                    }`}
                  />
                ))}
              </div>
              
              <button
                onClick={nextCard}
                className="bg-white border border-gray-300 rounded-full p-3 shadow-md hover:bg-gray-50 transition-colors"
                disabled={cards.length <= 1}
              >
                →
              </button>
            </div>
          </div>
        ) : (
          // 그리드 뷰 모드
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {cards.map((card, index) => (
              <div key={index} className="bg-white rounded-lg shadow-lg border border-gray-200 overflow-hidden hover:shadow-xl transition-shadow">
                <div className="bg-gradient-to-r from-purple-500 to-pink-500 text-white px-4 py-3">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-bold">카드 {card.card_number}</span>
                  </div>
                  <h3 className="text-lg font-bold mt-1">{card.title}</h3>
                </div>
                
                <div className="p-4">
                  <div className="text-center mb-4">
                    <div className="text-2xl font-bold text-purple-600">
                      {card.key_figure}
                    </div>
                  </div>
                  
                  <div className="text-gray-800 text-sm mb-3">
                    {card.main_text.slice(0, 100)}...
                  </div>
                  
                  <div className="flex flex-wrap gap-1">
                    {card.hashtags.slice(0, 3).map((tag, i) => (
                      <span key={i} className="text-purple-600 text-xs">
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        // 원본 응답 표시
        <div className="bg-white rounded-lg shadow-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">생성된 카드뉴스 내용</h3>
          <div className="prose max-w-none">
            <pre className="whitespace-pre-wrap text-sm text-gray-700">
              {analysisData.cardnews.raw_response || '내용이 없습니다.'}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};