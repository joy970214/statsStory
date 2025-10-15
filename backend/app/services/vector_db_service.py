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

    def create_or_get_collection(self, cache_key: str, stat_name: str = None):
        """
        통계별 컬렉션 생성 또는 가져오기

        Args:
            cache_key: 캐시 키 (컬렉션 식별자로 사용)
            stat_name: 통계명 (메타데이터용, 선택)

        Returns:
            ChromaDB Collection 객체
        """
        # 컬렉션 이름 정규화
        collection_name = self._normalize_collection_name(cache_key)

        try:
            # 기존 컬렉션 가져오기 시도
            collection = self.client.get_collection(name=collection_name)
            print(f"[VectorDB] 기존 컬렉션 로드: {collection_name}")
        except:
            # 없으면 새로 생성
            metadata = {"cache_key": cache_key}
            if stat_name:
                metadata["stat_name"] = stat_name
            collection = self.client.create_collection(
                name=collection_name,
                metadata=metadata
            )
            print(f"[VectorDB] 새 컬렉션 생성: {collection_name} (cache_key: {cache_key})")

        return collection

    def _normalize_collection_name(self, cache_key: str) -> str:
        """
        컬렉션 이름 정규화 (ChromaDB는 특수문자 제한)

        Args:
            cache_key: 캐시 키

        Returns:
            정규화된 컬렉션 이름
        """
        # cache_key는 이미 영문/숫자로 구성되어 있으므로 그대로 사용
        # cache_ 접두사 추가
        normalized = f"cache_{cache_key}"
        return normalized

    def store_stat_data(
        self,
        cache_key: str,
        stat_name: str,
        stat_data: List[Any],
        metadata: Any = None
    ) -> int:
        """
        통계 데이터를 벡터 DB에 저장

        Args:
            cache_key: 캐시 키 (컬렉션 식별자)
            stat_name: 통계명
            stat_data: StatData 객체 리스트
            metadata: StatMetadata 객체

        Returns:
            저장된 행 개수
        """
        collection = self.create_or_get_collection(cache_key, stat_name)

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
            ids.append(f"{cache_key}_{idx}")

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
        cache_key: str,
        query: str,
        n_results: int = 10,
        where: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        질문과 관련된 데이터 검색

        Args:
            cache_key: 캐시 키
            query: 검색 질문
            n_results: 반환할 결과 개수
            where: 메타데이터 필터 조건 (예: {"year": 2025})

        Returns:
            검색 결과 (documents, metadatas, distances)
        """
        try:
            collection = self.create_or_get_collection(cache_key)

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

    def delete_collection(self, cache_key: str):
        """
        컬렉션 삭제 (실제 파일도 삭제)

        Args:
            cache_key: 캐시 키
        """
        import shutil
        import os

        collection_name = self._normalize_collection_name(cache_key)
        try:
            # persist_dir 경로 확인
            if hasattr(self.client, '_settings'):
                persist_dir = self.client._settings.persist_directory
            elif hasattr(self.client, 'settings'):
                persist_dir = self.client.settings.persist_directory
            else:
                base_dir = Path(__file__).parent.parent.parent / "data" / "vector_db"
                persist_dir = str(base_dir)

            vector_db_path = Path(persist_dir)

            # 1. 먼저 컬렉션이 존재하는지 확인
            collection_exists = False
            collection_uuid = None
            try:
                collection = self.client.get_collection(name=collection_name)
                collection_uuid = str(collection.id)
                collection_exists = True
                print(f"[VectorDB] 컬렉션 존재 확인: {collection_name}, UUID: {collection_uuid}")
            except Exception as e:
                print(f"[VectorDB] 컬렉션이 존재하지 않음 또는 이미 삭제됨: {collection_name}")
                collection_exists = False

            # 2. ChromaDB에서 컬렉션 메타데이터 삭제 먼저 (파일 핸들 해제)
            try:
                if collection_exists:
                    self.client.delete_collection(name=collection_name)
                    print(f"[VectorDB] 컬렉션 메타데이터 삭제 완료: {collection_name} (cache_key: {cache_key})")

                    # 파일 핸들 해제를 위해 잠시 대기
                    import time
                    time.sleep(0.5)  # 500ms 대기
                else:
                    print(f"[VectorDB] 컬렉션이 존재하지 않아 메타데이터 삭제 건너뜀")
            except Exception as delete_error:
                print(f"[VectorDB] 컬렉션 메타데이터 삭제 실패 (무시하고 계속): {delete_error}")

            # 3. UUID 폴더 삭제 (파일 핸들 해제 후)
            deleted_folders = []
            try:
                # 모든 UUID 폴더 확인
                for item in os.listdir(vector_db_path):
                    item_path = vector_db_path / item
                    # UUID 형식의 폴더인지 확인
                    if item_path.is_dir() and len(item) == 36 and item.count('-') == 4:
                        try:
                            # 케이스 1: 컬렉션이 존재했고 UUID 매칭
                            if collection_exists and collection_uuid == item:
                                print(f"[VectorDB] 컬렉션 UUID 매칭: {item}")
                                shutil.rmtree(item_path)
                                deleted_folders.append(str(item_path))
                                print(f"[VectorDB] 벡터 데이터 폴더 삭제 완료: {item_path}")
                                break
                            # 케이스 2: 컬렉션이 없었으면 모든 고아 폴더를 확인
                            else:
                                # SQLite DB에서 이 UUID가 존재하는지 확인
                                is_orphan = True
                                try:
                                    # 모든 컬렉션 목록 가져오기
                                    all_collections = self.client.list_collections()
                                    for col in all_collections:
                                        if str(col.id) == item:
                                            is_orphan = False
                                            break
                                except:
                                    pass

                                # 고아 폴더면 삭제
                                if is_orphan:
                                    print(f"[VectorDB] 고아 폴더 발견: {item}")
                                    shutil.rmtree(item_path)
                                    deleted_folders.append(str(item_path))
                                    print(f"[VectorDB] 고아 폴더 삭제 완료: {item_path}")
                        except Exception as folder_error:
                            print(f"[VectorDB] 폴더 삭제 중 오류 ({item}): {folder_error}")
            except Exception as scan_error:
                print(f"[VectorDB] 폴더 스캔 중 오류: {scan_error}")

            # 3. 삭제 결과 로깅
            if deleted_folders:
                print(f"[VectorDB] 총 {len(deleted_folders)}개 폴더 삭제됨")
            else:
                print(f"[VectorDB] 삭제된 폴더 없음 (이미 삭제됨 or 존재하지 않음)")

        except Exception as e:
            print(f"[VectorDB] 컬렉션 삭제 실패: {e}")
            import traceback
            traceback.print_exc()

    def get_collection_stats(self, cache_key: str) -> Dict[str, Any]:
        """
        컬렉션 통계 조회

        Args:
            cache_key: 캐시 키

        Returns:
            컬렉션 정보 (문서 개수 등)
        """
        try:
            collection = self.create_or_get_collection(cache_key)
            count = collection.count()

            return {
                "cache_key": cache_key,
                "document_count": count,
                "exists": True
            }
        except Exception as e:
            return {
                "cache_key": cache_key,
                "document_count": 0,
                "exists": False,
                "error": str(e)
            }

    def get_all_data_for_analysis(self, cache_key: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        AI 분석을 위해 ChromaDB에서 데이터 샘플 가져오기

        Args:
            cache_key: 캐시 키
            limit: 최대 반환 개수 (None이면 전체)

        Returns:
            데이터 샘플 리스트 (document, year, table_name, metadata 포함)
        """
        try:
            collection = self.create_or_get_collection(cache_key)

            # 전체 데이터 가져오기
            if limit is None:
                # limit 없이 모든 데이터 가져오기
                total_count = collection.count()
                results = collection.get(
                    limit=total_count if total_count > 0 else 1,
                    include=['documents', 'metadatas']
                )
            else:
                # limit 지정된 경우
                results = collection.get(
                    limit=limit,
                    include=['documents', 'metadatas']
                )

            if not results or not results.get('documents'):
                print(f"[VectorDB] 데이터 없음: {cache_key}")
                return []

            # 데이터 구조화
            data_samples = []
            for doc, meta in zip(results['documents'], results['metadatas']):
                data_samples.append({
                    "document": doc,
                    "year": meta.get('year'),
                    "table_name": meta.get('table_name', ''),
                    "metadata": meta
                })

            print(f"[VectorDB] AI 분석용 데이터 샘플 {len(data_samples)}개 추출")
            return data_samples

        except Exception as e:
            print(f"[VectorDB] 데이터 추출 오류: {e}")
            return []


# 싱글톤 인스턴스
vector_db_service = VectorDBService()
