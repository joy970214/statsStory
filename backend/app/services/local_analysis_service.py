
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any
from app.models.stat_models import StatData, StatMetadata
import json
import re

class LocalAnalysisService:
    """AI API 없이 로컬에서 통계 분석을 수행하는 서비스"""
    
    def __init__(self):
        self.analysis_templates = {
            "trend": {
                "increasing": "증가 추세를 보이고 있습니다.",
                "decreasing": "감소 추세를 보이고 있습니다.",
                "stable": "안정적인 수준을 유지하고 있습니다.",
                "fluctuating": "변동성이 있는 패턴을 보이고 있습니다."
            },
            "seasonal": {
                "spring": "봄철에 증가하는 경향이 있습니다.",
                "summer": "여름철에 증가하는 경향이 있습니다.",
                "autumn": "가을철에 증가하는 경향이 있습니다.",
                "winter": "겨울철에 증가하는 경향이 있습니다."
            }
        }
    
    def analyze_basic_data(self, stat_data: List[StatData], metadata: StatMetadata) -> Dict[str, Any]:
        """기본 통계 데이터 분석"""
        try:
            if not stat_data:
                return self._get_empty_analysis()
            
            # 데이터를 pandas DataFrame으로 변환
            df = self._convert_to_dataframe(stat_data)
            
            # 기본 통계량 계산
            basic_stats = self._calculate_basic_statistics(df)
            
            # 트렌드 분석
            trend_analysis = self._analyze_trends(df)
            
            # 데이터 품질 평가
            data_quality = self._assess_data_quality(df)
            
            return {
                "data_structure": {
                    "description": f"{len(stat_data)}년간의 {metadata.title} 데이터",
                    "total_years": len(stat_data),
                    "data_fields": list(df.columns) if not df.empty else []
                },
                "collection_summary": {
                    "status": "완료",
                    "metadata_quality": data_quality["metadata_quality"],
                    "data_completeness": data_quality["completeness"]
                },
                "data_interpretation": self._generate_interpretation(basic_stats, trend_analysis, metadata),
                "basic_statistics": basic_stats,
                "trend_analysis": trend_analysis
            }
            
        except Exception as e:
            print(f"로컬 분석 오류: {e}")
            return self._get_empty_analysis()
    
    def generate_comprehensive_analysis(self, stat_data: List[StatData], metadata: StatMetadata) -> Dict[str, Any]:
        """종합 분석 생성"""
        try:
            # 기본 분석
            basic_analysis = self.analyze_basic_data(stat_data, metadata)
            
            # 통계 분석
            statistics_analysis = self._analyze_statistics(stat_data, metadata)
            
            # 트렌드 분석
            trend_analysis = self._analyze_trends_advanced(stat_data, metadata)
            
            # 정책 시사점
            policy_insights = self._generate_policy_insights(stat_data, metadata)
            
            # 카드뉴스 생성
            card_news = self._generate_simple_card_news(stat_data, metadata)
            
            return {
                "statistics_analysis": statistics_analysis,
                "trend_analysis": trend_analysis,
                "policy_insights": policy_insights,
                "card_news": card_news,
                "generated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"종합 분석 오류: {e}")
            return self._get_empty_comprehensive_analysis()
    
    def _convert_to_dataframe(self, stat_data: List[StatData]) -> pd.DataFrame:
        """StatData를 pandas DataFrame으로 변환"""
        data_list = []
        for stat in stat_data:
            if hasattr(stat, 'data') and isinstance(stat.data, dict):
                row_data = {'year': int(stat.year)}
                row_data.update(stat.data)
                data_list.append(row_data)
            else:
                # 기본 데이터 구조
                row_data = {
                    'year': int(stat.year),
                    'value': getattr(stat, 'value', 0),
                    'total': getattr(stat, 'total', 0)
                }
                data_list.append(row_data)
        
        return pd.DataFrame(data_list)
    
    def _calculate_basic_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """기본 통계량 계산"""
        try:
            # 수치형 컬럼 찾기
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            numeric_columns = [col for col in numeric_columns if col != 'year']
            
            if not numeric_columns:
                return {"error": "수치형 데이터가 없습니다."}
            
            # 첫 번째 수치형 컬럼 사용
            value_column = numeric_columns[0]
            values = df[value_column].dropna()
            
            if len(values) == 0:
                return {"error": "유효한 데이터가 없습니다."}
            
            return {
                "mean": float(values.mean()),
                "median": float(values.median()),
                "max": float(values.max()),
                "min": float(values.min()),
                "total": float(values.sum()),
                "count": int(len(values)),
                "std": float(values.std()),
                "variance": float(values.var())
            }
            
        except Exception as e:
            print(f"통계량 계산 오류: {e}")
            return {"error": f"통계량 계산 중 오류: {str(e)}"}
    
    def _analyze_trends(self, df: pd.DataFrame) -> Dict[str, Any]:
        """트렌드 분석"""
        try:
            if df.empty or len(df) < 2:
                return {"trend": "불명확", "description": "데이터가 부족합니다."}
            
            # 수치형 컬럼 찾기
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            numeric_columns = [col for col in numeric_columns if col != 'year']
            
            if not numeric_columns:
                return {"trend": "불명확", "description": "수치형 데이터가 없습니다."}
            
            value_column = numeric_columns[0]
            df_sorted = df.sort_values('year')
            
            # 선형 회귀로 트렌드 계산
            x = df_sorted['year'].values
            y = df_sorted[value_column].values
            
            if len(x) < 2:
                return {"trend": "불명확", "description": "데이터가 부족합니다."}
            
            # 간단한 선형 트렌드 계산
            slope = np.polyfit(x, y, 1)[0]
            
            if slope > 0:
                trend = "증가"
                description = f"연평균 {abs(slope):.2f} 증가"
            elif slope < 0:
                trend = "감소"
                description = f"연평균 {abs(slope):.2f} 감소"
            else:
                trend = "안정"
                description = "변화 없음"
            
            return {
                "trend": trend,
                "slope": float(slope),
                "description": description,
                "confidence": "높음" if len(x) >= 3 else "낮음"
            }
            
        except Exception as e:
            print(f"트렌드 분석 오류: {e}")
            return {"trend": "오류", "description": f"분석 중 오류: {str(e)}"}
    
    def _analyze_trends_advanced(self, stat_data: List[StatData], metadata: StatMetadata) -> Dict[str, Any]:
        """고급 트렌드 분석"""
        try:
            df = self._convert_to_dataframe(stat_data)
            basic_trend = self._analyze_trends(df)
            
            # 계절성 분석 (간단한 버전)
            seasonal_pattern = self._detect_seasonal_pattern(df)
            
            # 변동성 분석
            volatility = self._analyze_volatility(df)
            
            return {
                "trend_analysis": basic_trend["description"],
                "trend_direction": basic_trend["trend"],
                "seasonal_pattern": seasonal_pattern,
                "volatility": volatility,
                "status": "완료",
                "analysis_method": "로컬 통계 분석"
            }
            
        except Exception as e:
            print(f"고급 트렌드 분석 오류: {e}")
            return {
                "trend_analysis": "분석 중 오류가 발생했습니다.",
                "status": "오류",
                "error": str(e)
            }
    
    def _detect_seasonal_pattern(self, df: pd.DataFrame) -> str:
        """계절성 패턴 감지"""
        try:
            if df.empty or len(df) < 4:
                return "데이터 부족으로 계절성 분석 불가"
            
            # 간단한 계절성 감지 (연도별 변화율)
            df_sorted = df.sort_values('year')
            numeric_columns = df_sorted.select_dtypes(include=[np.number]).columns.tolist()
            numeric_columns = [col for col in numeric_columns if col != 'year']
            
            if not numeric_columns:
                return "수치형 데이터 없음"
            
            value_column = numeric_columns[0]
            values = df_sorted[value_column].dropna()
            
            if len(values) < 2:
                return "데이터 부족"
            
            # 연도별 변화율 계산
            changes = []
            for i in range(1, len(values)):
                if values.iloc[i-1] != 0:
                    change_rate = (values.iloc[i] - values.iloc[i-1]) / values.iloc[i-1] * 100
                    changes.append(change_rate)
            
            if not changes:
                return "변화율 계산 불가"
            
            avg_change = np.mean(changes)
            
            if abs(avg_change) < 5:
                return "안정적인 패턴"
            elif avg_change > 10:
                return "급격한 증가 패턴"
            elif avg_change < -10:
                return "급격한 감소 패턴"
            else:
                return "점진적 변화 패턴"
                
        except Exception as e:
            return f"계절성 분석 오류: {str(e)}"
    
    def _analyze_volatility(self, df: pd.DataFrame) -> str:
        """변동성 분석"""
        try:
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            numeric_columns = [col for col in numeric_columns if col != 'year']
            
            if not numeric_columns:
                return "수치형 데이터 없음"
            
            value_column = numeric_columns[0]
            values = df[value_column].dropna()
            
            if len(values) < 2:
                return "데이터 부족"
            
            cv = values.std() / values.mean() * 100  # 변동계수
            
            if cv < 10:
                return "낮은 변동성"
            elif cv < 30:
                return "보통 변동성"
            else:
                return "높은 변동성"
                
        except Exception as e:
            return f"변동성 분석 오류: {str(e)}"
    
    def _assess_data_quality(self, df: pd.DataFrame) -> Dict[str, str]:
        """데이터 품질 평가"""
        try:
            if df.empty:
                return {
                    "metadata_quality": "낮음",
                    "completeness": "낮음"
                }
            
            # 완성도 계산
            total_cells = len(df) * len(df.columns)
            non_null_cells = df.count().sum()
            completeness_rate = (non_null_cells / total_cells) * 100
            
            if completeness_rate >= 90:
                completeness = "높음"
            elif completeness_rate >= 70:
                completeness = "보통"
            else:
                completeness = "낮음"
            
            # 메타데이터 품질 (간단한 평가)
            metadata_quality = "보통"  # 기본값
            
            return {
                "metadata_quality": metadata_quality,
                "completeness": completeness,
                "completeness_rate": f"{completeness_rate:.1f}%"
            }
            
        except Exception as e:
            return {
                "metadata_quality": "오류",
                "completeness": "오류"
            }
    
    def _generate_interpretation(self, basic_stats: Dict, trend_analysis: Dict, metadata: StatMetadata) -> str:
        """데이터 해석 생성"""
        try:
            interpretation_parts = []
            
            # 기본 통계 해석
            if "error" not in basic_stats:
                mean_val = basic_stats.get("mean", 0)
                trend = trend_analysis.get("trend", "불명확")
                
                interpretation_parts.append(f"{metadata.title}의 평균값은 {mean_val:,.0f}입니다.")
                
                if trend == "증가":
                    interpretation_parts.append("전반적으로 증가 추세를 보이고 있습니다.")
                elif trend == "감소":
                    interpretation_parts.append("전반적으로 감소 추세를 보이고 있습니다.")
                elif trend == "안정":
                    interpretation_parts.append("안정적인 수준을 유지하고 있습니다.")
            else:
                interpretation_parts.append("데이터 분석에 어려움이 있습니다.")
            
            # 메타데이터 기반 해석
            if metadata.purpose and "목적" not in metadata.purpose:
                interpretation_parts.append(f"이 통계는 {metadata.purpose}를 위해 작성되었습니다.")
            
            if metadata.frequency:
                interpretation_parts.append(f"통계는 {metadata.frequency}적으로 작성됩니다.")
            
            return " ".join(interpretation_parts) if interpretation_parts else "데이터 해석을 생성할 수 없습니다."
            
        except Exception as e:
            return f"해석 생성 중 오류: {str(e)}"
    
    def _analyze_statistics(self, stat_data: List[StatData], metadata: StatMetadata) -> Dict[str, Any]:
        """통계 분석"""
        try:
            df = self._convert_to_dataframe(stat_data)
            basic_stats = self._calculate_basic_statistics(df)
            
            return {
                "analysis_result": f"{metadata.title}에 대한 기본 통계 분석이 완료되었습니다.",
                "status": "완료",
                "statistics": basic_stats
            }
            
        except Exception as e:
            return {
                "analysis_result": f"통계 분석 중 오류: {str(e)}",
                "status": "오류",
                "error": str(e)
            }
    
    def _generate_policy_insights(self, stat_data: List[StatData], metadata: StatMetadata) -> Dict[str, Any]:
        """정책 시사점 생성"""
        try:
            df = self._convert_to_dataframe(stat_data)
            trend = self._analyze_trends(df)
            
            insights = []
            
            if trend.get("trend") == "증가":
                insights.append("지속적인 증가 추세로 인한 정책적 대응이 필요할 수 있습니다.")
            elif trend.get("trend") == "감소":
                insights.append("감소 추세에 대한 원인 분석과 대책 마련이 필요합니다.")
            
            # 데이터 기반 정책 제안
            if len(stat_data) >= 3:
                insights.append("장기적인 데이터 수집을 통한 정책 효과성 평가가 가능합니다.")
            
            return {
                "policy_insights": " ".join(insights) if insights else "정책 시사점을 도출할 수 없습니다.",
                "status": "완료",
                "insights_count": len(insights)
            }
            
        except Exception as e:
            return {
                "policy_insights": f"정책 시사점 생성 중 오류: {str(e)}",
                "status": "오류",
                "error": str(e)
            }
    
    def _generate_simple_card_news(self, stat_data: List[StatData], metadata: StatMetadata) -> Dict[str, Any]:
        """간단한 카드뉴스 생성"""
        try:
            df = self._convert_to_dataframe(stat_data)
            basic_stats = self._calculate_basic_statistics(df)
            trend = self._analyze_trends(df)
            
            cards = []
            
            # 카드 1: 제목 및 개요
            cards.append({
                "title": metadata.title,
                "content": f"국토교통부에서 제공하는 {metadata.title} 통계입니다.",
                "type": "header"
            })
            
            # 카드 2: 기본 통계
            if "error" not in basic_stats:
                cards.append({
                    "title": "주요 통계",
                    "content": f"평균: {basic_stats.get('mean', 0):,.0f}\n최대: {basic_stats.get('max', 0):,.0f}\n최소: {basic_stats.get('min', 0):,.0f}",
                    "type": "statistics"
                })
            
            # 카드 3: 트렌드
            cards.append({
                "title": "트렌드 분석",
                "content": trend.get("description", "트렌드 분석을 할 수 없습니다."),
                "type": "trend"
            })
            
            # 카드 4: 정책 시사점
            policy_insights = self._generate_policy_insights(stat_data, metadata)
            cards.append({
                "title": "정책 시사점",
                "content": policy_insights.get("policy_insights", "정책 시사점을 도출할 수 없습니다."),
                "type": "policy"
            })
            
            return {
                "cards": cards,
                "status": "완료",
                "total_cards": len(cards)
            }
            
        except Exception as e:
            return {
                "cards": [],
                "status": "오류",
                "error": str(e)
            }
    
    def _get_empty_analysis(self) -> Dict[str, Any]:
        """빈 분석 결과 반환"""
        return {
            "data_structure": {
                "description": "분석할 데이터가 없습니다.",
                "total_years": 0,
                "data_fields": []
            },
            "collection_summary": {
                "status": "실패",
                "metadata_quality": "낮음",
                "data_completeness": "낮음"
            },
            "data_interpretation": "데이터가 부족하여 분석을 수행할 수 없습니다."
        }
    
    def _get_empty_comprehensive_analysis(self) -> Dict[str, Any]:
        """빈 종합 분석 결과 반환"""
        return {
            "statistics_analysis": {
                "analysis_result": "분석을 수행할 수 없습니다.",
                "status": "실패"
            },
            "trend_analysis": {
                "trend_analysis": "트렌드 분석을 수행할 수 없습니다.",
                "status": "실패"
            },
            "policy_insights": {
                "policy_insights": "정책 시사점을 도출할 수 없습니다.",
                "status": "실패"
            },
            "card_news": {
                "cards": [],
                "status": "실패"
            },
            "generated_at": datetime.now().isoformat()
        }

# 싱글톤 인스턴스
local_analysis_service = LocalAnalysisService()
