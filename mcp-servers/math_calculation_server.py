#!/usr/bin/env python3
"""
Mathematical Calculation MCP Server
수학적 계산 및 통계 분석을 위한 MCP 서버
"""

import json
import logging
import numpy as np
import scipy.stats as stats
from scipy import optimize
import math
from typing import Dict, Any, List, Optional, Union
import re

class MathCalculationServer:
    """수학 계산 MCP 서버"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.constants = {
            'pi': math.pi,
            'e': math.e,
            'tau': math.tau,
            'inf': math.inf,
            'nan': math.nan
        }
    
    def basic_statistics(self, data: List[Union[int, float]]) -> str:
        """기본 통계 계산"""
        try:
            if not data or len(data) == 0:
                raise ValueError("데이터가 비어있습니다.")
            
            arr = np.array(data)
            
            # 기본 통계량
            basic_stats = {
                "count": int(len(arr)),
                "sum": float(np.sum(arr)),
                "mean": float(np.mean(arr)),
                "median": float(np.median(arr)),
                "mode": float(stats.mode(arr, keepdims=False)[0]) if len(arr) > 1 else float(arr[0]),
                "std": float(np.std(arr, ddof=1)) if len(arr) > 1 else 0.0,
                "variance": float(np.var(arr, ddof=1)) if len(arr) > 1 else 0.0,
                "min": float(np.min(arr)),
                "max": float(np.max(arr)),
                "range": float(np.max(arr) - np.min(arr)),
                "q1": float(np.percentile(arr, 25)),
                "q3": float(np.percentile(arr, 75)),
                "iqr": float(np.percentile(arr, 75) - np.percentile(arr, 25)),
                "skewness": float(stats.skew(arr)) if len(arr) > 2 else 0.0,
                "kurtosis": float(stats.kurtosis(arr)) if len(arr) > 3 else 0.0
            }
            
            # 분포의 정규성 검정 (Shapiro-Wilk 테스트)
            if len(arr) >= 3:
                shapiro_stat, shapiro_p = stats.shapiro(arr)
                basic_stats["shapiro_test"] = {
                    "statistic": float(shapiro_stat),
                    "p_value": float(shapiro_p),
                    "is_normal": shapiro_p > 0.05
                }
            
            return json.dumps({
                "success": True,
                "input_data": data,
                "statistics": basic_stats
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
    
    def correlation_coefficient(self, x: List[Union[int, float]], y: List[Union[int, float]]) -> str:
        """상관계수 계산"""
        try:
            if len(x) != len(y):
                raise ValueError("두 데이터셋의 길이가 다릅니다.")
            
            if len(x) < 2:
                raise ValueError("상관계수 계산을 위해서는 최소 2개의 데이터 포인트가 필요합니다.")
            
            x_arr = np.array(x)
            y_arr = np.array(y)
            
            # 피어슨 상관계수
            pearson_r, pearson_p = stats.pearsonr(x_arr, y_arr)
            
            # 스피어만 상관계수
            spearman_rho, spearman_p = stats.spearmanr(x_arr, y_arr)
            
            # 켄달 타우
            kendall_tau, kendall_p = stats.kendalltau(x_arr, y_arr)
            
            correlation_analysis = {
                "data_points": len(x),
                "pearson": {
                    "coefficient": float(pearson_r),
                    "p_value": float(pearson_p),
                    "strength": get_correlation_strength(abs(pearson_r)),
                    "direction": "positive" if pearson_r > 0 else "negative" if pearson_r < 0 else "none"
                },
                "spearman": {
                    "coefficient": float(spearman_rho),
                    "p_value": float(spearman_p),
                    "strength": get_correlation_strength(abs(spearman_rho))
                },
                "kendall": {
                    "coefficient": float(kendall_tau),
                    "p_value": float(kendall_p),
                    "strength": get_correlation_strength(abs(kendall_tau))
                }
            }
            
            return json.dumps({
                "success": True,
                "x_data": x,
                "y_data": y,
                "correlation_analysis": correlation_analysis
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
    
    def linear_regression(self, x: List[Union[int, float]], y: List[Union[int, float]]) -> str:
        """선형 회귀 분석"""
        try:
            if len(x) != len(y):
                raise ValueError("두 데이터셋의 길이가 다릅니다.")
            
            if len(x) < 2:
                raise ValueError("회귀 분석을 위해서는 최소 2개의 데이터 포인트가 필요합니다.")
            
            x_arr = np.array(x)
            y_arr = np.array(y)
            
            # 선형 회귀 계산
            slope, intercept, r_value, p_value, std_err = stats.linregress(x_arr, y_arr)
            
            # 예측값 계산
            y_pred = slope * x_arr + intercept
            
            # R-squared 계산
            r_squared = r_value ** 2
            
            # 잔차 계산
            residuals = y_arr - y_pred
            
            # 표준 오차 계산
            n = len(x_arr)
            mse = np.sum(residuals ** 2) / (n - 2) if n > 2 else 0
            rmse = np.sqrt(mse)
            
            regression_analysis = {
                "equation": {
                    "slope": float(slope),
                    "intercept": float(intercept),
                    "formula": f"y = {slope:.4f}x + {intercept:.4f}"
                },
                "statistics": {
                    "r_value": float(r_value),
                    "r_squared": float(r_squared),
                    "p_value": float(p_value),
                    "standard_error": float(std_err),
                    "rmse": float(rmse),
                    "mse": float(mse)
                },
                "predictions": y_pred.tolist(),
                "residuals": residuals.tolist(),
                "interpretation": {
                    "fit_quality": "excellent" if r_squared > 0.9 else "good" if r_squared > 0.7 else "moderate" if r_squared > 0.5 else "poor",
                    "significance": "significant" if p_value < 0.05 else "not significant"
                }
            }
            
            return json.dumps({
                "success": True,
                "x_data": x,
                "y_data": y,
                "regression_analysis": regression_analysis
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
    
    def hypothesis_testing(self, data1: List[Union[int, float]], data2: List[Union[int, float]] = None, 
                          test_type: str = "one_sample", mu: float = 0) -> str:
        """가설 검정"""
        try:
            arr1 = np.array(data1)
            
            if test_type == "one_sample":
                # 일표본 t-검정
                t_stat, p_value = stats.ttest_1samp(arr1, mu)
                
                test_result = {
                    "test_type": "One-sample t-test",
                    "null_hypothesis": f"평균 = {mu}",
                    "alternative_hypothesis": f"평균 ≠ {mu}",
                    "sample_mean": float(np.mean(arr1)),
                    "hypothesized_mean": float(mu),
                    "t_statistic": float(t_stat),
                    "p_value": float(p_value),
                    "degrees_of_freedom": len(arr1) - 1,
                    "result": "reject null hypothesis" if p_value < 0.05 else "fail to reject null hypothesis",
                    "interpretation": f"평균이 {mu}와 {'다릅니다' if p_value < 0.05 else '같습니다'} (α=0.05)"
                }
                
            elif test_type == "two_sample":
                if data2 is None:
                    raise ValueError("이표본 검정을 위해서는 두 번째 데이터셋이 필요합니다.")
                
                arr2 = np.array(data2)
                
                # 이표본 t-검정 (등분산 가정)
                t_stat, p_value = stats.ttest_ind(arr1, arr2)
                
                test_result = {
                    "test_type": "Independent two-sample t-test",
                    "null_hypothesis": "두 그룹의 평균이 같다",
                    "alternative_hypothesis": "두 그룹의 평균이 다르다",
                    "sample1_mean": float(np.mean(arr1)),
                    "sample2_mean": float(np.mean(arr2)),
                    "mean_difference": float(np.mean(arr1) - np.mean(arr2)),
                    "t_statistic": float(t_stat),
                    "p_value": float(p_value),
                    "degrees_of_freedom": len(arr1) + len(arr2) - 2,
                    "result": "reject null hypothesis" if p_value < 0.05 else "fail to reject null hypothesis",
                    "interpretation": f"두 그룹의 평균이 {'다릅니다' if p_value < 0.05 else '같습니다'} (α=0.05)"
                }
                
            elif test_type == "paired":
                if data2 is None:
                    raise ValueError("대응표본 검정을 위해서는 두 번째 데이터셋이 필요합니다.")
                
                arr2 = np.array(data2)
                
                if len(arr1) != len(arr2):
                    raise ValueError("대응표본 검정을 위해서는 두 데이터셋의 길이가 같아야 합니다.")
                
                # 대응표본 t-검정
                t_stat, p_value = stats.ttest_rel(arr1, arr2)
                
                test_result = {
                    "test_type": "Paired samples t-test",
                    "null_hypothesis": "차이의 평균 = 0",
                    "alternative_hypothesis": "차이의 평균 ≠ 0",
                    "mean_difference": float(np.mean(arr1 - arr2)),
                    "t_statistic": float(t_stat),
                    "p_value": float(p_value),
                    "degrees_of_freedom": len(arr1) - 1,
                    "result": "reject null hypothesis" if p_value < 0.05 else "fail to reject null hypothesis",
                    "interpretation": f"두 측정값 간에 {'유의한 차이가 있습니다' if p_value < 0.05 else '유의한 차이가 없습니다'} (α=0.05)"
                }
            
            else:
                raise ValueError(f"지원하지 않는 검정 유형: {test_type}")
            
            return json.dumps({
                "success": True,
                "data1": data1,
                "data2": data2,
                "test_result": test_result
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)
    
    def mathematical_expression(self, expression: str, variables: Dict[str, float] = None) -> str:
        """수학 표현식 계산 (안전한 eval)"""
        try:
            # 안전한 수학 함수들만 허용
            safe_dict = {
                "__builtins__": {},
                "abs": abs, "round": round, "min": min, "max": max,
                "sum": sum, "pow": pow,
                "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
                "exp": math.exp, "sin": math.sin, "cos": math.cos, "tan": math.tan,
                "asin": math.asin, "acos": math.acos, "atan": math.atan,
                "pi": math.pi, "e": math.e, "tau": math.tau
            }
            
            # 사용자 정의 변수 추가
            if variables:
                safe_dict.update(variables)
            
            # 위험한 문자열 패턴 검사
            dangerous_patterns = [
                '__', 'import', 'exec', 'eval', 'open', 'file',
                'input', 'raw_input', 'compile', 'reload'
            ]
            
            for pattern in dangerous_patterns:
                if pattern in expression.lower():
                    raise ValueError(f"보안상 위험한 패턴이 감지되었습니다: {pattern}")
            
            # 표현식 계산
            result = eval(expression, safe_dict)
            
            return json.dumps({
                "success": True,
                "expression": expression,
                "variables": variables or {},
                "result": float(result) if isinstance(result, (int, float)) else str(result),
                "result_type": type(result).__name__
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "expression": expression,
                "error": str(e)
            }, ensure_ascii=False)
    
    def matrix_operations(self, matrix_a: List[List[Union[int, float]]], 
                         matrix_b: List[List[Union[int, float]]] = None, 
                         operation: str = "determinant") -> str:
        """행렬 연산"""
        try:
            mat_a = np.array(matrix_a)
            
            if operation == "determinant":
                if mat_a.shape[0] != mat_a.shape[1]:
                    raise ValueError("행렬식 계산을 위해서는 정사각행렬이 필요합니다.")
                
                det = np.linalg.det(mat_a)
                
                result = {
                    "operation": "determinant",
                    "matrix_a": matrix_a,
                    "result": float(det),
                    "matrix_shape": mat_a.shape
                }
                
            elif operation == "inverse":
                if mat_a.shape[0] != mat_a.shape[1]:
                    raise ValueError("역행렬 계산을 위해서는 정사각행렬이 필요합니다.")
                
                try:
                    inv_mat = np.linalg.inv(mat_a)
                    result = {
                        "operation": "inverse",
                        "matrix_a": matrix_a,
                        "result": inv_mat.tolist(),
                        "matrix_shape": mat_a.shape
                    }
                except np.linalg.LinAlgError:
                    raise ValueError("특이행렬(singular matrix)로 역행렬을 계산할 수 없습니다.")
                
            elif operation == "eigenvalues":
                if mat_a.shape[0] != mat_a.shape[1]:
                    raise ValueError("고유값 계산을 위해서는 정사각행렬이 필요합니다.")
                
                eigenvalues, eigenvectors = np.linalg.eig(mat_a)
                
                result = {
                    "operation": "eigenvalues",
                    "matrix_a": matrix_a,
                    "eigenvalues": eigenvalues.tolist(),
                    "eigenvectors": eigenvectors.tolist(),
                    "matrix_shape": mat_a.shape
                }
                
            elif operation == "multiply":
                if matrix_b is None:
                    raise ValueError("행렬 곱셈을 위해서는 두 번째 행렬이 필요합니다.")
                
                mat_b = np.array(matrix_b)
                
                if mat_a.shape[1] != mat_b.shape[0]:
                    raise ValueError("행렬 곱셈을 위해서는 첫 번째 행렬의 열 수와 두 번째 행렬의 행 수가 같아야 합니다.")
                
                product = np.dot(mat_a, mat_b)
                
                result = {
                    "operation": "multiply",
                    "matrix_a": matrix_a,
                    "matrix_b": matrix_b,
                    "result": product.tolist(),
                    "result_shape": product.shape
                }
            
            else:
                raise ValueError(f"지원하지 않는 연산: {operation}")
            
            return json.dumps({
                "success": True,
                "matrix_operation": result
            }, ensure_ascii=False, indent=2)
            
        except Exception as e:
            return json.dumps({
                "success": False,
                "error": str(e)
            }, ensure_ascii=False)

def get_correlation_strength(abs_corr: float) -> str:
    """상관계수 강도 분류"""
    if abs_corr >= 0.9:
        return "very strong"
    elif abs_corr >= 0.7:
        return "strong"
    elif abs_corr >= 0.5:
        return "moderate"
    elif abs_corr >= 0.3:
        return "weak"
    else:
        return "very weak"

def main():
    """MCP 서버 메인 함수"""
    server = MathCalculationServer()
    
    print("Mathematical Calculation MCP Server 초기화 완료")
    print("사용 가능한 기능:")
    print("- basic_statistics: 기본 통계 계산")
    print("- correlation_coefficient: 상관계수 계산")
    print("- linear_regression: 선형 회귀 분석")
    print("- hypothesis_testing: 가설 검정")
    print("- mathematical_expression: 수학 표현식 계산")
    print("- matrix_operations: 행렬 연산")

if __name__ == "__main__":
    main()