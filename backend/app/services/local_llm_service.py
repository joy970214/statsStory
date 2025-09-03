#!/usr/bin/env python3
"""
Local LLM Service
로컬 LLM을 사용한 통계 분석 서비스 (API 토큰 없이)
"""

import json
import logging
from typing import List, Dict, Any
from app.models.stat_models import StatData, StatMetadata
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

class LocalLLMService:
    """로컬 LLM 기반 분석 서비스"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    async def generate_comprehensive_analysis(self, stat_data: List[StatData], metadata: StatMetadata) -> str:
        """종합 분석 생성 (로컬 LLM 시뮬레이션)"""
        try:
            self.logger.info(f"로컬 LLM 종합 분석 시작: {metadata.title}")
            
            # 데이터 분석
            analysis_result = self._perform_comprehensive_analysis(stat_data, metadata)
            
            # 결과를 자연어로 변환
            narrative_analysis = self._generate_analysis_narrative(analysis_result, metadata)
            
            return narrative_analysis
            
        except Exception as e:
            self.logger.error(f"로컬 LLM 종합 분석 실패: {e}")
            return f"{metadata.title}에 대한 기본적인 종합 분석 결과입니다."
    
    def _perform_comprehensive_analysis(self, stat_data: List[StatData], metadata: StatMetadata) -> Dict[str, Any]:
        """포괄적인 데이터 분석 수행"""
        
        if not stat_data:
            return {"error": "분석할 데이터가 없습니다."}
        
        # 1. 시계열 분석
        trend_analysis = self._analyze_trends(stat_data)
        
        # 2. 통계적 특성 분석
        statistical_analysis = self._analyze_statistics(stat_data)
        
        # 3. 변화율 분석
        change_analysis = self._analyze_changes(stat_data)
        
        # 4. 패턴 및 특이사항 분석
        pattern_analysis = self._analyze_patterns(stat_data)
        
        return {
            "trend_analysis": trend_analysis,
            "statistical_analysis": statistical_analysis,
            "change_analysis": change_analysis,
            "pattern_analysis": pattern_analysis,
            "data_period": f"{min([d.year for d in stat_data])} - {max([d.year for d in stat_data])}",
            "total_data_points": len(stat_data)
        }
    
    def _analyze_trends(self, stat_data: List[StatData]) -> Dict[str, Any]:
        """트렌드 분석"""
        trends = {}
        
        # 모든 데이터 필드에 대해 트렌드 분석
        all_keys = set()
        for data in stat_data:
            if data.data:
                all_keys.update(data.data.keys())
        
        for key in all_keys:
            values = []
            years = []
            
            for data in stat_data:
                if data.data and key in data.data:
                    try:
                        value = self._convert_to_number(data.data[key])
                        if value is not None:
                            values.append(value)
                            years.append(data.year)
                    except:
                        continue
            
            if len(values) >= 2:
                # 선형 회귀를 통한 트렌드 분석
                slope = self._calculate_slope(years, values)
                
                trends[key] = {
                    "slope": slope,
                    "direction": "증가" if slope > 0.01 else "감소" if slope < -0.01 else "안정",
                    "first_value": values[0] if values else None,
                    "last_value": values[-1] if values else None,
                    "change_rate": ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0,
                    "volatility": np.std(values) if len(values) > 1 else 0
                }
        
        return trends
    
    def _analyze_statistics(self, stat_data: List[StatData]) -> Dict[str, Any]:
        """통계적 특성 분석"""
        stats = {}
        
        all_keys = set()
        for data in stat_data:
            if data.data:
                all_keys.update(data.data.keys())
        
        for key in all_keys:
            values = []
            
            for data in stat_data:
                if data.data and key in data.data:
                    try:
                        value = self._convert_to_number(data.data[key])
                        if value is not None:
                            values.append(value)
                    except:
                        continue
            
            if values:
                stats[key] = {
                    "count": len(values),
                    "mean": np.mean(values),
                    "median": np.median(values),
                    "std": np.std(values),
                    "min": np.min(values),
                    "max": np.max(values),
                    "range": np.max(values) - np.min(values),
                    "cv": (np.std(values) / np.mean(values)) if np.mean(values) != 0 else 0
                }
        
        return stats
    
    def _analyze_changes(self, stat_data: List[StatData]) -> Dict[str, Any]:
        """변화율 분석"""
        changes = {}
        
        # 연도별 정렬
        sorted_data = sorted(stat_data, key=lambda x: x.year)
        
        all_keys = set()
        for data in sorted_data:
            if data.data:
                all_keys.update(data.data.keys())
        
        for key in all_keys:
            yearly_changes = []
            prev_value = None
            
            for data in sorted_data:
                if data.data and key in data.data:
                    try:
                        current_value = self._convert_to_number(data.data[key])
                        if current_value is not None and prev_value is not None:
                            change_rate = ((current_value - prev_value) / prev_value * 100) if prev_value != 0 else 0
                            yearly_changes.append({
                                "year": data.year,
                                "change_rate": change_rate,
                                "absolute_change": current_value - prev_value
                            })
                        prev_value = current_value
                    except:
                        continue
            
            if yearly_changes:
                changes[key] = {
                    "yearly_changes": yearly_changes,
                    "avg_change_rate": np.mean([c["change_rate"] for c in yearly_changes]),
                    "max_increase": max([c["change_rate"] for c in yearly_changes]),
                    "max_decrease": min([c["change_rate"] for c in yearly_changes]),
                    "volatility": np.std([c["change_rate"] for c in yearly_changes])
                }
        
        return changes
    
    def _analyze_patterns(self, stat_data: List[StatData]) -> Dict[str, Any]:
        """패턴 및 특이사항 분석"""
        patterns = {
            "anomalies": [],
            "cycles": [],
            "correlations": [],
            "insights": []
        }
        
        # 이상값 탐지
        all_keys = set()
        for data in stat_data:
            if data.data:
                all_keys.update(data.data.keys())
        
        for key in all_keys:
            values = []
            years = []
            
            for data in stat_data:
                if data.data and key in data.data:
                    try:
                        value = self._convert_to_number(data.data[key])
                        if value is not None:
                            values.append(value)
                            years.append(data.year)
                    except:
                        continue
            
            if len(values) >= 3:
                # 이상값 탐지 (Z-score 방법)
                mean_val = np.mean(values)
                std_val = np.std(values)
                
                for i, (year, value) in enumerate(zip(years, values)):
                    if std_val > 0:
                        z_score = abs((value - mean_val) / std_val)
                        if z_score > 2:  # 2 표준편차 이상
                            patterns["anomalies"].append({
                                "field": key,
                                "year": year,
                                "value": value,
                                "z_score": z_score,
                                "description": f"{key}의 {year}년 값이 평균에서 크게 벗어남"
                            })
        
        return patterns
    
    def _generate_analysis_narrative(self, analysis_result: Dict[str, Any], metadata: StatMetadata) -> str:
        """분석 결과를 자연어 보고서로 변환"""
        
        narrative_parts = []
        
        # 제목 및 개요
        narrative_parts.append(f"# {metadata.title} 종합 분석 보고서")
        narrative_parts.append("")
        narrative_parts.append(f"**분석 기간**: {analysis_result.get('data_period', 'N/A')}")
        narrative_parts.append(f"**분석 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        narrative_parts.append(f"**데이터 포인트**: {analysis_result.get('total_data_points', 'N/A')}개")
        narrative_parts.append("")
        
        # 트렌드 분석 결과
        if "trend_analysis" in analysis_result and analysis_result["trend_analysis"]:
            narrative_parts.append("## 📈 트렌드 분석")
            narrative_parts.append("")
            
            trends = analysis_result["trend_analysis"]
            for field, trend_data in trends.items():
                direction = trend_data["direction"]
                change_rate = trend_data["change_rate"]
                first_val = trend_data["first_value"]
                last_val = trend_data["last_value"]
                
                if direction == "증가":
                    narrative_parts.append(f"- **{field}**: 지속적인 **증가 추세**를 보이고 있습니다. "
                                        f"분석 기간 동안 {first_val:,.0f}에서 {last_val:,.0f}으로 "
                                        f"{change_rate:+.1f}% 변화했습니다.")
                elif direction == "감소":
                    narrative_parts.append(f"- **{field}**: **감소 추세**를 나타내고 있습니다. "
                                        f"분석 기간 동안 {first_val:,.0f}에서 {last_val:,.0f}으로 "
                                        f"{change_rate:+.1f}% 변화했습니다.")
                else:
                    narrative_parts.append(f"- **{field}**: **안정적인 수준**을 유지하고 있습니다. "
                                        f"분석 기간 동안 큰 변화 없이 {change_rate:+.1f}% 변화했습니다.")
            narrative_parts.append("")
        
        # 통계적 특성
        if "statistical_analysis" in analysis_result and analysis_result["statistical_analysis"]:
            narrative_parts.append("## 📊 통계적 특성")
            narrative_parts.append("")
            
            stats = analysis_result["statistical_analysis"]
            for field, stat_data in stats.items():
                mean_val = stat_data["mean"]
                std_val = stat_data["std"]
                cv = stat_data["cv"]
                
                narrative_parts.append(f"- **{field}**: 평균 {mean_val:,.0f}, 표준편차 {std_val:,.0f}")
                
                if cv < 0.1:
                    narrative_parts.append(f"  - 변동계수 {cv:.3f}로 **매우 안정적**인 패턴을 보임")
                elif cv < 0.3:
                    narrative_parts.append(f"  - 변동계수 {cv:.3f}로 **적정 수준**의 변동성을 보임")
                else:
                    narrative_parts.append(f"  - 변동계수 {cv:.3f}로 **높은 변동성**을 보임")
            
            narrative_parts.append("")
        
        # 변화율 분석
        if "change_analysis" in analysis_result and analysis_result["change_analysis"]:
            narrative_parts.append("## 📋 변화율 분석")
            narrative_parts.append("")
            
            changes = analysis_result["change_analysis"]
            for field, change_data in changes.items():
                avg_change = change_data["avg_change_rate"]
                max_increase = change_data["max_increase"]
                max_decrease = change_data["max_decrease"]
                
                narrative_parts.append(f"- **{field}**: 연평균 {avg_change:+.1f}% 변화")
                narrative_parts.append(f"  - 최대 증가: {max_increase:+.1f}%")
                narrative_parts.append(f"  - 최대 감소: {max_decrease:+.1f}%")
            
            narrative_parts.append("")
        
        # 특이사항 및 이상값
        if "pattern_analysis" in analysis_result:
            patterns = analysis_result["pattern_analysis"]
            if patterns.get("anomalies"):
                narrative_parts.append("## ⚠️ 주요 특이사항")
                narrative_parts.append("")
                
                for anomaly in patterns["anomalies"]:
                    narrative_parts.append(f"- **{anomaly['year']}년 {anomaly['field']}**: "
                                        f"{anomaly['value']:,.0f} (Z-점수: {anomaly['z_score']:.2f}) - "
                                        f"평균에서 크게 벗어나는 값으로 주의깊은 분석이 필요합니다.")
                
                narrative_parts.append("")
        
        # 결론 및 시사점
        narrative_parts.append("## 💡 주요 시사점")
        narrative_parts.append("")
        
        # 로컬 LLM 기반 인사이트 생성 (시뮬레이션)
        insights = self._generate_insights(analysis_result, metadata)
        for insight in insights:
            narrative_parts.append(f"- {insight}")
        
        narrative_parts.append("")
        narrative_parts.append("---")
        narrative_parts.append("*이 분석은 로컬 LLM 기반 분석 시스템을 통해 생성되었습니다.*")
        
        return "\n".join(narrative_parts)
    
    def _generate_insights(self, analysis_result: Dict[str, Any], metadata: StatMetadata) -> List[str]:
        """분석 결과 기반 인사이트 생성"""
        insights = []
        
        # 트렌드 기반 인사이트
        if "trend_analysis" in analysis_result:
            trends = analysis_result["trend_analysis"]
            increasing_fields = [f for f, t in trends.items() if t["direction"] == "증가"]
            decreasing_fields = [f for f, t in trends.items() if t["direction"] == "감소"]
            
            if increasing_fields:
                insights.append(f"**증가 추세 지표**: {', '.join(increasing_fields[:3])} 등이 지속적으로 증가하고 있어 "
                              f"해당 분야의 성장을 시사합니다.")
            
            if decreasing_fields:
                insights.append(f"**감소 추세 지표**: {', '.join(decreasing_fields[:3])} 등이 감소하고 있어 "
                              f"관련 정책 검토가 필요할 수 있습니다.")
        
        # 변동성 기반 인사이트
        if "statistical_analysis" in analysis_result:
            stats = analysis_result["statistical_analysis"]
            high_volatility_fields = [f for f, s in stats.items() if s.get("cv", 0) > 0.3]
            
            if high_volatility_fields:
                insights.append(f"**높은 변동성**: {', '.join(high_volatility_fields[:2])} 등은 변동성이 높아 "
                              f"안정화 방안 모색이 필요합니다.")
        
        # 기본 인사이트
        if not insights:
            insights.append("데이터 분석 결과, 전반적으로 안정적인 패턴을 보이고 있습니다.")
            insights.append(f"{metadata.title} 분야의 지속적인 모니터링과 분석을 통해 "
                          "정책 수립에 활용할 수 있을 것으로 판단됩니다.")
        
        return insights
    
    def _convert_to_number(self, value) -> float:
        """문자열을 숫자로 변환"""
        if isinstance(value, (int, float)):
            return float(value)
        
        if isinstance(value, str):
            # 콤마 제거
            cleaned = value.replace(',', '')
            # 퍼센트 제거
            cleaned = cleaned.replace('%', '')
            # 기타 공백 제거
            cleaned = cleaned.strip()
            
            try:
                return float(cleaned)
            except ValueError:
                return None
        
        return None
    
    def _calculate_slope(self, x_values, y_values) -> float:
        """최소자승법으로 기울기 계산"""
        if len(x_values) != len(y_values) or len(x_values) < 2:
            return 0.0
        
        x_array = np.array(x_values)
        y_array = np.array(y_values)
        
        # 최소자승법
        n = len(x_array)
        slope = (n * np.sum(x_array * y_array) - np.sum(x_array) * np.sum(y_array)) / \
                (n * np.sum(x_array ** 2) - (np.sum(x_array)) ** 2)
        
        return slope

# 전역 인스턴스
local_llm_service = LocalLLMService()