import React, { useState, useEffect } from 'react';
import { statsAPI, OllamaModel } from '../services/api';

interface Props {
  onModelChange?: (modelName: string) => void;
}

const OllamaModelSelector: React.FC<Props> = ({ onModelChange }) => {
  const [models, setModels] = useState<OllamaModel[]>([]);
  const [currentModel, setCurrentModel] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [changing, setChanging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const fetchModels = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await statsAPI.getOllamaModels();
      setModels(data.models);
      setCurrentModel(data.current_model);
    } catch (e: any) {
      setError('Ollama 서버에 연결할 수 없습니다');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) fetchModels();
  }, [isOpen]);

  const handleSelect = async (modelName: string) => {
    if (modelName === currentModel) return;
    setChanging(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await statsAPI.setOllamaModel(modelName);
      setCurrentModel(result.current_model);
      setModels(prev => prev.map(m => ({ ...m, is_current: m.name === result.current_model })));
      setSuccess(`모델이 "${result.current_model}"로 변경되었습니다`);
      onModelChange?.(result.current_model);
      setTimeout(() => setSuccess(null), 3000);
    } catch (e: any) {
      setError(e.response?.data?.detail || '모델 변경 실패');
    } finally {
      setChanging(false);
    }
  };

  return (
    <div style={{ position: 'relative', display: 'inline-block' }}>
      <button
        onClick={() => setIsOpen(prev => !prev)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '6px 12px',
          background: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '8px',
          color: '#94a3b8',
          fontSize: '13px',
          cursor: 'pointer',
          whiteSpace: 'nowrap',
        }}
        title="AI 모델 선택"
      >
        <span style={{ fontSize: '16px' }}>🤖</span>
        <span style={{
          maxWidth: '140px',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          color: '#e2e8f0',
        }}>
          {currentModel || '모델 선택'}
        </span>
        <span style={{ fontSize: '10px', color: '#64748b' }}>{isOpen ? '▲' : '▼'}</span>
      </button>

      {isOpen && (
        <div style={{
          position: 'absolute',
          top: 'calc(100% + 6px)',
          right: 0,
          minWidth: '300px',
          background: '#1e293b',
          border: '1px solid #334155',
          borderRadius: '10px',
          boxShadow: '0 8px 24px rgba(0,0,0,0.4)',
          zIndex: 1000,
          overflow: 'hidden',
        }}>
          <div style={{
            padding: '12px 16px',
            borderBottom: '1px solid #334155',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}>
            <span style={{ color: '#e2e8f0', fontWeight: 600, fontSize: '14px' }}>AI 모델 선택</span>
            <button
              onClick={fetchModels}
              disabled={loading}
              style={{
                background: 'none',
                border: 'none',
                color: '#64748b',
                cursor: 'pointer',
                fontSize: '14px',
              }}
              title="새로고침"
            >
              {loading ? '...' : '↻'}
            </button>
          </div>

          {error && (
            <div style={{ padding: '10px 16px', color: '#f87171', fontSize: '13px', background: '#450a0a22' }}>
              ⚠ {error}
            </div>
          )}
          {success && (
            <div style={{ padding: '10px 16px', color: '#4ade80', fontSize: '13px', background: '#05260a22' }}>
              ✓ {success}
            </div>
          )}

          {loading ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
              불러오는 중...
            </div>
          ) : models.length === 0 ? (
            <div style={{ padding: '20px', textAlign: 'center', color: '#64748b', fontSize: '13px' }}>
              설치된 모델이 없습니다.<br />
              <code style={{ fontSize: '11px', color: '#94a3b8' }}>ollama pull qwen2.5:7b</code>
            </div>
          ) : (
            <div style={{ maxHeight: '280px', overflowY: 'auto' }}>
              {models.map(model => (
                <button
                  key={model.name}
                  onClick={() => handleSelect(model.name)}
                  disabled={changing}
                  style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '10px 16px',
                    background: model.is_current ? '#0f172a' : 'transparent',
                    border: 'none',
                    borderBottom: '1px solid #1e293b',
                    cursor: changing ? 'not-allowed' : 'pointer',
                    textAlign: 'left',
                    transition: 'background 0.15s',
                  }}
                  onMouseEnter={e => { if (!model.is_current) (e.currentTarget as HTMLButtonElement).style.background = '#0f172a88'; }}
                  onMouseLeave={e => { if (!model.is_current) (e.currentTarget as HTMLButtonElement).style.background = 'transparent'; }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                    <span style={{
                      color: model.is_current ? '#38bdf8' : '#e2e8f0',
                      fontSize: '13px',
                      fontWeight: model.is_current ? 600 : 400,
                    }}>
                      {model.is_current && '✓ '}{model.name}
                    </span>
                    <span style={{ color: '#64748b', fontSize: '11px' }}>
                      {model.size_gb} GB
                    </span>
                  </div>
                  {model.is_current && (
                    <span style={{
                      fontSize: '10px',
                      color: '#38bdf8',
                      background: '#0c4a6e44',
                      padding: '2px 6px',
                      borderRadius: '4px',
                    }}>
                      사용 중
                    </span>
                  )}
                </button>
              ))}
            </div>
          )}

          <div style={{
            padding: '10px 16px',
            borderTop: '1px solid #334155',
            color: '#475569',
            fontSize: '11px',
          }}>
            새 모델 설치: <code>ollama pull 모델명</code>
          </div>
        </div>
      )}

      {isOpen && (
        <div
          onClick={() => setIsOpen(false)}
          style={{ position: 'fixed', inset: 0, zIndex: 999 }}
        />
      )}
    </div>
  );
};

export default OllamaModelSelector;
