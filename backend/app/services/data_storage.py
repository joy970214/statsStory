import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from app.models.stat_models import StatData, StatMetadata

class DataStorageService:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), '../../data')
        self.metadata_dir = os.path.join(self.data_dir, 'metadata')
        self.stats_dir = os.path.join(self.data_dir, 'statistics')
        
        # 디렉토리 생성
        os.makedirs(self.metadata_dir, exist_ok=True)
        os.makedirs(self.stats_dir, exist_ok=True)
    
    def _get_cache_key(self, stat_url: str) -> str:
        """URL을 기반으로 고유한 캐시 키 생성"""
        return hashlib.md5(stat_url.encode()).hexdigest()[:12]
    
    def _get_metadata_path(self, cache_key: str) -> str:
        """메타데이터 파일 경로"""
        return os.path.join(self.metadata_dir, f"{cache_key}_metadata.json")
    
    def _get_stats_path(self, cache_key: str) -> str:
        """통계 데이터 파일 경로"""
        return os.path.join(self.stats_dir, f"{cache_key}_stats.json")
    
    def save_metadata(self, stat_url: str, metadata: StatMetadata) -> str:
        """메타데이터 저장"""
        cache_key = self._get_cache_key(stat_url)
        file_path = self._get_metadata_path(cache_key)
        
        data = {
            'cache_key': cache_key,
            'stat_url': stat_url,
            'saved_at': datetime.now().isoformat(),
            'metadata': {
                'id': metadata.id,
                'title': metadata.title,
                'purpose': metadata.purpose,
                'frequency': metadata.frequency,
                'department': metadata.department,
                'contact': metadata.contact,
                'keywords': metadata.keywords,
                'related_terms': metadata.related_terms
            }
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"메타데이터 저장 완료: {cache_key} -> {metadata.title}")
        return cache_key
    
    def save_statistics(self, stat_url: str, stat_data: List[StatData]) -> str:
        """통계 데이터 저장"""
        cache_key = self._get_cache_key(stat_url)
        file_path = self._get_stats_path(cache_key)
        
        data = {
            'cache_key': cache_key,
            'stat_url': stat_url,
            'saved_at': datetime.now().isoformat(),
            'data_count': len(stat_data),
            'statistics': []
        }
        
        for stat in stat_data:
            data['statistics'].append({
                'year': stat.year,
                'data': stat.data
            })
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"통계 데이터 저장 완료: {cache_key} -> {len(stat_data)}년치")
        return cache_key
    
    def load_metadata(self, stat_url: str, max_age_hours: int = 24) -> Optional[StatMetadata]:
        """저장된 메타데이터 로드 (24시간 이내)"""
        cache_key = self._get_cache_key(stat_url)
        file_path = self._get_metadata_path(cache_key)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 저장 시간 확인
            saved_at = datetime.fromisoformat(data['saved_at'])
            if datetime.now() - saved_at > timedelta(hours=max_age_hours):
                print(f"메타데이터 캐시 만료: {cache_key}")
                return None
            
            metadata_dict = data['metadata']
            metadata = StatMetadata(
                id=metadata_dict['id'],
                title=metadata_dict['title'],
                purpose=metadata_dict['purpose'],
                frequency=metadata_dict['frequency'],
                department=metadata_dict['department'],
                contact=metadata_dict['contact'],
                keywords=metadata_dict['keywords'],
                related_terms=metadata_dict['related_terms']
            )
            
            print(f"메타데이터 캐시 로드 성공: {cache_key} -> {metadata.title}")
            return metadata
            
        except Exception as e:
            print(f"메타데이터 로드 오류: {e}")
            return None
    
    def load_statistics(self, stat_url: str, max_age_hours: int = 24) -> Optional[List[StatData]]:
        """저장된 통계 데이터 로드 (24시간 이내)"""
        cache_key = self._get_cache_key(stat_url)
        file_path = self._get_stats_path(cache_key)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 저장 시간 확인
            saved_at = datetime.fromisoformat(data['saved_at'])
            if datetime.now() - saved_at > timedelta(hours=max_age_hours):
                print(f"통계 데이터 캐시 만료: {cache_key}")
                return None
            
            stat_data = []
            for stat_dict in data['statistics']:
                stat_data.append(StatData(
                    year=stat_dict['year'],
                    data=stat_dict['data']
                ))
            
            print(f"통계 데이터 캐시 로드 성공: {cache_key} -> {len(stat_data)}년치")
            return stat_data
            
        except Exception as e:
            print(f"통계 데이터 로드 오류: {e}")
            return None
    
    def get_cached_data(self, stat_url: str, max_age_hours: int = 24) -> Tuple[Optional[StatMetadata], Optional[List[StatData]]]:
        """메타데이터와 통계 데이터를 함께 로드"""
        metadata = self.load_metadata(stat_url, max_age_hours)
        statistics = self.load_statistics(stat_url, max_age_hours)
        return metadata, statistics
    
    def save_complete_data(self, stat_url: str, metadata: StatMetadata, stat_data: List[StatData]) -> str:
        """메타데이터와 통계 데이터를 함께 저장"""
        cache_key = self._get_cache_key(stat_url)
        self.save_metadata(stat_url, metadata)
        self.save_statistics(stat_url, stat_data)
        print(f"전체 데이터 저장 완료: {cache_key}")
        return cache_key
    
    def list_cached_files(self) -> Dict[str, List[str]]:
        """저장된 캐시 파일 목록"""
        metadata_files = os.listdir(self.metadata_dir) if os.path.exists(self.metadata_dir) else []
        stats_files = os.listdir(self.stats_dir) if os.path.exists(self.stats_dir) else []
        
        return {
            'metadata_files': metadata_files,
            'statistics_files': stats_files,
            'total_cache_keys': len(set([f.split('_')[0] for f in metadata_files + stats_files]))
        }
    
    def clear_expired_cache(self, max_age_hours: int = 24) -> int:
        """만료된 캐시 파일 삭제"""
        deleted_count = 0
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        for directory in [self.metadata_dir, self.stats_dir]:
            if not os.path.exists(directory):
                continue
                
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    saved_at = datetime.fromisoformat(data['saved_at'])
                    if saved_at < cutoff_time:
                        os.remove(file_path)
                        deleted_count += 1
                        print(f"만료된 캐시 파일 삭제: {filename}")
                        
                except Exception as e:
                    print(f"캐시 파일 확인 오류: {filename} -> {e}")
        
        return deleted_count