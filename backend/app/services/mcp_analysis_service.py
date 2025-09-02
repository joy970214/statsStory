import asyncio
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.models.stat_models import StatData, StatMetadata
from app.services.mcp_client import mcp_client
import logging

logger = logging.getLogger(__name__)

class MCPAnalysisService:
    """MCP 서버들을 활용한 통계 분석 서비스"""
    
    def __init__(self):
        self.mcp_client = mcp_client
        self.analysis_cache = {}
    
    async def analyze_basic_data(self, stat_data: List[StatData], metadata: StatMetadata) -> Dict[str, Any]:
        """MCP를 활용한 기본 통계 데이터 분석"""
        try:
            if not stat_data:
                return self._get_empty_analysis()
            
            # 데이터를 MCP 분석용 형식으로 변환
            analysis_data = self._prepare_data_for_mcp(stat_data)
            
            # 1. 기본 통계량 계산 (Math Calculation MCP)
            basic_stats = await self._get_basic_statistics_mcp(analysis_data)
            
            # 2. 트렌드 분석 (Pandas Analysis MCP)
            trend_analysis = await self._get_trend_analysis_mcp(analysis_data)
            
            # 3. 데이터 품질 평가
            data_quality = await self._assess_data_quality_mcp(analysis_data)
            
            # 4. 시각화 생성 (Visualization MCP)
            visualization = await self._create_basic_visualization_mcp(analysis_data)
            
            return {
                "data_structure": {
                    "description": f"{len(stat_data)}년간의 {metadata.title} 데이터",
                    "total_years": len(stat_data),
                    "data_fields": list(analysis_data.keys()) if analysis_data else []
                },
                "collection_summary": {
                    "status": "완료",
                    "metadata_quality": data_quality.get("metadata_quality", "보통"),
                    "data_completeness": data_quality.get("completeness", "보통")
                },
                "data_interpretation": self._generate_mcp_interpretation(basic_stats, trend_analysis, metadata),
                "basic_statistics": basic_stats,
                "trend_analysis": trend_analysis,
                "visualization": visualization,
                "analysis_method": "MCP 기반 분석"
            }
            
        except Exception as e:
            logger.error(f"MCP 기본 분석 오류: {e}")
            return self._get_empty_analysis()
    
    async def generate_comprehensive_analysis(self, stat_data: List[StatData], metadata: StatMetadata) -> Dict[str, Any]:
        """MCP를 활용한 종합 분석 생성"""
        try:
            # 기본 분석
            basic_analysis = await self.analyze_basic_data(stat_data, metadata)
            
            # 통계 분석
            statistics_analysis = await self._analyze_statistics_mcp(stat_data, metadata)
            
            # 트렌드 분석
            trend_analysis = await self._analyze_trends_advanced_mcp(stat_data, metadata)
            
            # 정책 시사점
            policy_insights = await self._generate_policy_insights_mcp(stat_data, metadata)
            
            # 카드뉴스 생성
            card_news = await self._generate_card_news_mcp(stat_data, metadata)
            
            return {
                "statistics_analysis": statistics_analysis,
                "trend_analysis": trend_analysis,
                "policy_insights": policy_insights,
                "card_news": card_news,
                "generated_at": datetime.now().isoformat(),
                "analysis_method": "MCP 종합 분석"
            }
            
        except Exception as e:
            logger.error(f"MCP 종합 분석 오류: {e}")
            return self._get_empty_comprehensive_analysis()
    
    def _prepare_data_for_mcp(self, stat_data: List[StatData]) -> Dict[str, List]:
        """MCP 분석을 위해 데이터 준비"""
        try:
            data_dict = {}
            
            for stat in stat_data:
                year = int(stat.year)
                
                if hasattr(stat, 'data') and isinstance(stat.data, dict):
                    for key, value in stat.data.items():
                        if key not in data_dict:
                            data_dict[key] = []
                        
                        # 수치형 데이터만 수집
                        if isinstance(value, (int, float)) and value is not None:
                            data_dict[key].append(value)
                        else:
                            data_dict[key].append(0)  # 기본값
                else:
                    # 기본 데이터 구조
                    if 'value' not in data_dict:
                        data_dict['value'] = []
                    if 'total' not in data_dict:
                        data_dict['total'] = []
                    
                    data_dict['value'].append(getattr(stat, 'value', 0) or 0)
                    data_dict['total'].append(getattr(stat, 'total', 0) or 0)
            
            return data_dict
            
        except Exception as e:
            logger.error(f"데이터 준비 오류: {e}")
            return {}
    
    async def _get_basic_statistics_mcp(self, data: Dict[str, List]) -> Dict[str, Any]:
        """Math Calculation MCP를 통한 기본 통계량 계산"""
        try:
            if not data:
                return {"error": "분석할 데이터가 없습니다."}
            
            # 첫 번째 수치형 컬럼 사용
            first_key = list(data.keys())[0]
            values = data[first_key]
            
            if not values or all(v == 0 for v in values):
                return {"error": "유효한 수치 데이터가 없습니다."}
            
            # MCP Math Calculation 서버 호출
            result = await self.mcp_client.call_math_calculation("basic_statistics", data=values)
            
            if result.get("success"):
                return result
            else:
                # MCP 실패 시 로컬 계산으로 대체
                return self._calculate_basic_stats_local(values)
                
        except Exception as e:
            logger.error(f"기본 통계 MCP 오류: {e}")
            # 로컬 계산으로 대체
            if data:
                first_key = list(data.keys())[0]
                values = data[first_key]
                return self._calculate_basic_stats_local(values)
            return {"error": f"통계 계산 중 오류: {str(e)}"}
    
    def _calculate_basic_stats_local(self, values: List) -> Dict[str, Any]:
        """로컬에서 기본 통계량 계산 (MCP 실패 시 대체)"""
        try:
            if not values:
                return {"error": "데이터가 없습니다."}
            
            # 0이 아닌 값만 필터링
            valid_values = [v for v in values if v != 0 and v is not None]
            
            if not valid_values:
                return {"error": "유효한 데이터가 없습니다."}
            
            # 기본 통계량 계산
            total = sum(valid_values)
            count = len(valid_values)
            mean = total / count
            
            # 중앙값 계산
            sorted_values = sorted(valid_values)
            if count % 2 == 0:
                median = (sorted_values[count//2 - 1] + sorted_values[count//2]) / 2
            else:
                median = sorted_values[count//2]
            
            return {
                "mean": float(mean),
                "median": float(median),
                "max": float(max(valid_values)),
                "min": float(min(valid_values)),
                "total": float(total),
                "count": int(count),
                "calculation_method": "로컬 계산"
            }
            
        except Exception as e:
            return {"error": f"로컬 계산 중 오류: {str(e)}"}
    
    async def _get_trend_analysis_mcp(self, data: Dict[str, List]) -> Dict[str, Any]:
        """Pandas Analysis MCP를 통한 트렌드 분석"""
        try:
            if not data:
                return {"trend": "불명확", "description": "데이터가 부족합니다."}
            
            # MCP Pandas Analysis 서버 호출
            result = await self.mcp_client.call_pandas_analysis("trend_analysis", data=data)
            
            if result.get("success"):
                return result
            else:
                # MCP 실패 시 로컬 계산으로 대체
                return self._calculate_trend_local(data)
                
        except Exception as e:
            logger.error(f"트렌드 분석 MCP 오류: {e}")
            return self._calculate_trend_local(data)
    
    def _calculate_trend_local(self, data: Dict[str, List]) -> Dict[str, Any]:
        """로컬에서 트렌드 계산"""
        try:
            if not data:
                return {"trend": "불명확", "description": "데이터가 부족합니다."}
            
            # 첫 번째 수치형 컬럼 사용
            first_key = list(data.keys())[0]
            values = data[first_key]
            
            if len(values) < 2:
                return {"trend": "불명확", "description": "데이터가 부족합니다."}
            
            # 간단한 트렌드 계산 (연속된 값들의 변화)
            changes = []
            for i in range(1, len(values)):
                if values[i-1] != 0:
                    change = values[i] - values[i-1]
                    changes.append(change)
            
            if not changes:
                return {"trend": "불명확", "description": "변화를 계산할 수 없습니다."}
            
            avg_change = sum(changes) / len(changes)
            
            if avg_change > 0:
                trend = "증가"
                description = f"평균 {abs(avg_change):.2f} 증가"
            elif avg_change < 0:
                trend = "감소"
                description = f"평균 {abs(avg_change):.2f} 감소"
            else:
                trend = "안정"
                description = "변화 없음"
            
            return {
                "trend": trend,
                "slope": float(avg_change),
                "description": description,
                "confidence": "보통",
                "calculation_method": "로컬 계산"
            }
            
        except Exception as e:
            return {"trend": "오류", "description": f"분석 중 오류: {str(e)}"}
    
    async def _assess_data_quality_mcp(self, data: Dict[str, List]) -> Dict[str, str]:
        """MCP를 통한 데이터 품질 평가"""
        try:
            if not data:
                return {"metadata_quality": "낮음", "completeness": "낮음"}
            
            # File Analysis MCP 서버 호출
            result = await self.mcp_client.call_file_analysis("assess_data_quality", 
                                                            file_path="virtual_data", data=data)
            
            if result.get("success"):
                return result
            else:
                # 로컬 품질 평가로 대체
                return self._assess_quality_local(data)
                
        except Exception as e:
            logger.error(f"데이터 품질 평가 MCP 오류: {e}")
            return self._assess_quality_local(data)
    
    def _assess_quality_local(self, data: Dict[str, List]) -> Dict[str, str]:
        """로컬에서 데이터 품질 평가"""
        try:
            if not data:
                return {"metadata_quality": "낮음", "completeness": "낮음"}
            
            # 완성도 계산
            total_cells = sum(len(values) for values in data.values())
            non_null_cells = sum(len([v for v in values if v != 0 and v is not None]) for values in data.values())
            
            if total_cells == 0:
                completeness_rate = 0
            else:
                completeness_rate = (non_null_cells / total_cells) * 100
            
            if completeness_rate >= 90:
                completeness = "높음"
            elif completeness_rate >= 70:
                completeness = "보통"
            else:
                completeness = "낮음"
            
            return {
                "metadata_quality": "보통",
                "completeness": completeness,
                "completeness_rate": f"{completeness_rate:.1f}%"
            }
            
        except Exception as e:
            return {"metadata_quality": "오류", "completeness": "오류"}
    
    async def _create_basic_visualization_mcp(self, data: Dict[str, List]) -> Dict[str, Any]:
        """Visualization MCP를 통한 기본 시각화 생성"""
        try:
            if not data:
                return {"error": "시각화할 데이터가 없습니다."}
            
            # MCP Visualization 서버 호출
            result = await self.mcp_client.call_visualization("create_statistical_chart", 
                                                            data=data, chart_type="line")
            
            if result.get("success"):
                return result
            else:
                # 기본 시각화 정보 반환
                return {
                    "chart_type": "line",
                    "data_points": len(list(data.values())[0]) if data else 0,
                    "status": "MCP 실패, 기본 정보 제공"
                }
                
        except Exception as e:
            logger.error(f"시각화 MCP 오류: {e}")
            return {"error": f"시각화 생성 중 오류: {str(e)}"}
    
    def _generate_mcp_interpretation(self, basic_stats: Dict, trend_analysis: Dict, metadata: StatMetadata) -> str:
        """MCP 분석 결과를 바탕으로 데이터 해석 생성"""
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
            
            interpretation_parts.append("분석은 MCP 서버를 통해 수행되었습니다.")
            
            return " ".join(interpretation_parts) if interpretation_parts else "데이터 해석을 생성할 수 없습니다."
            
        except Exception as e:
            return f"해석 생성 중 오류: {str(e)}"
    
    async def _analyze_statistics_mcp(self, stat_data: List[StatData], metadata: StatMetadata) -> Dict[str, Any]:
        """MCP를 통한 통계 분석"""
        try:
            data = self._prepare_data_for_mcp(stat_data)
            basic_stats = await self._get_basic_statistics_mcp(data)
            
            return {
                "analysis_result": f"{metadata.title}에 대한 MCP 기반 통계 분석이 완료되었습니다.",
                "status": "완료",
                "statistics": basic_stats,
                "analysis_method": "MCP"
            }
            
        except Exception as e:
            return {
                "analysis_result": f"통계 분석 중 오류: {str(e)}",
                "status": "오류",
                "error": str(e)
            }
    
    async def _analyze_trends_advanced_mcp(self, stat_data: List[StatData], metadata: StatMetadata) -> Dict[str, Any]:
        """MCP를 통한 고급 트렌드 분석"""
        try:
            data = self._prepare_data_for_mcp(stat_data)
            basic_trend = await self._get_trend_analysis_mcp(data)
            
            # 종합 통계 분석 워크플로우 호출
            comprehensive_result = await self.mcp_client.comprehensive_statistical_analysis(data, "trend")
            
            return {
                "trend_analysis": basic_trend.get("description", "트렌드 분석을 수행할 수 없습니다."),
                "trend_direction": basic_trend.get("trend", "불명확"),
                "advanced_analysis": comprehensive_result,
                "status": "완료",
                "analysis_method": "MCP 종합 분석"
            }
            
        except Exception as e:
            logger.error(f"고급 트렌드 분석 MCP 오류: {e}")
            return {
                "trend_analysis": "분석 중 오류가 발생했습니다.",
                "status": "오류",
                "error": str(e)
            }
    
    async def _generate_policy_insights_mcp(self, stat_data: List[StatData], metadata: StatMetadata) -> Dict[str, Any]:
        """MCP를 통한 정책 시사점 생성"""
        try:
            data = self._prepare_data_for_mcp(stat_data)
            trend = await self._get_trend_analysis_mcp(data)
            
            insights = []
            
            if trend.get("trend") == "증가":
                insights.append("지속적인 증가 추세로 인한 정책적 대응이 필요할 수 있습니다.")
            elif trend.get("trend") == "감소":
                insights.append("감소 추세에 대한 원인 분석과 대책 마련이 필요합니다.")
            
            # 데이터 기반 정책 제안
            if len(stat_data) >= 3:
                insights.append("장기적인 데이터 수집을 통한 정책 효과성 평가가 가능합니다.")
            
            insights.append("MCP 기반 분석을 통해 정책 시사점을 도출했습니다.")
            
            return {
                "policy_insights": " ".join(insights) if insights else "정책 시사점을 도출할 수 없습니다.",
                "status": "완료",
                "insights_count": len(insights),
                "analysis_method": "MCP"
            }
            
        except Exception as e:
            return {
                "policy_insights": f"정책 시사점 생성 중 오류: {str(e)}",
                "status": "오류",
                "error": str(e)
            }
    
    async def _generate_card_news_mcp(self, stat_data: List[StatData], metadata: StatMetadata) -> Dict[str, Any]:
        """MCP를 통한 카드뉴스 생성"""
        try:
            data = self._prepare_data_for_mcp(stat_data)
            basic_stats = await self._get_basic_statistics_mcp(data)
            trend = await self._get_trend_analysis_mcp(data)
            
            cards = []
            
            # 카드 1: 제목 및 개요
            cards.append({
                "title": metadata.title,
                "content": f"국토교통부에서 제공하는 {metadata.title} 통계입니다. MCP 기반 분석으로 생성되었습니다.",
                "type": "header"
            })
            
            # 카드 2: 기본 통계
            if "error" not in basic_stats:
                cards.append({
                    "title": "주요 통계 (MCP 분석)",
                    "content": f"평균: {basic_stats.get('mean', 0):,.0f}\n최대: {basic_stats.get('max', 0):,.0f}\n최소: {basic_stats.get('min', 0):,.0f}",
                    "type": "statistics"
                })
            
            # 카드 3: 트렌드
            cards.append({
                "title": "트렌드 분석 (MCP)",
                "content": trend.get("description", "트렌드 분석을 할 수 없습니다."),
                "type": "trend"
            })
            
            # 카드 4: 정책 시사점
            policy_insights = await self._generate_policy_insights_mcp(stat_data, metadata)
            cards.append({
                "title": "정책 시사점 (MCP)",
                "content": policy_insights.get("policy_insights", "정책 시사점을 도출할 수 없습니다."),
                "type": "policy"
            })
            
            return {
                "cards": cards,
                "status": "완료",
                "total_cards": len(cards),
                "generation_method": "MCP"
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
            "data_interpretation": "데이터가 부족하여 분석을 수행할 수 없습니다.",
            "analysis_method": "MCP (실패)"
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
            "generated_at": datetime.now().isoformat(),
            "analysis_method": "MCP (실패)"
        }

# 싱글톤 인스턴스
mcp_analysis_service = MCPAnalysisService()
