import axios from 'axios';

const API_BASE_URL = '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5분으로 증가 (최적화된 크롤링용)
});

export interface StatItem {
  id: string;
  title: string;
  publish_date: string;
  category?: string;
  department?: string;
  url?: string;
  stat_field?: string;
}

export interface RecentStatsResponse {
  stats: StatItem[];
  total_count: number;
}

export interface StatMetadata {
  id: string;
  title: string;
  purpose?: string;
  frequency?: string;
  department?: string;
  contact?: string;
  keywords: string[];
  related_terms: Record<string, string>;
  url?: string;
  search_field?: string;
  responsible_department?: string;
  statistical_info?: Record<string, string>;
  major_items?: Record<string, string>;
  meaning_analysis?: Record<string, string>;
  terminology?: Record<string, string>;
}

export interface CardNewsSection {
  title: string;
  content: string;
  chart_data?: any;
}

export interface StoryResponse {
  title: string;
  summary: string;
  sections: CardNewsSection[];
  metadata: StatMetadata;
  generated_at: string;
}

export interface GenerateStoryRequest {
  stat_name: string;
  stat_url?: string;
  period?: string;
}



// 기본 분석 응답 타입
export interface BasicAnalysisResponse {
  stat_name: string;
  analysis_date: string;
  metadata: StatMetadata;
  data_structure: {
    total_years: number;
    data_keys: string[];
    year_range: {
      start: number | null;
      end: number | null;
    };
  };
  basic_analysis: {
    data_structure: {
      description: string;
      total_years: number;
      data_fields: string[];
    };
    collection_summary: {
      status: string;
      metadata_quality: string;
      data_completeness: string;
    };
    data_interpretation: string;
  };
}

// 기본통계현황분석 응답 타입
export interface AdvancedCardNewsResponse {
  stat_name: string;
  analysis_date: string;
  analysis_type: string;
  metadata?: StatMetadata;
  basic_statistics: {
    mean: number;
    median: number;
    max: number;
    min: number;
    total: number;
    count: number;
  };
  analysis_summary: {
    analysis_period: string;
    total_data_points: number;
    analysis_focus: string;
  };
  raw_data?: Array<{
    table_name: string;
    year: number;
    data: Record<string, any>;
  }>;
  raw_data_by_table?: Record<string, Array<{
    table_name: string;
    year: number;
    data: Record<string, any>;
  }>>;
}

export const statsAPI = {
  // 최근 통계 목록 조회
  async getRecentStats(): Promise<RecentStatsResponse> {
    const response = await api.get<RecentStatsResponse>('/recent-stats');
    return response.data;
  },

  // 통계 메타데이터 조회
  async getStatMetadata(statId: string): Promise<StatMetadata> {
    const response = await api.get<StatMetadata>(`/stats/${statId}/metadata`);
    return response.data;
  },

  // 기본 분석 (메타데이터 및 데이터 정리)
  async generateStory(request: GenerateStoryRequest): Promise<BasicAnalysisResponse> {
    const response = await api.post<BasicAnalysisResponse>('/analyze-basic', request);
    return response.data;
  },


  // 고급 카드뉴스 생성 (기존 버전)
  async generateAdvancedCardNews(request: GenerateStoryRequest): Promise<AdvancedCardNewsResponse> {
    const response = await api.post<AdvancedCardNewsResponse>('/generate-advanced-cardnews', request);
    return response.data;
  },

  // 최적화된 분석 시작
  async startOptimizedAnalysis(request: GenerateStoryRequest): Promise<{task_id: string, message: string, stat_name: string, estimated_time: string}> {
    const response = await api.post('/start-analysis', request);
    return response.data;
  },

  // 분석 상태 조회
  async getAnalysisStatus(taskId: string): Promise<{task_id: string, completed: boolean, progress: number, stage: string, message: string}> {
    const response = await api.get(`/analysis/status/${taskId}`);
    return response.data;
  },

  // 분석 결과 조회
  async getAnalysisResult(taskId: string): Promise<any> {
    const response = await api.get(`/analysis/result/${taskId}`);
    return response.data;
  },

  // 분석 작업 취소
  async cancelAnalysis(taskId: string): Promise<{message: string}> {
    const response = await api.delete(`/analysis/cancel/${taskId}`);
    return response.data;
  },

  // SSE 진행률 스트림 구독
  subscribeToProgress(taskId: string, onProgress: (data: any) => void): EventSource {
    // 프록시를 우회하고 직접 백엔드로 연결 시도
    const sseUrl = `http://localhost:8001/api/analysis/progress/${taskId}`;
    console.log('[API] SSE 연결 시작 (직접 연결):', sseUrl);
    console.log('[API] 현재 위치:', window.location.href);
    
    // 먼저 엔드포인트가 존재하는지 확인
    const statusUrl = sseUrl.replace('/progress/', '/status/');
    fetch(statusUrl)
      .then(response => {
        console.log('[API] 상태 확인 응답:', response.status, response.statusText);
      })
      .catch(error => {
        console.error('[API] 상태 확인 실패:', error);
      });
    
    const eventSource = new EventSource(sseUrl);
    
    // 연결 시작 로그
    console.log('[API] EventSource 생성됨, 초기 readyState:', eventSource.readyState);
    
    eventSource.onopen = (event) => {
      console.log('[API] SSE 연결 성공!', event);
      console.log('[API] EventSource readyState:', eventSource.readyState);
      console.log('[API] EventSource URL:', eventSource.url);
    };
    
    eventSource.onmessage = (event) => {
      console.log('[API] SSE 메시지 수신 - Raw:', event.data);
      console.log('[API] SSE 메시지 이벤트 전체:', event);
      try {
        const data = JSON.parse(event.data);
        console.log('[API] SSE 메시지 파싱 완료:', data);
        onProgress(data);
      } catch (error) {
        console.error('[API] SSE 데이터 파싱 오류:', error, 'Raw data:', event.data);
      }
    };

    eventSource.onerror = (error) => {
      console.error('[API] SSE 연결 오류:', error);
      console.log('[API] EventSource readyState:', eventSource.readyState);
      console.log('[API] EventSource url:', eventSource.url);
      
      // 연결 상태별 자세한 로그
      switch(eventSource.readyState) {
        case EventSource.CONNECTING:
          console.log('[API] SSE 연결 중... (재연결 시도 중일 수 있음)');
          break;
        case EventSource.OPEN:
          console.log('[API] SSE 연결 열림 (오류에도 불구하고)');
          break;
        case EventSource.CLOSED:
          console.log('[API] SSE 연결 닫힘 (서버에서 연결 종료 또는 네트워크 오류)');
          break;
        default:
          console.log('[API] SSE 알 수 없는 상태:', eventSource.readyState);
      }
    };

    // 5초 후 연결 상태 체크
    setTimeout(() => {
      console.log('[API] 5초 후 SSE 상태 체크:');
      console.log('  - readyState:', eventSource.readyState);
      console.log('  - url:', eventSource.url);
    }, 5000);

    return eventSource;
  },

  // 데이터 검사 및 탐색
  async inspectData(request: GenerateStoryRequest): Promise<any> {
    const response = await api.post<any>('/data/inspect', request);
    return response.data;
  },

  async viewRawData(request: GenerateStoryRequest): Promise<any> {
    const response = await api.post<any>('/data/raw-view', request);
    return response.data;
  },

  async getDataSummary(request: GenerateStoryRequest): Promise<any> {
    const response = await api.post<any>('/data/summary', request);
    return response.data;
  },

  async exploreDataByYear(year: number, request: GenerateStoryRequest): Promise<any> {
    const response = await api.post<any>(`/data/explore-by-year/${year}`, request);
    return response.data;
  },

  async getCollectionLog(request: GenerateStoryRequest): Promise<any> {
    const response = await api.post<any>('/data/collection-log', request);
    return response.data;
  },

  // 통계표별 상세 분석
  async getTableAnalysis(statName: string): Promise<any> {
    const response = await api.get(`/table-analysis/${encodeURIComponent(statName)}`);
    return response.data;
  },
};