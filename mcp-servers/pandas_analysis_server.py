#!/usr/bin/env python3
"""
Pandas Data Analysis MCP Server
통계 데이터 분석을 위한 MCP 서버
"""

import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from typing import Dict, Any, List, Optional
from pathlib import Path

# MCP 서버 설정
class PandasAnalysisServer:
    """pandas 기반 데이터 분석 MCP 서버"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.data_cache = {}  # 데이터 캐시
        
    def load_data(self, file_path: str, file_type: str = "csv") -> str:
        """데이터 파일 로드"""
        try:
            if file_type.lower() == "csv":
                df = pd.read_csv(file_path)
            elif file_type.lower() == "excel":
                df = pd.read_excel(file_path)
            elif file_type.lower() == "json":
                df = pd.read_json(file_path)
            else:
                raise ValueError(f"지원하지 않는 파일 형식: {file_type}")
            
            # 데이터 캐시에 저장
            cache_key = Path(file_path).stem
            self.data_cache[cache_key] = df
            
            return json.dumps({
                "success": True,
                "cache_key": cache_key,
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "dtypes": df.dtypes.astype(str).to_dict(),
                "head": df.head().to_dict('records')
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
    
    def basic_statistics(self, cache_key: str) -> str:
        """기초 통계 분석"""
        try:
            if cache_key not in self.data_cache:
                raise ValueError(f"캐시에서 데이터를 찾을 수 없습니다: {cache_key}")
            
            df = self.data_cache[cache_key]
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            
            if not numeric_columns:
                raise ValueError("수치형 데이터가 없습니다.")
            
            stats = {}
            for col in numeric_columns:
                series = df[col].dropna()
                stats[col] = {
                    "count": int(series.count()),
                    "mean": float(series.mean()),
                    "median": float(series.median()),
                    "std": float(series.std()),
                    "min": float(series.min()),
                    "max": float(series.max()),
                    "q1": float(series.quantile(0.25)),
                    "q3": float(series.quantile(0.75)),
                    "skewness": float(series.skew()),
                    "kurtosis": float(series.kurtosis())
                }
            
            return json.dumps({
                "success": True,
                "cache_key": cache_key,
                "numeric_columns": numeric_columns,
                "statistics": stats,
                "summary": {
                    "total_rows": len(df),
                    "total_columns": len(df.columns),
                    "numeric_columns": len(numeric_columns),
                    "missing_values": df.isnull().sum().to_dict()
                }
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
    
    def correlation_analysis(self, cache_key: str) -> str:
        """상관관계 분석"""
        try:
            if cache_key not in self.data_cache:
                raise ValueError(f"캐시에서 데이터를 찾을 수 없습니다: {cache_key}")
            
            df = self.data_cache[cache_key]
            numeric_df = df.select_dtypes(include=[np.number])
            
            if numeric_df.empty:
                raise ValueError("수치형 데이터가 없습니다.")
            
            # 상관관계 계산
            correlation_matrix = numeric_df.corr()
            
            # 강한 상관관계 찾기 (0.7 이상)
            strong_correlations = []
            for i in range(len(correlation_matrix.columns)):
                for j in range(i + 1, len(correlation_matrix.columns)):
                    col1 = correlation_matrix.columns[i]
                    col2 = correlation_matrix.columns[j]
                    corr_value = correlation_matrix.iloc[i, j]
                    
                    if abs(corr_value) >= 0.7:
                        strong_correlations.append({
                            "variable1": col1,
                            "variable2": col2,
                            "correlation": float(corr_value),
                            "strength": "강한 양의 상관관계" if corr_value >= 0.7 else "강한 음의 상관관계"
                        })
            
            return json.dumps({
                "success": True,
                "cache_key": cache_key,
                "correlation_matrix": correlation_matrix.to_dict(),
                "strong_correlations": strong_correlations,
                "interpretation": {
                    "total_pairs": len(strong_correlations),
                    "analysis_note": "상관계수 0.7 이상의 강한 상관관계를 표시"
                }
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
    
    def generate_visualization(self, cache_key: str, chart_type: str, columns: List[str]) -> str:
        """데이터 시각화 생성"""
        try:
            if cache_key not in self.data_cache:
                raise ValueError(f"캐시에서 데이터를 찾을 수 없습니다: {cache_key}")
            
            df = self.data_cache[cache_key]
            
            # 한글 폰트 설정
            plt.rcParams['font.family'] = 'Malgun Gothic'
            plt.rcParams['axes.unicode_minus'] = False
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            if chart_type == "histogram":
                if len(columns) != 1:
                    raise ValueError("히스토그램은 하나의 컬럼만 지원합니다.")
                
                ax.hist(df[columns[0]].dropna(), bins=20, alpha=0.7, edgecolor='black')
                ax.set_title(f'{columns[0]} 분포')
                ax.set_xlabel(columns[0])
                ax.set_ylabel('빈도')
                
            elif chart_type == "boxplot":
                if len(columns) < 1:
                    raise ValueError("박스플롯에는 최소 하나의 컬럼이 필요합니다.")
                
                df[columns].boxplot(ax=ax)
                ax.set_title('박스플롯 분석')
                
            elif chart_type == "scatter":
                if len(columns) != 2:
                    raise ValueError("산점도는 정확히 두 개의 컬럼이 필요합니다.")
                
                ax.scatter(df[columns[0]], df[columns[1]], alpha=0.6)
                ax.set_xlabel(columns[0])
                ax.set_ylabel(columns[1])
                ax.set_title(f'{columns[0]} vs {columns[1]} 산점도')
                
            elif chart_type == "line":
                for col in columns:
                    ax.plot(df.index, df[col], label=col, linewidth=2)
                ax.set_title('시계열 분석')
                ax.set_xlabel('인덱스')
                ax.set_ylabel('값')
                ax.legend()
                
            elif chart_type == "correlation_heatmap":
                numeric_df = df.select_dtypes(include=[np.number])
                correlation_matrix = numeric_df.corr()
                
                sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0, ax=ax)
                ax.set_title('상관관계 히트맵')
                
            else:
                raise ValueError(f"지원하지 않는 차트 타입: {chart_type}")
            
            # 이미지를 base64로 인코딩
            buffer = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return json.dumps({
                "success": True,
                "cache_key": cache_key,
                "chart_type": chart_type,
                "columns": columns,
                "image_base64": image_base64,
                "image_format": "png"
            }, ensure_ascii=False)
            
        except Exception as e:
            plt.close()  # 에러 시에도 figure 정리
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
    
    def trend_analysis(self, cache_key: str, time_column: str, value_columns: List[str]) -> str:
        """트렌드 분석"""
        try:
            if cache_key not in self.data_cache:
                raise ValueError(f"캐시에서 데이터를 찾을 수 없습니다: {cache_key}")
            
            df = self.data_cache[cache_key].copy()
            
            # 시간 컬럼 변환
            if time_column in df.columns:
                df[time_column] = pd.to_datetime(df[time_column])
                df = df.sort_values(time_column)
            
            trends = {}
            for col in value_columns:
                if col not in df.columns:
                    continue
                    
                series = df[col].dropna()
                if len(series) < 2:
                    continue
                
                # 선형 회귀를 통한 트렌드 분석
                x = np.arange(len(series))
                y = series.values
                
                # 최소자승법으로 기울기 계산
                slope = np.polyfit(x, y, 1)[0]
                
                # 변화율 계산
                if len(series) > 1:
                    first_value = series.iloc[0]
                    last_value = series.iloc[-1]
                    change_rate = ((last_value - first_value) / first_value * 100) if first_value != 0 else 0
                else:
                    change_rate = 0
                
                trends[col] = {
                    "slope": float(slope),
                    "change_rate_percent": float(change_rate),
                    "trend_direction": "증가" if slope > 0 else "감소" if slope < 0 else "평형",
                    "first_value": float(series.iloc[0]) if len(series) > 0 else None,
                    "last_value": float(series.iloc[-1]) if len(series) > 0 else None,
                    "mean_value": float(series.mean()),
                    "volatility": float(series.std())
                }
            
            return json.dumps({
                "success": True,
                "cache_key": cache_key,
                "time_column": time_column,
                "value_columns": value_columns,
                "trends": trends,
                "analysis_period": {
                    "start": str(df[time_column].min()) if time_column in df.columns else "N/A",
                    "end": str(df[time_column].max()) if time_column in df.columns else "N/A",
                    "total_periods": len(df)
                }
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)

# MCP 서버 실행을 위한 메인 함수
def main():
    """MCP 서버 메인 함수"""
    server = PandasAnalysisServer()
    
    # 테스트 실행
    print("Pandas Analysis MCP Server 초기화 완료")
    print("사용 가능한 기능:")
    print("- load_data: 데이터 파일 로드")
    print("- basic_statistics: 기초 통계 분석")
    print("- correlation_analysis: 상관관계 분석")
    print("- generate_visualization: 데이터 시각화")
    print("- trend_analysis: 트렌드 분석")

if __name__ == "__main__":
    main()