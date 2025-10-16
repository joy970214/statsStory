"""
ChromaDB 기반 벡터 데이터베이스 서비스
- 엑셀 통계 데이터를 벡터로 저장
- 의미 기반 검색 및 메타데이터 필터링
- 동적 테이블 구조 분석 및 자연어 생성
"""
import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
from pathlib import Path
import json

# 새로 추가된 분석기 및 생성기
from app.services.table_structure_analyzer import TableStructureAnalyzer
from app.services.natural_language_generator import NaturalLanguageGenerator

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

        # 분석기 및 생성기 초기화
        self.analyzer = TableStructureAnalyzer()
        self.generator = NaturalLanguageGenerator()

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
        통계 데이터를 벡터 DB에 저장 (개선된 버전)
        - 동적 테이블 구조 분석
        - 자연어 텍스트 생성
        - 연도-카테고리 단위 청킹

        Args:
            cache_key: 캐시 키 (컬렉션 식별자)
            stat_name: 통계명
            stat_data: StatData 객체 리스트
            metadata: StatMetadata 객체

        Returns:
            저장된 청크 개수
        """
        collection = self.create_or_get_collection(cache_key, stat_name)

        # 기존 데이터 삭제 (새로 저장)
        try:
            collection.delete(where={})
            print(f"[VectorDB] 기존 데이터 삭제 완료")
        except:
            pass

        # StatData 객체를 Dict로 변환
        statistics_list = []
        for data_item in stat_data:
            if not hasattr(data_item, 'data') or not data_item.data:
                continue

            statistics_list.append({
                'year': getattr(data_item, 'year', 2025),
                'data': data_item.data,
                'table_name': getattr(data_item, 'table_name', ''),
                'period_text': getattr(data_item, 'period_text', '')
            })

        if not statistics_list:
            print(f"[VectorDB] 저장할 데이터가 없음")
            return 0

        # 1단계: 테이블 구조 분석
        print(f"[VectorDB] 테이블 구조 분석 중...")
        structure = self.analyzer.analyze(statistics_list)
        table_name = structure.get('table_name', stat_name)

        # 2단계: 데이터 행만 추출
        data_rows = structure.get('data_rows', [])
        if not data_rows:
            print(f"[VectorDB] 데이터 행이 없음")
            return 0

        # 3단계: 연도-카테고리 단위로 그룹화
        year_category_groups = self._group_by_year_category(data_rows, structure)

        # 4단계: 각 그룹을 자연어 청크로 변환
        documents = []
        metadatas = []
        ids = []

        chunk_idx = 0
        for (year, category), rows in year_category_groups.items():
            # 자연어 텍스트 생성
            natural_text = self.generator.generate(
                year=str(year),
                category=category,
                rows=rows,
                structure=structure,
                table_name=table_name
            )

            if not natural_text.strip():
                continue

            # 메타데이터 구성
            chunk_metadata = {
                'year': year,
                'category': category,
                'table_name': table_name,
                'cache_key': cache_key,
                'row_count': len(rows)
            }

            # 추가 메타데이터 (구조 정보)
            if structure.get('data_structure', {}).get('is_timeseries'):
                chunk_metadata['data_type'] = 'timeseries'
            elif structure.get('data_structure', {}).get('is_geographic'):
                chunk_metadata['data_type'] = 'geographic'
            else:
                chunk_metadata['data_type'] = 'categorical'

            # 저장
            documents.append(natural_text)
            metadatas.append(chunk_metadata)
            ids.append(f"{cache_key}_chunk_{chunk_idx}")
            chunk_idx += 1

        # ChromaDB에 저장
        if documents:
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"[VectorDB] {len(documents)}개 청크 저장 완료: {stat_name}")
            print(f"[VectorDB] 샘플 텍스트: {documents[0][:200]}...")
        else:
            print(f"[VectorDB] 생성된 문서가 없음")

        return len(documents)

    def _group_by_year_category(self, data_rows: List[Dict], structure: Dict) -> Dict[tuple, List[Dict]]:
        """
        데이터를 연도-카테고리 단위로 그룹화

        Args:
            data_rows: 데이터 행 리스트
            structure: 테이블 구조 정보

        Returns:
            {(year, category): [rows]} 형태의 딕셔너리
        """
        groups = {}

        # 컬럼 정보 추출
        temporal_col = structure.get('data_structure', {}).get('temporal_column')
        category_col = structure.get('data_structure', {}).get('category_column')

        for row in data_rows:
            data = row.get('data', {})

            # 연도 추출
            if temporal_col and temporal_col in data:
                year_value = data.get(temporal_col)
                try:
                    year = int(str(year_value))
                except:
                    year = 2025  # 기본값
            else:
                # 첫 번째 컬럼에서 연도 추출 시도
                first_col_value = list(data.values())[0] if data else None
                try:
                    year = int(str(first_col_value))
                except:
                    year = 2025

            # 카테고리 추출
            if category_col and category_col in data:
                category = str(data.get(category_col, '기타'))
            else:
                # 두 번째 컬럼을 카테고리로 간주
                col_list = list(data.values())
                category = str(col_list[1]) if len(col_list) > 1 else '기타'

            # 그룹에 추가
            key = (year, category)
            if key not in groups:
                groups[key] = []
            groups[key].append(row)

        print(f"[VectorDB] {len(groups)}개 그룹 생성 (연도-카테고리 단위)")
        return groups

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
