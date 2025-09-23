"""
통계명 동적 저장 서비스
최신통계목록에서 수집된 통계명을 동적으로 저장하고 관리
"""
import json
import os
from typing import Dict, Optional


class StatNameStorage:
    def __init__(self, storage_file: str = "data/stat_name_mapping.json"):
        """
        통계명 저장소 초기화

        Args:
            storage_file: 통계명 매핑을 저장할 JSON 파일 경로
        """
        self.storage_file = storage_file
        self.ensure_storage_directory()
        self._stat_name_map = self.load_stat_name_map()

    def ensure_storage_directory(self):
        """저장 디렉토리가 존재하는지 확인하고 없으면 생성"""
        storage_dir = os.path.dirname(self.storage_file)
        if storage_dir and not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)

    def load_stat_name_map(self) -> Dict[str, str]:
        """저장된 통계명 매핑 로드"""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                # 기본 매핑으로 초기화 (기존 하드코딩된 값들)
                default_map = {}
                self.save_stat_name_map(default_map)
                return default_map
        except Exception as e:
            print(f"통계명 매핑 로드 실패: {e}")
            return {}

    def save_stat_name_map(self, stat_map: Dict[str, str]):
        """통계명 매핑 저장"""
        try:
            with open(self.storage_file, 'w', encoding='utf-8') as f:
                json.dump(stat_map, f, ensure_ascii=False, indent=2)
            self._stat_name_map = stat_map
            print(f"통계명 매핑 저장 완료: {len(stat_map)}개 항목")
        except Exception as e:
            print(f"통계명 매핑 저장 실패: {e}")

    def store_stat_name(self, hrsid: str, stat_name: str):
        """
        새로운 통계명 저장

        Args:
            hrsid: 통계 ID (hRsId 파라미터 값)
            stat_name: 통계명 (최신통계목록에서 가져온 제목)
        """
        if hrsid and stat_name:
            self._stat_name_map[hrsid] = stat_name
            self.save_stat_name_map(self._stat_name_map)
            print(f"새로운 통계명 저장: {hrsid} -> {stat_name}")

    def get_stat_name(self, hrsid: str) -> Optional[str]:
        """
        저장된 통계명 조회

        Args:
            hrsid: 통계 ID

        Returns:
            통계명 또는 None
        """
        return self._stat_name_map.get(hrsid)

    def has_stat_name(self, hrsid: str) -> bool:
        """해당 ID의 통계명이 저장되어 있는지 확인"""
        return hrsid in self._stat_name_map

    def get_all_mappings(self) -> Dict[str, str]:
        """모든 통계명 매핑 반환"""
        return self._stat_name_map.copy()

    def update_stat_name(self, hrsid: str, new_stat_name: str):
        """기존 통계명 업데이트"""
        if hrsid in self._stat_name_map:
            old_name = self._stat_name_map[hrsid]
            self._stat_name_map[hrsid] = new_stat_name
            self.save_stat_name_map(self._stat_name_map)
            print(f"통계명 업데이트: {hrsid} - {old_name} -> {new_stat_name}")
        else:
            self.store_stat_name(hrsid, new_stat_name)

    def remove_stat_name(self, hrsid: str) -> bool:
        """통계명 매핑 삭제"""
        if hrsid in self._stat_name_map:
            removed_name = self._stat_name_map.pop(hrsid)
            self.save_stat_name_map(self._stat_name_map)
            print(f"통계명 매핑 삭제: {hrsid} -> {removed_name}")
            return True
        return False


# 전역 인스턴스
stat_name_storage = StatNameStorage()