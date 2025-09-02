#!/usr/bin/env python3
"""
Visualization MCP Server
데이터 시각화를 위한 MCP 서버
"""

import json
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from plotly.utils import PlotlyJSONEncoder
import io
import base64
from typing import Dict, Any, List, Optional, Union

class VisualizationServer:
    """데이터 시각화 MCP 서버"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # 한글 폰트 설정
        plt.rcParams['font.family'] = 'Malgun Gothic'
        plt.rcParams['axes.unicode_minus'] = False
        # seaborn 스타일 설정
        sns.set_style("whitegrid")
        sns.set_palette("husl")
    
    def create_statistical_chart(self, data: Dict[str, List[Union[int, float]]], 
                                chart_type: str, title: str = "Statistical Chart") -> str:
        """통계 차트 생성"""
        try:
            df = pd.DataFrame(data)
            
            fig, ax = plt.subplots(figsize=(12, 8))
            
            if chart_type == "histogram":
                # 히스토그램 - 첫 번째 컬럼 사용
                column = list(data.keys())[0]
                values = data[column]
                
                ax.hist(values, bins=20, alpha=0.7, edgecolor='black', color='skyblue')
                ax.set_title(f'{title} - {column} 분포', fontsize=14, fontweight='bold')
                ax.set_xlabel(column, fontsize=12)
                ax.set_ylabel('빈도', fontsize=12)
                ax.grid(True, alpha=0.3)
                
                # 통계 정보 추가
                mean_val = np.mean(values)
                std_val = np.std(values)
                ax.axvline(mean_val, color='red', linestyle='--', linewidth=2, label=f'평균: {mean_val:.2f}')
                ax.axvline(mean_val + std_val, color='orange', linestyle=':', alpha=0.7, label=f'평균+표준편차: {mean_val + std_val:.2f}')
                ax.axvline(mean_val - std_val, color='orange', linestyle=':', alpha=0.7, label=f'평균-표준편차: {mean_val - std_val:.2f}')
                ax.legend()
                
            elif chart_type == "boxplot":
                # 박스플롯
                df.boxplot(ax=ax)
                ax.set_title(f'{title} - 박스플롯 분석', fontsize=14, fontweight='bold')
                ax.set_ylabel('값', fontsize=12)
                ax.grid(True, alpha=0.3)
                
            elif chart_type == "scatter":
                # 산점도 - 첫 두 컬럼 사용
                columns = list(data.keys())
                if len(columns) < 2:
                    raise ValueError("산점도를 위해서는 최소 2개의 데이터 컬럼이 필요합니다.")
                
                x_data = data[columns[0]]
                y_data = data[columns[1]]
                
                ax.scatter(x_data, y_data, alpha=0.6, s=50, color='coral')
                ax.set_title(f'{title} - {columns[0]} vs {columns[1]}', fontsize=14, fontweight='bold')
                ax.set_xlabel(columns[0], fontsize=12)
                ax.set_ylabel(columns[1], fontsize=12)
                ax.grid(True, alpha=0.3)
                
                # 회귀선 추가
                z = np.polyfit(x_data, y_data, 1)
                p = np.poly1d(z)
                ax.plot(x_data, p(x_data), "r--", alpha=0.8, linewidth=2, label=f'회귀선: y={z[0]:.3f}x+{z[1]:.3f}')
                ax.legend()
                
            elif chart_type == "line":
                # 선 그래프
                for column in data.keys():
                    ax.plot(range(len(data[column])), data[column], marker='o', linewidth=2, label=column)
                
                ax.set_title(f'{title} - 시계열 분석', fontsize=14, fontweight='bold')
                ax.set_xlabel('인덱스', fontsize=12)
                ax.set_ylabel('값', fontsize=12)
                ax.legend()
                ax.grid(True, alpha=0.3)
                
            elif chart_type == "correlation_heatmap":
                # 상관관계 히트맵
                correlation_matrix = df.corr()
                
                # matplotlib figure 크기 조정
                fig, ax = plt.subplots(figsize=(10, 8))
                
                # 히트맵 생성
                im = ax.imshow(correlation_matrix, cmap='coolwarm', aspect='auto', vmin=-1, vmax=1)
                
                # 축 설정
                ax.set_xticks(range(len(correlation_matrix.columns)))
                ax.set_yticks(range(len(correlation_matrix.columns)))
                ax.set_xticklabels(correlation_matrix.columns, rotation=45, ha='right')
                ax.set_yticklabels(correlation_matrix.columns)
                
                # 값 표시
                for i in range(len(correlation_matrix.columns)):
                    for j in range(len(correlation_matrix.columns)):
                        text = ax.text(j, i, f'{correlation_matrix.iloc[i, j]:.2f}',
                                     ha="center", va="center", color="black" if abs(correlation_matrix.iloc[i, j]) < 0.7 else "white")
                
                ax.set_title(f'{title} - 상관관계 히트맵', fontsize=14, fontweight='bold')
                
                # 컬러바 추가
                cbar = plt.colorbar(im, ax=ax)
                cbar.set_label('상관계수', rotation=270, labelpad=15)
                
            elif chart_type == "violin":
                # 바이올린 플롯
                if len(data.keys()) == 1:
                    column = list(data.keys())[0]
                    parts = ax.violinplot([data[column]], positions=[1], showmeans=True, showextrema=True)
                    ax.set_xticks([1])
                    ax.set_xticklabels([column])
                else:
                    df.plot(kind='box', ax=ax)  # 다중 컬럼의 경우 박스플롯으로 대체
                
                ax.set_title(f'{title} - 분포 분석', fontsize=14, fontweight='bold')
                ax.set_ylabel('값', fontsize=12)
                ax.grid(True, alpha=0.3)
                
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
                "chart_type": chart_type,
                "title": title,
                "data_columns": list(data.keys()),
                "image_base64": image_base64,
                "image_format": "png"
            }, ensure_ascii=False)
            
        except Exception as e:
            plt.close()
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
    
    def create_interactive_chart(self, data: Dict[str, List[Union[int, float]]], 
                               chart_type: str, title: str = "Interactive Chart") -> str:
        """인터랙티브 차트 생성 (Plotly)"""
        try:
            df = pd.DataFrame(data)
            
            if chart_type == "scatter_interactive":
                columns = list(data.keys())
                if len(columns) < 2:
                    raise ValueError("산점도를 위해서는 최소 2개의 데이터 컬럼이 필요합니다.")
                
                fig = px.scatter(df, x=columns[0], y=columns[1], 
                               title=f'{title} - 인터랙티브 산점도',
                               hover_data=columns,
                               color_discrete_sequence=['coral'])
                
            elif chart_type == "line_interactive":
                fig = go.Figure()
                
                for column in data.keys():
                    fig.add_trace(go.Scatter(
                        x=list(range(len(data[column]))),
                        y=data[column],
                        mode='lines+markers',
                        name=column,
                        line=dict(width=3),
                        marker=dict(size=6)
                    ))
                
                fig.update_layout(
                    title=f'{title} - 인터랙티브 시계열',
                    xaxis_title='인덱스',
                    yaxis_title='값',
                    hovermode='x unified'
                )
                
            elif chart_type == "histogram_interactive":
                column = list(data.keys())[0]
                fig = px.histogram(df, x=column, nbins=20,
                                 title=f'{title} - {column} 분포',
                                 color_discrete_sequence=['skyblue'])
                
            elif chart_type == "box_interactive":
                fig = go.Figure()
                
                for column in data.keys():
                    fig.add_trace(go.Box(
                        y=data[column],
                        name=column,
                        boxpoints='outliers'
                    ))
                
                fig.update_layout(
                    title=f'{title} - 인터랙티브 박스플롯',
                    yaxis_title='값'
                )
                
            elif chart_type == "3d_scatter":
                columns = list(data.keys())
                if len(columns) < 3:
                    raise ValueError("3D 산점도를 위해서는 최소 3개의 데이터 컬럼이 필요합니다.")
                
                fig = go.Figure(data=[go.Scatter3d(
                    x=data[columns[0]],
                    y=data[columns[1]],
                    z=data[columns[2]],
                    mode='markers',
                    marker=dict(
                        size=8,
                        color=data[columns[2]],
                        colorscale='Viridis',
                        showscale=True
                    ),
                    text=[f'{columns[0]}: {x}<br>{columns[1]}: {y}<br>{columns[2]}: {z}' 
                          for x, y, z in zip(data[columns[0]], data[columns[1]], data[columns[2]])],
                    hovertemplate='%{text}<extra></extra>'
                )])
                
                fig.update_layout(
                    title=f'{title} - 3D 산점도',
                    scene=dict(
                        xaxis_title=columns[0],
                        yaxis_title=columns[1],
                        zaxis_title=columns[2]
                    )
                )
                
            else:
                raise ValueError(f"지원하지 않는 인터랙티브 차트 타입: {chart_type}")
            
            # Plotly 차트를 JSON으로 변환
            fig_json = json.loads(json.dumps(fig, cls=PlotlyJSONEncoder))
            
            return json.dumps({
                "success": True,
                "chart_type": chart_type,
                "title": title,
                "data_columns": list(data.keys()),
                "plotly_json": fig_json,
                "chart_format": "plotly"
            }, ensure_ascii=False)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
    
    def create_dashboard_chart(self, datasets: List[Dict[str, Any]], 
                             dashboard_type: str = "multi_chart") -> str:
        """대시보드 차트 생성"""
        try:
            if dashboard_type == "multi_chart":
                # 여러 차트를 하나의 대시보드로
                n_charts = len(datasets)
                fig, axes = plt.subplots(2, 2, figsize=(16, 12))
                axes = axes.flatten()
                
                fig.suptitle('통계 분석 대시보드', fontsize=16, fontweight='bold')
                
                for i, dataset in enumerate(datasets[:4]):  # 최대 4개 차트
                    if i >= 4:
                        break
                        
                    data = dataset.get('data', {})
                    chart_type = dataset.get('type', 'line')
                    chart_title = dataset.get('title', f'Chart {i+1}')
                    
                    if not data:
                        continue
                    
                    df = pd.DataFrame(data)
                    
                    if chart_type == 'histogram' and len(data.keys()) > 0:
                        column = list(data.keys())[0]
                        axes[i].hist(data[column], bins=15, alpha=0.7, edgecolor='black')
                        axes[i].set_title(chart_title)
                        axes[i].set_xlabel(column)
                        axes[i].set_ylabel('빈도')
                        
                    elif chart_type == 'line':
                        for column in data.keys():
                            axes[i].plot(range(len(data[column])), data[column], 
                                       marker='o', label=column, linewidth=2)
                        axes[i].set_title(chart_title)
                        axes[i].set_xlabel('인덱스')
                        axes[i].set_ylabel('값')
                        axes[i].legend()
                        
                    elif chart_type == 'bar' and len(data.keys()) > 0:
                        column = list(data.keys())[0]
                        indices = range(len(data[column]))
                        axes[i].bar(indices, data[column], alpha=0.7)
                        axes[i].set_title(chart_title)
                        axes[i].set_xlabel('인덱스')
                        axes[i].set_ylabel(column)
                        
                    elif chart_type == 'scatter' and len(data.keys()) >= 2:
                        columns = list(data.keys())
                        axes[i].scatter(data[columns[0]], data[columns[1]], alpha=0.6)
                        axes[i].set_title(chart_title)
                        axes[i].set_xlabel(columns[0])
                        axes[i].set_ylabel(columns[1])
                    
                    axes[i].grid(True, alpha=0.3)
                
                # 빈 서브플롯 제거
                for i in range(len(datasets), 4):
                    fig.delaxes(axes[i])
                
            elif dashboard_type == "comparison":
                # 비교 분석 대시보드
                fig, axes = plt.subplots(1, 3, figsize=(18, 6))
                fig.suptitle('데이터 비교 분석', fontsize=16, fontweight='bold')
                
                if len(datasets) >= 2:
                    data1 = datasets[0].get('data', {})
                    data2 = datasets[1].get('data', {})
                    
                    # 첫 번째 차트: 히스토그램 비교
                    if data1 and data2:
                        col1 = list(data1.keys())[0]
                        col2 = list(data2.keys())[0]
                        
                        axes[0].hist(data1[col1], alpha=0.7, label=f'Dataset 1: {col1}', bins=15)
                        axes[0].hist(data2[col2], alpha=0.7, label=f'Dataset 2: {col2}', bins=15)
                        axes[0].set_title('분포 비교')
                        axes[0].legend()
                        axes[0].grid(True, alpha=0.3)
                        
                        # 두 번째 차트: 박스플롯 비교
                        combined_data = [data1[col1], data2[col2]]
                        axes[1].boxplot(combined_data, labels=[f'Dataset 1\n{col1}', f'Dataset 2\n{col2}'])
                        axes[1].set_title('박스플롯 비교')
                        axes[1].grid(True, alpha=0.3)
                        
                        # 세 번째 차트: 통계 요약 막대 그래프
                        stats1 = [np.mean(data1[col1]), np.median(data1[col1]), np.std(data1[col1])]
                        stats2 = [np.mean(data2[col2]), np.median(data2[col2]), np.std(data2[col2])]
                        
                        x = np.arange(3)
                        width = 0.35
                        
                        axes[2].bar(x - width/2, stats1, width, label='Dataset 1', alpha=0.7)
                        axes[2].bar(x + width/2, stats2, width, label='Dataset 2', alpha=0.7)
                        axes[2].set_title('통계 요약 비교')
                        axes[2].set_xticks(x)
                        axes[2].set_xticklabels(['평균', '중위수', '표준편차'])
                        axes[2].legend()
                        axes[2].grid(True, alpha=0.3)
            
            # 이미지를 base64로 인코딩
            buffer = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return json.dumps({
                "success": True,
                "dashboard_type": dashboard_type,
                "charts_count": len(datasets),
                "image_base64": image_base64,
                "image_format": "png"
            }, ensure_ascii=False)
            
        except Exception as e:
            plt.close()
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
    
    def create_statistical_summary_viz(self, data: Dict[str, List[Union[int, float]]], 
                                     title: str = "Statistical Summary") -> str:
        """통계 요약 시각화"""
        try:
            df = pd.DataFrame(data)
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
            
            if not numeric_cols:
                raise ValueError("수치형 데이터가 없습니다.")
            
            # 2x2 서브플롯 구성
            fig, axes = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle(f'{title} - 종합 통계 분석', fontsize=16, fontweight='bold')
            
            # 1. 기술통계 막대 그래프
            stats_data = []
            for col in numeric_cols[:3]:  # 최대 3개 컬럼
                col_data = df[col].dropna()
                stats_data.append([
                    col_data.mean(),
                    col_data.median(),
                    col_data.std(),
                    col_data.min(),
                    col_data.max()
                ])
            
            if stats_data:
                stats_df = pd.DataFrame(stats_data, 
                                      columns=['평균', '중위수', '표준편차', '최솟값', '최댓값'],
                                      index=numeric_cols[:len(stats_data)])
                
                stats_df.plot(kind='bar', ax=axes[0, 0], alpha=0.8)
                axes[0, 0].set_title('기술통계 요약')
                axes[0, 0].set_ylabel('값')
                axes[0, 0].tick_params(axis='x', rotation=45)
                axes[0, 0].legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                axes[0, 0].grid(True, alpha=0.3)
            
            # 2. 분포 히스토그램
            if len(numeric_cols) > 0:
                col = numeric_cols[0]
                axes[0, 1].hist(df[col].dropna(), bins=20, alpha=0.7, edgecolor='black', color='lightblue')
                axes[0, 1].set_title(f'{col} 분포')
                axes[0, 1].set_xlabel(col)
                axes[0, 1].set_ylabel('빈도')
                axes[0, 1].grid(True, alpha=0.3)
            
            # 3. 박스플롯
            df[numeric_cols].boxplot(ax=axes[1, 0])
            axes[1, 0].set_title('박스플롯 - 이상치 탐지')
            axes[1, 0].set_ylabel('값')
            axes[1, 0].tick_params(axis='x', rotation=45)
            axes[1, 0].grid(True, alpha=0.3)
            
            # 4. 상관관계 히트맵 (수치형 컬럼이 2개 이상인 경우)
            if len(numeric_cols) > 1:
                corr_matrix = df[numeric_cols].corr()
                im = axes[1, 1].imshow(corr_matrix, cmap='coolwarm', aspect='auto', vmin=-1, vmax=1)
                
                axes[1, 1].set_xticks(range(len(corr_matrix.columns)))
                axes[1, 1].set_yticks(range(len(corr_matrix.columns)))
                axes[1, 1].set_xticklabels(corr_matrix.columns, rotation=45, ha='right')
                axes[1, 1].set_yticklabels(corr_matrix.columns)
                
                # 상관계수 값 표시
                for i in range(len(corr_matrix.columns)):
                    for j in range(len(corr_matrix.columns)):
                        axes[1, 1].text(j, i, f'{corr_matrix.iloc[i, j]:.2f}',
                                       ha="center", va="center", 
                                       color="white" if abs(corr_matrix.iloc[i, j]) > 0.7 else "black")
                
                axes[1, 1].set_title('상관관계 히트맵')
                
                # 컬러바 추가
                cbar = plt.colorbar(im, ax=axes[1, 1])
                cbar.set_label('상관계수', rotation=270, labelpad=15)
            else:
                axes[1, 1].text(0.5, 0.5, '상관관계 분석 불가\n(수치형 컬럼 < 2개)', 
                               ha='center', va='center', transform=axes[1, 1].transAxes)
                axes[1, 1].set_title('상관관계 히트맵')
            
            # 이미지를 base64로 인코딩
            buffer = io.BytesIO()
            plt.tight_layout()
            plt.savefig(buffer, format='png', dpi=300, bbox_inches='tight')
            buffer.seek(0)
            image_base64 = base64.b64encode(buffer.getvalue()).decode()
            plt.close()
            
            return json.dumps({
                "success": True,
                "title": title,
                "numeric_columns": numeric_cols,
                "data_shape": df.shape,
                "image_base64": image_base64,
                "image_format": "png"
            }, ensure_ascii=False)
            
        except Exception as e:
            plt.close()
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)

def main():
    """MCP 서버 메인 함수"""
    server = VisualizationServer()
    
    print("Visualization MCP Server 초기화 완료")
    print("사용 가능한 기능:")
    print("- create_statistical_chart: 통계 차트 생성")
    print("- create_interactive_chart: 인터랙티브 차트 생성")
    print("- create_dashboard_chart: 대시보드 차트 생성")
    print("- create_statistical_summary_viz: 통계 요약 시각화")

if __name__ == "__main__":
    main()