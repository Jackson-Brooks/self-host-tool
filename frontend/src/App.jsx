import React, { useState, useEffect } from 'react';
import SystemStats from './components/SystemStats';
import AppStore from './components/AppStore';
import InstalledApps from './components/InstalledApps';
import AppConfigModal from './components/AppConfigModal';

export default function App() {
  const [activeTab, setActiveTab] = useState('services'); // 'services' | 'store'
  const [tailscale, setTailscale] = useState({ connected: false, ip: 'N/A', magic_dns: 'N/A', device_name: 'N/A' });
  const [stats, setStats] = useState(null);
  const [availableApps, setAvailableApps] = useState([]);
  const [installedApps, setInstalledApps] = useState([]);
  const [selectedApp, setSelectedApp] = useState(null);

  // Synchronous reload of all data models
  const reloadData = async () => {
    try {
      const [tsRes, statsRes, availRes, instRes] = await Promise.all([
        fetch('/api/tailscale/status'),
        fetch('/api/system/stats'),
        fetch('/api/apps/available'),
        fetch('/api/apps/installed')
      ]);

      if (tsRes.ok) setTailscale(await tsRes.json());
      if (statsRes.ok) setStats(await statsRes.json());
      if (availRes.ok) setAvailableApps(await availRes.json());
      if (instRes.ok) setInstalledApps(await instRes.json());
    } catch (err) {
      console.error('Failed to sync portal configurations:', err);
    }
  };

  // Initial load and telemetry scheduling
  useEffect(() => {
    reloadData();

    // Fast-polling worker to keep resource meters and container statuses synchronized
    const poller = setInterval(async () => {
      try {
        const [statsRes, instRes] = await Promise.all([
          fetch('/api/system/stats'),
          fetch('/api/apps/installed')
        ]);
        if (statsRes.ok) setStats(await statsRes.json());
        if (instRes.ok) setInstalledApps(await instRes.json());
      } catch (err) {
        console.error('Telemetry loop sync failure:', err);
      }
    }, 3000);

    return () => clearInterval(poller);
  }, []);

  const handleCopySecureAddress = () => {
    if (tailscale.magic_dns && tailscale.magic_dns !== 'N/A') {
      const secureUrl = `https://${tailscale.magic_dns}`;
      navigator.clipboard.writeText(secureUrl);
      alert(`Copied secure access address to clipboard: ${secureUrl}`);
    } else if (tailscale.ip && tailscale.ip !== 'N/A') {
      const ipUrl = `http://${tailscale.ip}`;
      navigator.clipboard.writeText(ipUrl);
      alert(`Copied local IP address to clipboard: ${ipUrl}`);
    }
  };

  return (
    <div className="app-container">
      {/* Background Animated Blurs */}
      <div className="bg-glow-orb-1" aria-hidden="true" />
      <div className="bg-glow-orb-2" aria-hidden="true" />

      {/* Header Panel */}
      <header className="app-header">
        <div className="header-logo">
          <span className="logo-icon" aria-hidden="true">🌐</span>
          <h1 className="logo-text">Self Host Tool</h1>
        </div>

        {/* Tailscale Indicator Badge */}
        <div 
          className="tailscale-status-badge" 
          onClick={handleCopySecureAddress}
          title="Click to copy secure address"
          role="button"
          tabIndex="0"
        >
          <span className={`status-dot ${tailscale.connected ? 'online' : 'offline'}`} aria-hidden="true" />
          <span className="status-text">
            {tailscale.connected ? (
              <>
                Secured over VPN: <span className="status-dns">{tailscale.magic_dns}</span>
              </>
            ) : (
              'Tailscale Connection Offline'
            )}
          </span>
        </div>
      </header>

      {/* Main Content Layout */}
      <main className="dashboard-grid">
        
        {/* Left Side: Dynamic Host resource telemetry */}
        <SystemStats stats={stats} />

        {/* Right Side: Primary View Container */}
        <section aria-label="Portal Workspace" style={{ display: 'flex', flexDirection: 'column' }}>
          
          {/* Tab Navigation */}
          <nav className="tabs-container" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button 
                className={`tab-btn ${activeTab === 'services' ? 'active' : ''}`}
                onClick={() => setActiveTab('services')}
              >
                My Services
              </button>
              <button 
                className={`tab-btn ${activeTab === 'store' ? 'active' : ''}`}
                onClick={() => setActiveTab('store')}
              >
                App Store
              </button>
            </div>
            
            <a 
              href="/docs.html"
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-secondary"
              style={{ textDecoration: 'none', fontSize: '0.85rem', padding: '0.45rem 1rem', borderRadius: '8px', border: '1px solid var(--border-glass)', display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' }}
            >
              📖 Developer Guide
            </a>
          </nav>

          {/* Tab Views */}
          <div style={{ flexGrow: 1 }}>
            {activeTab === 'services' ? (
              <InstalledApps 
                installedApps={installedApps} 
                onRefresh={reloadData} 
              />
            ) : (
              <AppStore 
                availableApps={availableApps} 
                installedApps={installedApps} 
                onSelectApp={setSelectedApp} 
              />
            )}
          </div>

        </section>

      </main>

      {/* Dynamic Installation Dialog overlay */}
      {selectedApp && (
        <AppConfigModal 
          app={selectedApp} 
          onClose={() => setSelectedApp(null)} 
          onInstalled={reloadData}
        />
      )}

    </div>
  );
}
