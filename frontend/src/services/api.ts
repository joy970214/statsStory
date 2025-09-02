import axios from 'axios';

const API_BASE_URL = 'http://localhost:8001/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2분으로 증가
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

// 종합 분석 응답 타입
export interface ComprehensiveAnalysisResponse {
  stat_name: string;
  analysis_date: string;
  metadata: StatMetadata;
  analysis: {
    statistics_analysis: {
      analysis_result: string;
      status: string;
      error?: string;
    };
    trend_analysis: {
      trend_analysis: string;
      status: string;
      error?: string;
    };
    policy_insights: {
      policy_insights: string;
      status: string;
      error?: string;
    };
    card_news: {
      cards?: any[];
      sections?: any[];
      raw_response?: string;
      status: string;
      error?: string;
    };
    generated_at: string;
  };
}

// 개별 분석 응답 타입
export interface StatisticsAnalysisResponse {
  stat_name: string;
  analysis_date: string;
  statistics_analysis: {
    analysis_result: string;
    status: string;
    error?: string;
  };
}

export interface TrendAnalysisResponse {
  stat_name: string;
  analysis_date: string;
  trend_analysis: {
    trend_analysis: string;
    status: string;
    error?: string;
  };
}

export interface PolicyInsightsResponse {
  stat_name: string;
  analysis_date: string;
  policy_insights: {
    policy_insights: string;
    status: string;
    error?: string;
  };
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

  // 종합 분석 (모든 분석 포함)
  async generateComprehensiveAnalysis(request: GenerateStoryRequest): Promise<ComprehensiveAnalysisResponse> {
    const response = await api.post<ComprehensiveAnalysisResponse>('/analyze-comprehensive', request);
    return response.data;
  },

  // 통계 분석만
  async generateStatisticsAnalysis(request: GenerateStoryRequest): Promise<StatisticsAnalysisResponse> {
    const response = await api.post<StatisticsAnalysisResponse>('/analyze-statistics', request);
    return response.data;
  },

  // 트렌드 분석만
  async generateTrendAnalysis(request: GenerateStoryRequest): Promise<TrendAnalysisResponse> {
    const response = await api.post<TrendAnalysisResponse>('/analyze-trends', request);
    return response.data;
  },

  // 정책 시사점만
  async generatePolicyInsights(request: GenerateStoryRequest): Promise<PolicyInsightsResponse> {
    const response = await api.post<PolicyInsightsResponse>('/generate-policy-insights', request);
    return response.data;
  },

  // 고급 카드뉴스 생성
  async generateAdvancedCardNews(request: GenerateStoryRequest): Promise<AdvancedCardNewsResponse> {
    const response = await api.post<AdvancedCardNewsResponse>('/generate-advanced-cardnews', request);
    return response.data;
  },
};