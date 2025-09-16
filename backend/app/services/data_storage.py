import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from app.models.stat_models import StatData, StatMetadata

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    print("pandas not installed - Excel 기능을 사용하려면 'pip install pandas openpyxl' 실행")
    HAS_PANDAS = False

class DataStorageService:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), '../../data')
        self.metadata_dir = os.path.join(self.data_dir, 'metadata')
        self.stats_dir = os.path.join(self.data_dir, 'statistics')
        self.excel_dir = os.path.join(self.data_dir, 'excel')
        
        # 디렉토리 생성
        os.makedirs(self.metadata_dir, exist_ok=True)
        os.makedirs(self.stats_dir, exist_ok=True)
        os.makedirs(self.excel_dir, exist_ok=True)
    
    def _get_cache_key(self, stat_url: str) -> str:
        """URL을 기반으로 고유한 캐시 키 생성"""
        return hashlib.md5(stat_url.encode()).hexdigest()[:12]
    
    def _get_metadata_path(self, cache_key: str) -> str:
        """메타데이터 파일 경로"""
        return os.path.join(self.metadata_dir, f"{cache_key}_metadata.json")
    
    def _get_stats_path(self, cache_key: str) -> str:
        """통계 데이터 파일 경로"""
        return os.path.join(self.stats_dir, f"{cache_key}_stats.json")
    
    def _get_excel_path(self, cache_key: str) -> str:
        """Excel 파일 경로"""
        return os.path.join(self.excel_dir, f"{cache_key}_data.xlsx")
    
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
            stat_dict = {
                'year': stat.year,
                'data': stat.data
            }
            # 추가 필드들도 저장
            if hasattr(stat, 'table_name') and stat.table_name:
                stat_dict['table_name'] = stat.table_name
            if hasattr(stat, 'period_text') and stat.period_text:
                stat_dict['period_text'] = stat.period_text
            if hasattr(stat, 'period_type') and stat.period_type:
                stat_dict['period_type'] = stat.period_type
            if hasattr(stat, 'raw_data_count') and stat.raw_data_count:
                stat_dict['raw_data_count'] = stat.raw_data_count
            if hasattr(stat, 'collection_status') and stat.collection_status:
                stat_dict['collection_status'] = stat.collection_status
            if hasattr(stat, 'data_quality_score') and stat.data_quality_score:
                stat_dict['data_quality_score'] = stat.data_quality_score

            data['statistics'].append(stat_dict)
        
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
                    data=stat_dict['data'],
                    table_name=stat_dict.get('table_name'),
                    period_text=stat_dict.get('period_text'),
                    period_type=stat_dict.get('period_type'),
                    raw_data_count=stat_dict.get('raw_data_count'),
                    collection_status=stat_dict.get('collection_status', 'success'),
                    data_quality_score=stat_dict.get('data_quality_score')
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
        """메타데이터와 통계 데이터를 함께 저장 (JSON + Excel)"""
        cache_key = self._get_cache_key(stat_url)
        
        # JSON 형태로 저장 (기존 방식)
        self.save_metadata(stat_url, metadata)
        self.save_statistics(stat_url, stat_data)
        
        # Excel 형태로도 저장
        excel_path = self.save_to_excel(stat_url, metadata, stat_data)
        if excel_path:
            print(f"전체 데이터 저장 완료: {cache_key} (JSON + Excel)")
        else:
            print(f"전체 데이터 저장 완료: {cache_key} (JSON만)")
        
        return cache_key
    
    def list_cached_files(self) -> Dict[str, List[str]]:
        """저장된 캐시 파일 목록"""
        metadata_files = os.listdir(self.metadata_dir) if os.path.exists(self.metadata_dir) else []
        stats_files = os.listdir(self.stats_dir) if os.path.exists(self.stats_dir) else []
        excel_files = os.listdir(self.excel_dir) if os.path.exists(self.excel_dir) else []
        
        return {
            'metadata_files': metadata_files,
            'statistics_files': stats_files,
            'excel_files': excel_files,
            'total_cache_keys': len(set([f.split('_')[0] for f in metadata_files + stats_files + excel_files]))
        }
    
    def clear_expired_cache(self, max_age_hours: int = 24) -> int:
        """만료된 캐시 파일 삭제"""
        deleted_count = 0
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        for directory in [self.metadata_dir, self.stats_dir, self.excel_dir]:
            if not os.path.exists(directory):
                continue
                
            for filename in os.listdir(directory):
                file_path = os.path.join(directory, filename)
                try:
                    # Excel 파일의 경우 파일 시스템 시간 사용
                    if directory == self.excel_dir:
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if file_mtime < cutoff_time:
                            os.remove(file_path)
                            deleted_count += 1
                            print(f"만료된 Excel 파일 삭제: {filename}")
                    else:
                        # JSON 파일의 경우 내부 데이터 사용
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
    
    def save_to_excel(self, stat_url: str, metadata: StatMetadata, stat_data: List[StatData]) -> str:
        """메타데이터와 통계 데이터를 Excel 파일로 저장"""
        if not HAS_PANDAS:
            print("pandas가 설치되지 않아 Excel 저장을 건너뜁니다.")
            return ""
        
        try:
            cache_key = self._get_cache_key(stat_url)
            excel_path = self._get_excel_path(cache_key)
            
            # Excel 파일에 여러 시트로 저장
            with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
                # 1. 메타데이터 시트
                metadata_df = pd.DataFrame([{
                    '항목': '통계 ID',
                    '내용': metadata.id
                }, {
                    '항목': '제목',
                    '내용': metadata.title
                }, {
                    '항목': '목적',
                    '내용': metadata.purpose
                }, {
                    '항목': '주기',
                    '내용': metadata.frequency
                }, {
                    '항목': '작성기관',
                    '내용': metadata.department
                }, {
                    '항목': '담당자',
                    '내용': metadata.contact
                }, {
                    '항목': '키워드',
                    '내용': ', '.join(metadata.keywords) if metadata.keywords else ''
                }, {
                    '항목': 'URL',
                    '내용': stat_url
                }, {
                    '항목': '저장 시간',
                    '내용': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }])
                
                metadata_df.to_excel(writer, sheet_name='메타데이터', index=False)
                
                # 2. 통계 데이터 시트
                if stat_data:
                    # 통계 데이터를 DataFrame으로 변환
                    stats_records = []
                    for stat in stat_data:
                        base_record = {
                            '연도': stat.year,
                            '테이블명': getattr(stat, 'table_name', '기본 테이블')
                        }
                        
                        # 데이터 필드들을 컬럼으로 추가
                        if stat.data:
                            for key, value in stat.data.items():
                                # 복잡한 데이터 구조를 문자열로 변환
                                if isinstance(value, (dict, list)):
                                    base_record[key] = str(value)
                                else:
                                    base_record[key] = value
                        
                        stats_records.append(base_record)
                    
                    stats_df = pd.DataFrame(stats_records)
                    stats_df.to_excel(writer, sheet_name='통계데이터', index=False)
                
                # 3. 관련 용어 시트 (있는 경우)
                if metadata.related_terms:
                    terms_records = []
                    for term, definition in metadata.related_terms.items():
                        terms_records.append({
                            '용어': term,
                            '정의': definition
                        })
                    
                    if terms_records:
                        terms_df = pd.DataFrame(terms_records)
                        terms_df.to_excel(writer, sheet_name='관련용어', index=False)
            
            print(f"Excel 파일 저장 완료: {cache_key} -> {excel_path}")
            return excel_path
            
        except Exception as e:
            print(f"Excel 저장 오류: {e}")
            return ""
    
    def load_from_excel(self, stat_url: str) -> Tuple[Optional[StatMetadata], Optional[List[StatData]]]:
        """Excel 파일에서 데이터 로드"""
        if not HAS_PANDAS:
            return None, None
        
        try:
            cache_key = self._get_cache_key(stat_url)
            excel_path = self._get_excel_path(cache_key)
            
            if not os.path.exists(excel_path):
                return None, None
            
            # Excel 파일 읽기
            with pd.ExcelFile(excel_path) as xls:
                # 메타데이터 읽기
                metadata_df = pd.read_excel(xls, sheet_name='메타데이터')
                metadata_dict = dict(zip(metadata_df['항목'], metadata_df['내용']))
                
                metadata = StatMetadata(
                    id=metadata_dict.get('통계 ID', ''),
                    title=metadata_dict.get('제목', ''),
                    purpose=metadata_dict.get('목적', ''),
                    frequency=metadata_dict.get('주기', ''),
                    department=metadata_dict.get('작성기관', ''),
                    contact=metadata_dict.get('담당자', ''),
                    keywords=metadata_dict.get('키워드', '').split(', ') if metadata_dict.get('키워드') else [],
                    related_terms={}
                )
                
                # 통계 데이터 읽기
                stat_data = []
                if '통계데이터' in xls.sheet_names:
                    stats_df = pd.read_excel(xls, sheet_name='통계데이터')
                    
                    for _, row in stats_df.iterrows():
                        year = row.get('연도', 0)
                        table_name = row.get('테이블명', '기본 테이블')
                        
                        # 연도와 테이블명을 제외한 나머지 데이터
                        data = {}
                        for col, val in row.items():
                            if col not in ['연도', '테이블명'] and pd.notna(val):
                                data[col] = val
                        
                        stat_data.append(StatData(
                            year=int(year) if pd.notna(year) else 0,
                            data=data,
                            table_name=table_name
                        ))
                
                print(f"Excel 파일 로드 성공: {cache_key} -> {len(stat_data)}년치")
                return metadata, stat_data
                
        except Exception as e:
            print(f"Excel 로드 오류: {e}")
            return None, None
    
    def find_data_by_name(self, stat_name: str, max_age_hours: int = 24) -> Tuple[Optional[StatMetadata], Optional[List[StatData]], Optional[str]]:
        """통계명으로 캐시된 데이터를 찾기"""
        try:
            # 모든 메타데이터 파일을 확인
            if not os.path.exists(self.metadata_dir):
                return None, None, None
                
            for filename in os.listdir(self.metadata_dir):
                if not filename.endswith('_metadata.json'):
                    continue
                    
                file_path = os.path.join(self.metadata_dir, filename)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 저장 시간 확인
                    saved_at = datetime.fromisoformat(data['saved_at'])
                    if datetime.now() - saved_at > timedelta(hours=max_age_hours):
                        continue
                    
                    # stat_name이 제목에 포함되어 있는지 확인
                    metadata_dict = data['metadata']
                    title = metadata_dict.get('title', '')
                    
                    # 더 유연한 매칭 (키워드 매칭)
                    stat_name_lower = stat_name.lower()
                    title_lower = title.lower()
                    
                    # URL에서 키워드 추출해서 매칭
                    url = data['stat_url']
                    url_keywords = []
                    if 'hRsId=' in url:
                        url_keywords.append(f"hRsId={url.split('hRsId=')[1].split('&')[0]}")
                    if 'hFormId=' in url:
                        url_keywords.append(f"hFormId={url.split('hFormId=')[1].split('&')[0]}")
                    
                    # 부서 정보 확인
                    department = metadata_dict.get('department', '').lower()
                    
                    # 다양한 매칭 조건
                    match_conditions = [
                        stat_name_lower in title_lower,  # 기본 매칭
                        title_lower in stat_name_lower,  # 반대 매칭
                        # 키워드 매칭 (주택건설 관련)
                        ('주택' in stat_name_lower and '주택' in title_lower),
                        ('건설' in stat_name_lower and '착공' in title_lower),  # 건설과 착공 연관
                        ('착공' in stat_name_lower and ('착공' in title_lower or '건설' in title_lower)),
                        # 부서 기반 매칭 (주택 관련 부서)
                        ('주택' in stat_name_lower and '주택' in department),
                        ('건설' in stat_name_lower and '주택' in department),
                        ('착공' in stat_name_lower and '주택' in department),
                        # URL 기반 매칭 (특정 hRsId, hFormId에 대한 매칭)
                        ('주택건설' in stat_name_lower and 'hRsId=471' in url),
                        ('착공' in stat_name_lower and 'hFormId=5386' in url),
                        # URL 키워드 매칭
                        any(keyword in stat_name for keyword in url_keywords)
                    ]
                    
                    if any(match_conditions):
                        # 매칭되는 데이터를 찾았음
                        stat_url = data['stat_url']
                        metadata = StatMetadata(
                            id=metadata_dict.get('id', ''),
                            title=metadata_dict.get('title', ''),
                            purpose=metadata_dict.get('purpose', ''),
                            frequency=metadata_dict.get('frequency', ''),
                            department=metadata_dict.get('department', ''),
                            contact=metadata_dict.get('contact', ''),
                            keywords=metadata_dict.get('keywords', []),
                            related_terms=metadata_dict.get('related_terms', {})
                        )
                        
                        # 해당 URL의 통계 데이터도 로드
                        stat_data = self.load_statistics(stat_url, max_age_hours)
                        
                        print(f"통계명으로 데이터 발견: '{stat_name}' -> {title} ({data['cache_key']})")
                        return metadata, stat_data, stat_url
                        
                except Exception as e:
                    print(f"메타데이터 파일 읽기 오류: {filename} -> {e}")
                    continue
            
            print(f"통계명 '{stat_name}'에 해당하는 캐시 데이터를 찾을 수 없습니다")
            return None, None, None
            
        except Exception as e:
            print(f"stat_name으로 데이터 찾기 오류: {e}")
            return None, None, None