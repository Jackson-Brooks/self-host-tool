import React, { useState } from 'react';

export default function InstalledApps({ installedApps, onRefresh }) {
  const [loadingAppAction, setLoadingAppAction] = useState(null); // Track specific buttons like 'code-server-stop'
  const [uninstallConfirmId, setUninstallConfirmId] = useState(null); // Track which app is awaiting uninstall confirmation

  const handleAction = async (appId, action) => {
    const actionKey = `${appId}-${action}`;
    setLoadingAppAction(actionKey);
    try {
      const res = await fetch(`/api/apps/${appId}/${action}`, { method: 'POST' });
      if (!res.ok) {
        const errorMsg = await res.text();
        throw new Error(errorMsg || `Failed to execute ${action} routine`);
      }
      // Refresh backend state
      await onRefresh();
    } catch (err) {
      alert(`Operation failed: ${err.message}`);
    } finally {
      setLoadingAppAction(null);
      if (action === 'uninstall') {
        setUninstallConfirmId(null);
      }
    }
  };

  return (
    <section aria-label="Installed Services Management">
      {installedApps.length > 0 ? (
        <div className="services-list">
          {installedApps.map(app => {
            const isRunning = app.status === 'running';
            const isStopped = app.status === 'stopped';
            
            return (
              <div key={app.id} className="glass-card service-row">
                
                {/* Left Side: Metadata and State */}
                <div className="service-main">
                  <span className="app-icon-wrapper" aria-hidden="true" style={{ fontSize: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    {app.icon || '📦'}
                  </span>
                  <div className="service-meta">
                    <h3 className="service-name">
                      {app.name}
                      <span className={`badge ${app.status}`}>
                        {app.status}
                      </span>
                    </h3>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                      Category: {app.category}
                    </p>
                  </div>
                </div>

                {/* Right Side: Orchestration Control Suite */}
                <div className="service-actions">
                  
                  {/* Start / Stop Toggle */}
                  {isRunning ? (
                    <button 
                      className="btn btn-secondary" 
                      disabled={loadingAppAction !== null}
                      onClick={() => handleAction(app.id, 'stop')}
                    >
                      {loadingAppAction === `${app.id}-stop` ? 'Stopping...' : 'Stop'}
                    </button>
                  ) : (
                    <button 
                      className="btn btn-success" 
                      disabled={loadingAppAction !== null}
                      onClick={() => handleAction(app.id, 'start')}
                    >
                      {loadingAppAction === `${app.id}-start` ? 'Starting...' : 'Start'}
                    </button>
                  )}

                  {/* Launch App secure gateway link */}
                  {isRunning && (
                    <a 
                      href={app.open_path} 
                      className="btn btn-primary"
                      target="_blank" 
                      rel="noopener noreferrer"
                      style={{ textDecoration: 'none' }}
                    >
                      Open App ↗
                    </a>
                  )}

                  {/* Uninstall Suite (Safety confirmed state) */}
                  {uninstallConfirmId === app.id ? (
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                      <button 
                        className="btn btn-danger"
                        disabled={loadingAppAction !== null}
                        onClick={() => handleAction(app.id, 'uninstall')}
                      >
                        {loadingAppAction === `${app.id}-uninstall` ? 'Deleting...' : 'Confirm'}
                      </button>
                      <button 
                        className="btn btn-secondary"
                        disabled={loadingAppAction !== null}
                        onClick={() => setUninstallConfirmId(null)}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button 
                      className="btn btn-danger"
                      style={{ opacity: 0.8 }}
                      disabled={loadingAppAction !== null}
                      onClick={() => setUninstallConfirmId(app.id)}
                    >
                      Uninstall
                    </button>
                  )}

                </div>

              </div>
            );
          })}
        </div>
      ) : (
        <div className="empty-view glass-card">
          <div className="empty-view-icon" aria-hidden="true">🌌</div>
          <h3 className="empty-view-title">No applications installed yet</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: '380px', margin: '0 auto' }}>
            Browse our catalog in the App Store tab above to launch your first self-hosted container stack!
          </p>
        </div>
      )}
    </section>
  );
}
