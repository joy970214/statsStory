#!/usr/bin/env python3
"""
File Analysis MCP Server
파일 분석 및 처리를 위한 MCP 서버
"""

import json
import logging
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
import PyPDF2

class FileAnalysisServer:
    """파일 분석 MCP 서버"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.supported_formats = ['csv', 'xlsx', 'xls', 'json', 'txt', 'pdf']
        
    def analyze_file_structure(self, file_path: str) -> str:
        """파일 구조 분석"""
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
            
            file_info = {
                "file_name": file_path.name,
                "file_size": file_path.stat().st_size,
                "file_extension": file_path.suffix.lower(),
                "absolute_path": str(file_path.absolute()),
                "created_time": str(pd.to_datetime(file_path.stat().st_ctime, unit='s')),
                "modified_time": str(pd.to_datetime(file_path.stat().st_mtime, unit='s'))
            }
            
            # 파일 타입별 추가 분석
            if file_info["file_extension"] == '.csv':
                df = pd.read_csv(file_path)
                file_info.update({
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": df.columns.tolist(),
                    "data_types": df.dtypes.astype(str).to_dict(),
                    "memory_usage": df.memory_usage(deep=True).sum(),
                    "null_counts": df.isnull().sum().to_dict()
                })
                
            elif file_info["file_extension"] in ['.xlsx', '.xls']:
                df = pd.read_excel(file_path)
                file_info.update({
                    "rows": len(df),
                    "columns": len(df.columns),
                    "column_names": df.columns.tolist(),
                    "data_types": df.dtypes.astype(str).to_dict()
                })
                
            elif file_info["file_extension"] == '.txt':
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    file_info.update({
                        "lines": len(content.split('\n')),
                        "characters": len(content),
                        "words": len(content.split()),
                        "encoding": "utf-8"
                    })
            
            return json.dumps({
                "success": True,
                "file_analysis": file_info
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
    
    def csv_detailed_analysis(self, file_path: str) -> str:
        """CSV 파일 상세 분석"""
        try:
            df = pd.read_csv(file_path)
            
            # 기본 정보
            basic_info = {
                "shape": df.shape,
                "columns": df.columns.tolist(),
                "data_types": df.dtypes.astype(str).to_dict(),
                "memory_usage_mb": df.memory_usage(deep=True).sum() / 1024 / 1024
            }
            
            # 수치형 컬럼 분석
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            numeric_analysis = {}
            
            for col in numeric_columns:
                series = df[col].dropna()
                numeric_analysis[col] = {
                    "count": int(series.count()),
                    "mean": float(series.mean()),
                    "median": float(series.median()),
                    "std": float(series.std()),
                    "min": float(series.min()),
                    "max": float(series.max()),
                    "q1": float(series.quantile(0.25)),
                    "q3": float(series.quantile(0.75)),
                    "null_count": int(df[col].isnull().sum()),
                    "null_percentage": float(df[col].isnull().sum() / len(df) * 100)
                }
            
            # 범주형 컬럼 분석
            categorical_columns = df.select_dtypes(include=['object']).columns.tolist()
            categorical_analysis = {}
            
            for col in categorical_columns:
                series = df[col].dropna()
                value_counts = series.value_counts().head(10)
                categorical_analysis[col] = {
                    "unique_count": int(series.nunique()),
                    "null_count": int(df[col].isnull().sum()),
                    "null_percentage": float(df[col].isnull().sum() / len(df) * 100),
                    "top_values": value_counts.to_dict(),
                    "most_frequent": str(series.mode().iloc[0]) if not series.mode().empty else None
                }
            
            # 데이터 품질 분석
            quality_analysis = {
                "total_missing_values": int(df.isnull().sum().sum()),
                "missing_percentage": float(df.isnull().sum().sum() / (df.shape[0] * df.shape[1]) * 100),
                "duplicate_rows": int(df.duplicated().sum()),
                "complete_rows": int((~df.isnull().any(axis=1)).sum())
            }
            
            return json.dumps({
                "success": True,
                "file_path": file_path,
                "basic_info": basic_info,
                "numeric_analysis": numeric_analysis,
                "categorical_analysis": categorical_analysis,
                "quality_analysis": quality_analysis,
                "sample_data": df.head(5).to_dict('records')
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
    
    def generate_data_profile_chart(self, file_path: str, chart_type: str = "summary") -> str:
        """데이터 프로파일링 차트 생성"""
        try:
            df = pd.read_csv(file_path)
            
            # 한글 폰트 설정
            plt.rcParams['font.family'] = 'Malgun Gothic'
            plt.rcParams['axes.unicode_minus'] = False
            
            if chart_type == "summary":
                # 데이터 요약 차트 (4개 서브플롯)
                fig, axes = plt.subplots(2, 2, figsize=(15, 12))
                fig.suptitle('데이터 프로파일링 요약', fontsize=16)
                
                # 1. 결측값 현황
                missing_data = df.isnull().sum()
                missing_data = missing_data[missing_data > 0]
                if not missing_data.empty:
                    missing_data.plot(kind='bar', ax=axes[0, 0], color='red', alpha=0.7)
                    axes[0, 0].set_title('결측값 현황')
                    axes[0, 0].set_xlabel('컬럼')
                    axes[0, 0].set_ylabel('결측값 개수')
                    axes[0, 0].tick_params(axis='x', rotation=45)
                else:
                    axes[0, 0].text(0.5, 0.5, '결측값 없음', ha='center', va='center', transform=axes[0, 0].transAxes)
                    axes[0, 0].set_title('결측값 현황')
                
                # 2. 데이터 타입 분포
                dtypes_counts = df.dtypes.value_counts()
                axes[0, 1].pie(dtypes_counts.values, labels=dtypes_counts.index, autopct='%1.1f%%')
                axes[0, 1].set_title('데이터 타입 분포')
                
                # 3. 수치형 데이터 분포 (첫 번째 수치형 컬럼)
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) > 0:
                    df[numeric_cols[0]].hist(bins=20, ax=axes[1, 0], alpha=0.7, edgecolor='black')
                    axes[1, 0].set_title(f'{numeric_cols[0]} 분포')
                    axes[1, 0].set_xlabel(numeric_cols[0])
                    axes[1, 0].set_ylabel('빈도')
                else:
                    axes[1, 0].text(0.5, 0.5, '수치형 데이터 없음', ha='center', va='center', transform=axes[1, 0].transAxes)
                    axes[1, 0].set_title('수치형 데이터 분포')
                
                # 4. 상관관계 히트맵
                numeric_df = df.select_dtypes(include=[np.number])
                if len(numeric_df.columns) > 1:
                    correlation_matrix = numeric_df.corr()
                    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', center=0, ax=axes[1, 1])
                    axes[1, 1].set_title('상관관계 히트맵')
                else:
                    axes[1, 1].text(0.5, 0.5, '상관관계 분석 불가\n(수치형 컬럼 < 2개)', ha='center', va='center', transform=axes[1, 1].transAxes)
                    axes[1, 1].set_title('상관관계 히트맵')
                
            elif chart_type == "distribution":
                # 모든 수치형 컬럼의 분포 차트
                numeric_cols = df.select_dtypes(include=[np.number]).columns
                if len(numeric_cols) == 0:
                    raise ValueError("수치형 데이터가 없습니다.")
                
                n_cols = min(3, len(numeric_cols))
                n_rows = (len(numeric_cols) + n_cols - 1) // n_cols
                
                fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 4 * n_rows))
                if n_rows == 1 and n_cols == 1:
                    axes = [axes]
                elif n_rows == 1 or n_cols == 1:
                    axes = axes.flatten()
                else:
                    axes = axes.flatten()
                
                fig.suptitle('수치형 데이터 분포', fontsize=16)
                
                for i, col in enumerate(numeric_cols):
                    if i < len(axes):
                        axes[i].hist(df[col].dropna(), bins=20, alpha=0.7, edgecolor='black')
                        axes[i].set_title(f'{col} 분포')
                        axes[i].set_xlabel(col)
                        axes[i].set_ylabel('빈도')
                
                # 빈 서브플롯 제거
                for i in range(len(numeric_cols), len(axes)):
                    fig.delaxes(axes[i])
            
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
                "file_path": file_path,
                "chart_type": chart_type,
                "image_base64": image_base64,
                "image_format": "png"
            }, ensure_ascii=False)
            
        except Exception as e:
            plt.close()
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
    
    def text_file_analysis(self, file_path: str) -> str:
        """텍스트 파일 분석"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            words = content.split()
            
            # 문자 빈도 분석
            char_freq = {}
            for char in content.lower():
                if char.isalpha():
                    char_freq[char] = char_freq.get(char, 0) + 1
            
            # 단어 길이 분석
            word_lengths = [len(word) for word in words]
            
            analysis = {
                "file_path": file_path,
                "total_lines": len(lines),
                "total_words": len(words),
                "total_characters": len(content),
                "total_characters_no_spaces": len(content.replace(' ', '')),
                "average_words_per_line": len(words) / len(lines) if lines else 0,
                "average_word_length": sum(word_lengths) / len(word_lengths) if word_lengths else 0,
                "longest_line": max(lines, key=len) if lines else "",
                "longest_word": max(words, key=len) if words else "",
                "character_frequency": dict(sorted(char_freq.items(), key=lambda x: x[1], reverse=True)[:10]),
                "line_length_stats": {
                    "min": min(len(line) for line in lines) if lines else 0,
                    "max": max(len(line) for line in lines) if lines else 0,
                    "avg": sum(len(line) for line in lines) / len(lines) if lines else 0
                }
            }
            
            return json.dumps({
                "success": True,
                "analysis": analysis
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
    
    def pdf_text_extraction(self, file_path: str) -> str:
        """PDF 텍스트 추출 및 분석"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                pdf_info = {
                    "total_pages": len(pdf_reader.pages),
                    "metadata": {
                        "title": pdf_reader.metadata.get('/Title', '') if pdf_reader.metadata else '',
                        "author": pdf_reader.metadata.get('/Author', '') if pdf_reader.metadata else '',
                        "creator": pdf_reader.metadata.get('/Creator', '') if pdf_reader.metadata else ''
                    }
                }
                
                # 모든 페이지의 텍스트 추출
                all_text = ""
                page_texts = []
                
                for page_num, page in enumerate(pdf_reader.pages):
                    page_text = page.extract_text()
                    page_texts.append({
                        "page_number": page_num + 1,
                        "text_length": len(page_text),
                        "word_count": len(page_text.split()),
                        "text_preview": page_text[:200] + "..." if len(page_text) > 200 else page_text
                    })
                    all_text += page_text + "\n"
                
                # 전체 텍스트 통계
                words = all_text.split()
                pdf_info.update({
                    "total_text_length": len(all_text),
                    "total_word_count": len(words),
                    "average_words_per_page": len(words) / len(pdf_reader.pages) if pdf_reader.pages else 0,
                    "page_details": page_texts[:5]  # 처음 5페이지만 표시
                })
            
            return json.dumps({
                "success": True,
                "pdf_analysis": pdf_info
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)

def main():
    """MCP 서버 메인 함수"""
    server = FileAnalysisServer()
    
    print("File Analysis MCP Server 초기화 완료")
    print("사용 가능한 기능:")
    print("- analyze_file_structure: 파일 구조 분석")
    print("- csv_detailed_analysis: CSV 상세 분석")
    print("- generate_data_profile_chart: 데이터 프로파일링 차트")
    print("- text_file_analysis: 텍스트 파일 분석")
    print("- pdf_text_extraction: PDF 텍스트 추출")

if __name__ == "__main__":
    main()