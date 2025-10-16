// 파일 다운로드 관련 유틸리티 함수들

/**
 * 텍스트 내용을 파일로 다운로드
 */
export const downloadTextFile = (content: string, filename: string, mimeType: string = 'text/plain') => {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
};

/**
 * 마크다운 파일 다운로드
 */
export const downloadMarkdown = (content: string, filename: string) => {
  const mdFilename = filename.endsWith('.md') ? filename : `${filename}.md`;
  downloadTextFile(content, mdFilename, 'text/markdown');
};

/**
 * HTML을 PDF로 변환하여 다운로드 (html2pdf.js 사용)
 */
export const downloadPDF = async (element: HTMLElement, filename: string) => {
  try {
    // html2pdf 라이브러리를 동적으로 로드
    const html2pdf = (window as any).html2pdf || await loadHtml2PdfScript();
    
    if (!html2pdf) {
      throw new Error('html2pdf 라이브러리를 로드할 수 없습니다.');
    }
    
    const pdfFilename = filename.endsWith('.pdf') ? filename : `${filename}.pdf`;
    
    const opt = {
      margin: 0.1,
      filename: pdfFilename,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { scale: 2, useCORS: true },
      jsPDF: { unit: 'in', format: 'a4', orientation: 'portrait' }
    };

    await html2pdf().set(opt).from(element).save();
  } catch (error) {
    console.error('PDF 다운로드 실패:', error);
    // Fallback: window.print() 사용
    fallbackToPrint(element, filename);
  }
};

/**
 * html2pdf 스크립트를 동적으로 로드
 */
const loadHtml2PdfScript = (): Promise<any> => {
  return new Promise((resolve, reject) => {
    if ((window as any).html2pdf) {
      resolve((window as any).html2pdf);
      return;
    }

    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js';
    script.onload = () => {
      resolve((window as any).html2pdf);
    };
    script.onerror = () => {
      reject(new Error('html2pdf 스크립트 로드 실패'));
    };
    document.head.appendChild(script);
  });
};

/**
 * 브라우저 프린트 기능으로 폴백
 */
const fallbackToPrint = (element: HTMLElement, filename: string) => {
  const printWindow = window.open('', '_blank');
  if (printWindow) {
    printWindow.document.write(`
      <html>
        <head>
          <title>${filename}</title>
          <style>
            body {
              font-family: 'Malgun Gothic', Arial, sans-serif;
              margin: 5px;
              font-size: 12px;
              line-height: 1.5;
            }
            .page-break { page-break-after: always; }
            h1, h2, h3 { color: #333; margin-top: 20px; }
            .bg-blue-50, .bg-green-50, .bg-purple-50, .bg-pink-50, .bg-gray-50 { 
              background-color: #f8f9fa !important; 
              border: 1px solid #dee2e6;
              padding: 10px;
              margin: 10px 0;
            }
            @media print {
              body {
                font-size: 10px;
                margin: 2px !important;
              }
              .hidden { display: none; }
            }
          </style>
        </head>
        <body>
          ${element.innerHTML}
        </body>
      </html>
    `);
    printWindow.document.close();
    
    // 약간의 지연 후 프린트 실행
    setTimeout(() => {
      printWindow.print();
      printWindow.close();
    }, 500);
  } else {
    alert('팝업이 차단되어 PDF 다운로드를 할 수 없습니다. 팝업을 허용해주세요.');
  }
};

/**
 * 원본 URL 열기
 */
export const openOriginalUrl = (url: string) => {
  if (url) {
    window.open(url, '_blank', 'noopener,noreferrer');
  } else {
    alert('원본 URL이 없습니다.');
  }
};

/**
 * 분석 데이터를 마크다운 형식으로 변환
 */
export const generateBasicAnalysisMarkdown = (analysisData: any): string => {
  const date = new Date(analysisData.analysis_date).toLocaleString('ko-KR');
  
  return `# 📊 기본 분석 결과

## 개요
- **통계명**: ${analysisData.stat_name}
- **분석일시**: ${date}
- **수집방법**: ${analysisData.collection_method || 'MCP 강화 크롤링'}

## 📋 메타데이터 정보

### 기본 정보
- **제목**: ${analysisData.metadata.title}
- **목적**: ${analysisData.metadata.purpose || '정보 없음'}
- **주기**: ${analysisData.metadata.frequency || '정보 없음'}
- **담당부서**: ${analysisData.metadata.department || '정보 없음'}

### 키워드
${analysisData.metadata.keywords.map((keyword: string) => `- ${keyword}`).join('\n')}

## 🔍 데이터 구조 분석

- **수집된 연도**: ${analysisData.data_structure.total_years}개
- **데이터 필드**: ${analysisData.data_structure.data_keys.length}개
- **데이터 범위**: ${analysisData.data_structure.year_range.start} - ${analysisData.data_structure.year_range.end}

### 수집된 데이터 필드
${analysisData.data_structure.data_keys.map((key: string) => `- ${key}`).join('\n')}

## 📈 수집 현황 요약

- **수집 상태**: ${analysisData.basic_analysis.collection_summary.status}
- **메타데이터 품질**: ${analysisData.basic_analysis.collection_summary.metadata_quality}
- **데이터 완성도**: ${analysisData.basic_analysis.collection_summary.data_completeness}

## 💡 데이터 해석

${analysisData.basic_analysis.data_interpretation}

---
*이 보고서는 statsStory 시스템에서 자동 생성되었습니다.*
`;
};

/**
 * 기본통계현황분석 데이터를 마크다운 형식으로 변환
 */
export const generateBasicStatisticsMarkdown = (analysisData: any): string => {
  const date = new Date(analysisData.analysis_date).toLocaleString('ko-KR');
  const stats = analysisData.basic_statistics;
  
  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 2 }).format(num);
  };
  
  return `# 📈 기본통계현황분석 결과

## 개요
- **통계명**: ${analysisData.stat_name}
- **분석일시**: ${date}
- **분석유형**: ${analysisData.analysis_type}

## 📊 분석 개요

- **분석 기간**: ${analysisData.analysis_summary.analysis_period}
- **총 데이터 포인트**: ${analysisData.analysis_summary.total_data_points}개
- **분석 초점**: ${analysisData.analysis_summary.analysis_focus}

## 🔢 기초통계 지표

| 지표 | 값 | 설명 |
|------|----|----- |
| **평균값 (Mean)** | ${formatNumber(stats.mean)} | 전체 데이터의 중심 경향 |
| **중위수 (Median)** | ${formatNumber(stats.median)} | 데이터의 중앙값 |
| **최댓값 (Maximum)** | ${formatNumber(stats.max)} | 가장 높은 수치 |
| **최솟값 (Minimum)** | ${formatNumber(stats.min)} | 가장 낮은 수치 |
| **총합계 (Total)** | ${formatNumber(stats.total)} | 전체 규모 |
| **데이터 개수 (Count)** | ${stats.count} | 총 데이터 수 |

## 📊 데이터 분포 특성

### 중심경향 분석
- **평균값**: ${formatNumber(stats.mean)}
- **중위수**: ${formatNumber(stats.median)}
- **평균과 중위수 차이**: ${formatNumber(Math.abs(stats.mean - stats.median))}

### 변동성 분석
- **최댓값**: ${formatNumber(stats.max)}
- **최솟값**: ${formatNumber(stats.min)}
- **범위 (Range)**: ${formatNumber(stats.max - stats.min)}

### 규모 분석
- **총 데이터 수**: ${stats.count}개
- **총합계**: ${formatNumber(stats.total)}
- **데이터 당 평균**: ${formatNumber(stats.total / stats.count)}

## 💡 객관적 현황 요약

### 🎯 핵심 수치
- 가장 높은 수치: **${formatNumber(stats.max)}**
- 가장 낮은 수치: **${formatNumber(stats.min)}**
- 전체 평균: **${formatNumber(stats.mean)}**
- 중앙값: **${formatNumber(stats.median)}**

### 📈 데이터 현황
- 분석 기간: **${analysisData.analysis_summary.analysis_period}**
- 총 데이터 수: **${stats.count}개**
- 전체 규모: **${formatNumber(stats.total)}**
- 분석 유형: **기본통계현황분석**

### 📋 분석 특징
주관적 해석을 배제하고 수집된 데이터의 객관적 사실만을 바탕으로 한 기술통계 분석 결과입니다.
기초통계 지표를 통해 현황을 파악하고 데이터 분포 특성을 확인할 수 있습니다.

---
*이 보고서는 statsStory 시스템에서 자동 생성되었습니다.*
`;
};

/**
 * 종합분석 데이터를 마크다운 형식으로 변환
 */
export const generateComprehensiveAnalysisMarkdown = (analysisData: any): string => {
  const date = new Date(analysisData.analysis_date).toLocaleString('ko-KR');
  
  return `# 📊 종합분석 결과

## 개요
- **통계명**: ${analysisData.stat_name}
- **분석일시**: ${date}

## 📈 통계 분석
${analysisData.analysis.statistics_analysis.status === 'success' ? 
  analysisData.analysis.statistics_analysis.analysis_result : 
  `분석 실패: ${analysisData.analysis.statistics_analysis.error || '알 수 없는 오류'}`}

## 📊 트렌드 분석
${analysisData.analysis.trend_analysis.status === 'success' ? 
  analysisData.analysis.trend_analysis.trend_analysis : 
  `분석 실패: ${analysisData.analysis.trend_analysis.error || '알 수 없는 오류'}`}

## 🏛️ 정책 인사이트
${analysisData.analysis.policy_insights.status === 'success' ? 
  analysisData.analysis.policy_insights.policy_insights : 
  `분석 실패: ${analysisData.analysis.policy_insights.error || '알 수 없는 오류'}`}

## 📰 카드뉴스
${analysisData.analysis.card_news.status === 'success' ? 
  (analysisData.analysis.card_news.raw_response || '카드뉴스가 생성되었습니다.') : 
  `생성 실패: ${analysisData.analysis.card_news.error || '알 수 없는 오류'}`}

---
*분석 생성일시: ${new Date(analysisData.analysis.generated_at).toLocaleString('ko-KR')}*  
*이 보고서는 statsStory 시스템에서 자동 생성되었습니다.*
`;
};

/**
 * AI 분석 인사이트만 마크다운 형식으로 변환
 */
export const generateAIInsightsMarkdown = (analysisData: any): string => {
  const date = new Date(analysisData.analysis_date).toLocaleString('ko-KR');
  const aiInsights = analysisData.metadata?.ai_insights;
  
  if (!aiInsights || (aiInsights?.insights_count ?? 0) === 0) {
    return `# ✨ AI 분석 인사이트

## 개요
- **통계명**: ${analysisData.stat_name}
- **분석일시**: ${date}

## 인사이트 부재
AI 분석 인사이트가 아직 생성되지 않았습니다.
'분석하기' 버튼을 눌러 새로 분석하면 AI 인사이트가 자동 생성됩니다.

---
*이 보고서는 statsStory 시스템에서 자동 생성되었습니다.*
`;
  }
  
  let markdown = `# ✨ AI 분석 인사이트

## 개요
- **통계명**: ${analysisData.stat_name}
- **분석일시**: ${date}
- **총 인사이트 수**: ${aiInsights.insights_count}개

---

`;

  // 10개 카테고리 인사이트 추가
  for (let i = 1; i <= 10; i++) {
    const insightKey = `insight_${i}`;
    const insight = aiInsights[insightKey];
    
    if (insight) {
      markdown += `## ${i}. ${insight.category}

**내용:**
${insight.content}

**시각화 제안:** ${insight.visualization}

---

`;
    }
  }
  
  markdown += `
*이 AI 인사이트는 수집된 통계 데이터를 바탕으로 자동 생성되었습니다.*
*분석일시: ${date}*
`;
  
  return markdown;
};