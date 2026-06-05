import React, { useState, useEffect, useRef } from 'react';

export default function AppConfigModal({ app, onClose, onInstalled }) {
  const [formData, setFormData] = useState({});
  const [phase, setPhase] = useState('config'); // 'config' | 'installing' | 'finished'
  const [logs, setLogs] = useState('');
  const [error, setError] = useState(null);
  const [showPasswords, setShowPasswords] = useState({});
  
  const logContainerRef = useRef(null);
  const pollTimerRef = useRef(null);

  // Auto-populate default form inputs on load
  useEffect(() => {
    if (app && app.fields) {
      const defaults = {};
      app.fields.forEach(f => {
        if (f.default !== undefined) {
          defaults[f.key] = f.default;
        }
      });
      setFormData(defaults);
    }
  }, [app]);

  // Autoscroll the terminal logger to the bottom as lines arrive
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  // Clean up timers on unmount
  useEffect(() => {
    return () => {
      if (pollTimerRef.current) clearInterval(pollTimerRef.current);
    };
  }, []);

  const handleInputChange = (key, value) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const togglePasswordVisibility = (key) => {
    setShowPasswords(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleInstall = async (e) => {
    e.preventDefault();
    setPhase('installing');
    setError(null);
    setLogs('Contacting Self Host Tool Docker orchestrator...\n');

    try {
      const res = await fetch(`/api/apps/${app.id}/install`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(errorText || 'Failed to initialize deployment process');
      }

      // Begin polling log file
      pollTimerRef.current = setInterval(async () => {
        try {
          const logRes = await fetch(`/api/apps/${app.id}/logs`);
          if (logRes.ok) {
            const data = await logRes.json();
            setLogs(data.logs || '');
            
            // Check terminal triggers for success/failure
            if (data.logs.includes('Installation completed successfully!')) {
              clearInterval(pollTimerRef.current);
              setPhase('finished');
              if (onInstalled) onInstalled();
            } else if (data.logs.includes('failed with exit code') || data.logs.includes('Fatal error')) {
              clearInterval(pollTimerRef.current);
              setError('Deployment failed. Review container logs in terminal.');
            }
          }
        } catch (err) {
          console.error('Failed to pull installation output:', err);
        }
      }, 1000);

    } catch (err) {
      setError(err.message);
      setPhase('config');
    }
  };

  return (
    <div className="modal-overlay" onClick={phase === 'installing' ? undefined : onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        
        {/* Modal Header */}
        <header className="modal-header">
          <h2 className="modal-title">

            <span className="app-icon-wrapper" aria-hidden="true" style={{ fontSize: '1.5rem', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginRight: '0.75rem' }}>
              {app.icon || '📦'}
            </span>
            {phase === 'config' ? `Configure ${app.name}` : phase === 'installing' ? `Installing ${app.name}...` : `${app.name} Installed!`}
          </h2>
          {phase !== 'installing' && (
            <button className="close-btn" onClick={onClose} aria-label="Close dialog">×</button>
          )}
        </header>

        {/* Modal Content Bodies */}
        <div className="modal-body">
          {error && (
            <div style={{
              background: 'rgba(244, 63, 94, 0.1)',
              border: '1px solid var(--status-red)',
              borderRadius: '10px',
              padding: '0.75rem 1rem',
              color: 'var(--status-red)',
              fontSize: '0.85rem',
              marginBottom: '1.25rem'
            }}>
              ⚠️ {error}
            </div>
          )}

          {phase === 'config' && (
            <form id="install-form" onSubmit={handleInstall}>
              {app.fields && app.fields.map(field => {
                const isPasswordType = field.type === 'password';
                const currentType = isPasswordType 
                  ? (showPasswords[field.key] ? 'text' : 'password') 
                  : field.type;

                return (
                  <div key={field.key} className="form-group">
                    <label htmlFor={field.key} className="form-label">
                      {field.label} {field.required && <span style={{ color: 'var(--status-red)' }}>*</span>}
                    </label>
                    <div className="input-with-button-wrapper" style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                      <input
                        id={field.key}
                        type={currentType}
                        className="form-input"
                        style={{ paddingRight: isPasswordType ? '2.5rem' : '1rem', width: '100%' }}
                        placeholder={field.placeholder || ''}
                        value={formData[field.key] ?? ''}
                        onChange={e => handleInputChange(field.key, e.target.value)}
                        required={field.required}
                      />
                      {isPasswordType && (
                        <button
                          type="button"
                          className="password-toggle-btn"
                          onClick={() => togglePasswordVisibility(field.key)}
                          style={{
                            position: 'absolute',
                            right: '0.75rem',
                            background: 'none',
                            border: 'none',
                            color: 'var(--text-secondary)',
                            cursor: 'pointer',
                            fontSize: '1.1rem',
                            padding: '0',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            zIndex: 10
                          }}
                          aria-label={showPasswords[field.key] ? "Hide password" : "Show password"}
                        >
                          {showPasswords[field.key] ? '👁️' : '🙈'}
                        </button>
                      )}
                    </div>
                    {field.help && <span className="form-help">{field.help}</span>}
                  </div>
                );
              })}
            </form>
          )}

          {phase === 'installing' && (
            <div>
              <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                Downloading images and spinning up application containers. This may take a few moments.
              </p>
              <div className="console-logs-container" ref={logContainerRef}>
                {logs || 'Downloading container configs...'}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                <span className="badge installing">ACTIVE</span>
                Compiling container stack
              </div>
            </div>
          )}

          {phase === 'finished' && (
            <div style={{ textAlign: 'center', padding: '1rem 0' }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>🎉</div>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', lineHeight: '1.6', marginBottom: '1.5rem' }}>
                Excellent! <strong>{app.name}</strong> is now deployed in an isolated Docker container and reverse-proxied over your Tailscale IP.
              </p>
              <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: '12px', padding: '1rem', border: '1px solid rgba(255,255,255,0.03)' }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'block', marginBottom: '0.5rem' }}>SECURE ACCESS ADDRESS</span>
                <span style={{ fontFamily: 'monospace', color: 'var(--glow-cyan)', fontSize: '1.05rem', fontWeight: 600 }}>
                  {window.location.origin}{app.open_path}
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer actions */}
        <footer className="modal-footer">
          {phase === 'config' && (
            <>
              <button className="btn btn-secondary" onClick={onClose} type="button">Cancel</button>
              <button className="btn btn-primary" type="submit" form="install-form">Deploy Stack</button>
            </>
          )}
          {phase === 'finished' && (
            <>
              <button className="btn btn-secondary" onClick={onClose}>Close Portal</button>
              <a 
                className="btn btn-primary" 
                href={app.open_path} 
                target="_blank" 
                rel="noopener noreferrer"
                style={{ textDecoration: 'none' }}
              >
                Launch Application
              </a>
            </>
          )}
        </footer>

      </div>
    </div>
  );
}
