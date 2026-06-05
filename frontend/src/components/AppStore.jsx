import React, { useState } from 'react';

export default function AppStore({ availableApps, installedApps, onSelectApp }) {
  const [searchTerm, setSearchTerm] = useState('');
  
  // Local filtering by search term only
  const filteredApps = availableApps.filter(app => {
    return app.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
           app.description.toLowerCase().includes(searchTerm.toLowerCase());
  });

  const checkIfInstalled = (appId) => {
    return installedApps.some(app => app.id === appId);
  };

  return (
    <section aria-label="Available Applications Catalog">
      {/* Filters Bar */}
      <div style={{
        display: 'flex',
        justifyContent: 'flex-end',
        alignItems: 'center',
        marginBottom: '2rem'
      }}>
        
        {/* Search Input */}
        <div style={{ position: 'relative', width: '100%', maxWidth: '300px' }}>
          <input
            type="search"
            placeholder="Search applications..."
            className="form-input"
            style={{ width: '100%', paddingLeft: '2.5rem', borderRadius: '6px' }}
            value={searchTerm}
            onChange={e => setSearchTerm(e.target.value)}
          />
          <span style={{ position: 'absolute', left: '1rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }}>
            🔍
          </span>
        </div>

      </div>

      {/* Grid of Apps */}
      {filteredApps.length > 0 ? (
        <div className="catalog-grid">
          {filteredApps.map(app => {
            const installed = checkIfInstalled(app.id);
            return (
              <div key={app.id} className="glass-card app-card">
                <div>
                  <div className="app-info-row">
                    <span className="app-icon-wrapper" aria-hidden="true" style={{ fontSize: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                      {app.icon || '📦'}
                    </span>
                    <div className="app-meta">
                      <h3 className="app-title">{app.name}</h3>
                      <span className="app-category">{app.category}</span>
                    </div>
                  </div>
                  <p className="app-desc">{app.description}</p>
                </div>
                
                {/* Actions button */}
                <div>
                  {installed ? (
                    <button className="btn btn-secondary" style={{ width: '100%' }} disabled>
                      ✓ Already Installed
                    </button>
                  ) : (
                    <button 
                      className="btn btn-primary" 
                      style={{ width: '100%' }}
                      onClick={() => onSelectApp(app)}
                    >
                      Configure & Install
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
          <h3 className="empty-view-title">No applications match your criteria</h3>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>Try clearing your search query or filters.</p>
        </div>
      )}
    </section>
  );
}
