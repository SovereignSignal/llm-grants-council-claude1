import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import './SubmitApplication.css';

export default function SubmitApplication() {
  const navigate = useNavigate();
  const [inputMode, setInputMode] = useState('url');
  const [url, setUrl] = useState('');
  const [text, setText] = useState('');
  const [file, setFile] = useState(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [progress, setProgress] = useState([]);
  const [error, setError] = useState(null);
  const [applicationId, setApplicationId] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setProgress([]);
    setApplicationId(null);
    setIsSubmitting(true);

    let content = '';
    if (inputMode === 'url') {
      content = `Please review this grant application: ${url}`;
    } else if (inputMode === 'paste') {
      content = text;
    } else if (inputMode === 'upload' && file) {
      content = await file.text();
    }

    if (!content.trim()) {
      setError('Please provide application content');
      setIsSubmitting(false);
      return;
    }

    let capturedAppId = null;

    try {
      await api.submitApplicationStream(content, 'web', null, (eventType, event) => {
        setProgress(prev => [...prev, { type: eventType, ...event }]);

        // Capture application_id from stage1_complete
        if (eventType === 'stage1_complete' && event.data?.application_id) {
          capturedAppId = event.data.application_id;
          setApplicationId(capturedAppId);
        }

        // Redirect on complete
        if (eventType === 'complete') {
          const appId = capturedAppId || applicationId;
          if (appId) {
            setTimeout(() => {
              navigate(`/applications/${appId}`);
            }, 1500);
          }
        }

        if (eventType === 'error') {
          setError(event.message || 'An error occurred');
          setIsSubmitting(false);
        }
      });
    } catch (err) {
      setError(err.message);
      setIsSubmitting(false);
    }
  };

  const handleFileDrop = (e) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files[0];
    if (droppedFile) {
      setFile(droppedFile);
    }
  };

  const handleFileSelect = (e) => {
    const selectedFile = e.target.files[0];
    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  const getStageLabel = (type) => {
    const labels = {
      'stage1_start': 'Parsing application...',
      'stage1_complete': 'Application parsed',
      'stage2_start': 'Agents evaluating...',
      'stage2_complete': 'Evaluations complete',
      'stage3_start': 'Agents deliberating...',
      'stage3_complete': 'Deliberation complete',
      'stage4_start': 'Voting...',
      'stage4_complete': 'Decision made',
      'complete': 'Processing complete!',
    };
    return labels[type] || type;
  };

  return (
    <div className="submit-application">
      <div className="page-header">
        <h1>Submit Grant Application</h1>
        <p className="subtitle">Submit a new application for council review</p>
      </div>

      <div className="submit-card">
        <div className="input-tabs">
          <button
            className={`tab ${inputMode === 'url' ? 'active' : ''}`}
            onClick={() => setInputMode('url')}
            disabled={isSubmitting}
          >
            URL
          </button>
          <button
            className={`tab ${inputMode === 'paste' ? 'active' : ''}`}
            onClick={() => setInputMode('paste')}
            disabled={isSubmitting}
          >
            Paste Text
          </button>
          <button
            className={`tab ${inputMode === 'upload' ? 'active' : ''}`}
            onClick={() => setInputMode('upload')}
            disabled={isSubmitting}
          >
            Upload File
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          {inputMode === 'url' && (
            <div className="input-section">
              <label>Application URL</label>
              <input
                type="url"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://forum.example.com/grant-application/..."
                disabled={isSubmitting}
              />
              <p className="hint">Paste a link to a forum post, document, or any webpage containing the grant application.</p>
            </div>
          )}

          {inputMode === 'paste' && (
            <div className="input-section">
              <label>Application Content</label>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Paste the full grant application text here..."
                rows={12}
                disabled={isSubmitting}
              />
            </div>
          )}

          {inputMode === 'upload' && (
            <div className="input-section">
              <label>Upload File</label>
              <div
                className={`drop-zone ${file ? 'has-file' : ''}`}
                onDrop={handleFileDrop}
                onDragOver={(e) => e.preventDefault()}
              >
                {file ? (
                  <div className="file-info">
                    <span className="file-name">{file.name}</span>
                    <button type="button" onClick={() => setFile(null)} className="remove-file">
                      Remove
                    </button>
                  </div>
                ) : (
                  <>
                    <p>Drag and drop a file here, or</p>
                    <label className="file-select-btn">
                      Browse Files
                      <input
                        type="file"
                        accept=".txt,.md,.pdf"
                        onChange={handleFileSelect}
                        disabled={isSubmitting}
                      />
                    </label>
                    <p className="hint">Supported: .txt, .md, .pdf</p>
                  </>
                )}
              </div>
            </div>
          )}

          {error && (
            <div className="error-message">{error}</div>
          )}

          {progress.length > 0 && (
            <div className="progress-section">
              <h3>Processing</h3>
              <div className="progress-steps">
                {progress.map((p, i) => (
                  <div key={i} className={`progress-step ${p.type.includes('complete') ? 'complete' : ''}`}>
                    <span className="step-icon">{p.type.includes('complete') ? '✓' : '...'}</span>
                    <span className="step-label">{getStageLabel(p.type)}</span>
                  </div>
                ))}
              </div>
              {applicationId && progress.some(p => p.type === 'complete') && (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => navigate(`/applications/${applicationId}`)}
                  style={{ marginTop: '16px' }}
                >
                  View Evaluation Results
                </button>
              )}
            </div>
          )}

          <button type="submit" className="btn btn-primary btn-lg" disabled={isSubmitting}>
            {isSubmitting ? 'Processing...' : 'Submit for Review'}
          </button>
        </form>
      </div>
    </div>
  );
}
