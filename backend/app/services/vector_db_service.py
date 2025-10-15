"""
ChromaDB 기반 벡터 데이터베이스 서비스
- 엑셀 통계 데이터를 벡터로 저장
- 의미 기반 검색 및 메타데이터 필터링
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

class VectorDBService:
    def __init__(self, persist_directory: str = None):
        """
        ChromaDB 클라이언트 초기화

        Args:
            persist_directory: 데이터 저장 경로 (기본: backend/data/vector_db)
        """
        if persist_directory is None:
            base_dir = Path(__file__).parent.parent.parent / "data" / "vector_db"
            persist_directory = str(base_dir)

        # ChromaDB 클라이언트 생성
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,  # 텔레메트리 비활성화
                allow_reset=True
            )
        )

        print(f"[VectorDB] ChromaDB 초기화 완료: {persist_directory}")

    def create_or_get_collection(self, stat_name: str):
        """
        통계별 컬렉션 생성 또는 가져오기

        Args:
            stat_name: 통계명 (컬렉션 이름으로 사용)

        Returns:
            ChromaDB Collection 객체
        """
        # 컬렉션 이름 정규화 (특수문자 제거)
        collection_name = self._normalize_collection_name(stat_name)

        try:
            # 기존 컬렉션 가져오기 시도
            collection = self.client.get_collection(name=collection_name)
            print(f"[VectorDB] 기존 컬렉션 로드: {collection_name}")
        except:
            # 없으면 새로 생성
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"stat_name": stat_name}
            )
            print(f"[VectorDB] 새 컬렉션 생성: {collection_name}")

        return collection

    def _normalize_collection_name(self, stat_name: str) -> str:
        """
        컬렉션 이름 정규화 (ChromaDB는 특수문자 제한)

        Args:
            stat_name: 원본 통계명

        Returns:
            정규화된 컬렉션 이름
        """
        # 영문, 숫자, 언더스코어, 하이픈만 허용
        import re
        import hashlib

        # 한글/특수문자가 많으므로 해시 사용
        hash_value = hashlib.md5(stat_name.encode()).hexdigest()[:8]
        normalized = f"stat_{hash_value}"

        return normalized

    def store_stat_data(
        self,
        stat_name: str,
        stat_data: List[Any],
        metadata: Any = None
    ) -> int:
        """
        통계 데이터를 벡터 DB에 저장

        Args:
            stat_name: 통계명
            stat_data: StatData 객체 리스트
            metadata: StatMetadata 객체

        Returns:
            저장된 행 개수
        """
        collection = self.create_or_get_collection(stat_name)

        # 기존 데이터 삭제 (새로 저장)
        try:
            collection.delete(where={})
            print(f"[VectorDB] 기존 데이터 삭제 완료")
        except:
            pass

        documents = []
        metadatas = []
        ids = []

        for idx, data_item in enumerate(stat_data):
            if not hasattr(data_item, 'data') or not data_item.data:
                continue

            # 텍스트 생성 (ChromaDB가 임베딩)
            text_parts = []
            item_metadata = {}

            # 기본 정보
            year = getattr(data_item, 'year', None)
            table_name = getattr(data_item, 'table_name', '')
            period_text = getattr(data_item, 'period_text', '')

            if year:
                text_parts.append(f"{year}년")
                item_metadata['year'] = year

            if table_name:
                text_parts.append(f"[{table_name}]")
                item_metadata['table_name'] = table_name

            if period_text:
                item_metadata['period'] = period_text

            # 데이터 파싱
            data_dict = data_item.data

            # 숫자 값 추출
            numeric_values = {}
            text_values = []

            for key, value in data_dict.items():
                # 특수 키 건너뛰기
                if key.startswith('_') or key.startswith('Unnamed'):
                    # Unnamed 컬럼도 값이 의미있으면 포함
                    if value and str(value).strip() and value != ' ':
                        text_values.append(str(value))
                    continue

                # 값 처리
                if value is not None and str(value).strip() and str(value) != ' ':
                    # 숫자 변환 시도
                    try:
                        # 쉼표 제거 후 숫자 변환
                        numeric_val = float(str(value).replace(',', ''))
                        numeric_values[key] = numeric_val
                        text_parts.append(f"{key}: {value}")
                    except ValueError:
                        # 숫자가 아니면 텍스트로
                        text_values.append(f"{key}: {value}")
                        text_parts.append(f"{key}: {value}")

            # 메타데이터에 숫자 정보 저장 (필터링용)
            if numeric_values:
                # 첫 번째 숫자 값만 메타데이터에 (ChromaDB 제한)
                first_numeric_key = list(numeric_values.keys())[0]
                item_metadata['first_value'] = numeric_values[first_numeric_key]
                item_metadata['first_key'] = first_numeric_key

            # 텍스트 값 추가
            if text_values:
                text_parts.extend(text_values)

            # 최종 텍스트 생성
            document_text = " ".join(text_parts)

            if not document_text.strip():
                continue

            # 저장용 데이터 추가
            documents.append(document_text)
            metadatas.append(item_metadata)
            ids.append(f"{stat_name}_{idx}")

        # ChromaDB에 저장
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"[VectorDB] {len(documents)}개 데이터 저장 완료: {stat_name}")

        return len(documents)

    def search_relevant_data(
        self,
        stat_name: str,
        query: str,
        n_results: int = 10,
        where: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        질문과 관련된 데이터 검색

        Args:
            stat_name: 통계명
            query: 검색 질문
            n_results: 반환할 결과 개수
            where: 메타데이터 필터 조건 (예: {"year": 2025})

        Returns:
            검색 결과 (documents, metadatas, distances)
        """
        try:
            collection = self.create_or_get_collection(stat_name)

            # 검색 실행
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )

            print(f"[VectorDB] 검색 완료: {query[:50]}... → {len(results['documents'][0])}개 결과")

            return {
                "documents": results['documents'][0] if results['documents'] else [],
                "metadatas": results['metadatas'][0] if results['metadatas'] else [],
                "distances": results['distances'][0] if results.get('distances') else []
            }

        except Exception as e:
            print(f"[VectorDB] 검색 오류: {e}")
            return {
                "documents": [],
                "metadatas": [],
                "distances": []
            }

    def delete_collection(self, stat_name: str):
        """
        컬렉션 삭제

        Args:
            stat_name: 통계명
        """
        collection_name = self._normalize_collection_name(stat_name)
        try:
            self.client.delete_collection(name=collection_name)
            print(f"[VectorDB] 컬렉션 삭제: {collection_name}")
        except Exception as e:
            print(f"[VectorDB] 컬렉션 삭제 실패: {e}")

    def get_collection_stats(self, stat_name: str) -> Dict[str, Any]:
        """
        컬렉션 통계 조회

        Args:
            stat_name: 통계명

        Returns:
            컬렉션 정보 (문서 개수 등)
        """
        try:
            collection = self.create_or_get_collection(stat_name)
            count = collection.count()

            return {
                "stat_name": stat_name,
                "document_count": count,
                "exists": True
            }
        except Exception as e:
            return {
                "stat_name": stat_name,
                "document_count": 0,
                "exists": False,
                "error": str(e)
            }


# 싱글톤 인스턴스
vector_db_service = VectorDBService()
