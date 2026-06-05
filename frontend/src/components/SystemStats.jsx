import React from 'react';

export default function SystemStats({ stats }) {
  const formatGB = (bytes) => {
    if (!bytes || isNaN(bytes)) return '0 GB';
    return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
  };

  const formatUptime = (seconds) => {
    if (!seconds || isNaN(seconds)) return '0s';
    const d = Math.floor(seconds / (3600 * 24));
    const h = Math.floor((seconds % (3600 * 24)) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    return `${d}d ${h}h ${m}m`;
  };

  const cpuPercent = stats?.cpu?.percent ?? 0;
  const memPercent = stats?.memory?.percent ?? 0;
  const diskPercent = stats?.disk?.percent ?? 0;

  return (
    <aside className="glass-card stats-card" aria-label="System Performance Overview">
      <h2 className="stats-card-title">Host Resource Telemetry</h2>

      {/* CPU */}
      <div className="stat-item">
        <div className="stat-header">
          <span className="stat-label">CPU Load</span>
          <span className="stat-value">{cpuPercent.toFixed(1)}%</span>
        </div>
        <div className="progress-bar-bg" role="progressbar" aria-valuenow={cpuPercent} aria-valuemin="0" aria-valuemax="100">
          <div 
            className="progress-bar-fill cpu" 
            style={{ width: `${Math.min(100, Math.max(0, cpuPercent))}%` }}
          />
        </div>
      </div>

      {/* Memory */}
      <div className="stat-item">
        <div className="stat-header">
          <span className="stat-label">Memory Usage</span>
          <span className="stat-value">
            {stats?.memory?.used ? `${formatGB(stats.memory.used)} / ${formatGB(stats.memory.total)}` : `${memPercent.toFixed(0)}%`}
          </span>
        </div>
        <div className="progress-bar-bg" role="progressbar" aria-valuenow={memPercent} aria-valuemin="0" aria-valuemax="100">
          <div 
            className="progress-bar-fill memory" 
            style={{ width: `${Math.min(100, Math.max(0, memPercent))}%` }}
          />
        </div>
      </div>

      {/* Disk Storage */}
      <div className="stat-item">
        <div className="stat-header">
          <span className="stat-label">Storage (Persistent)</span>
          <span className="stat-value">
            {stats?.disk?.used ? `${formatGB(stats.disk.used)} / ${formatGB(stats.disk.total)}` : `${diskPercent.toFixed(0)}%`}
          </span>
        </div>
        <div className="progress-bar-bg" role="progressbar" aria-valuenow={diskPercent} aria-valuemin="0" aria-valuemax="100">
          <div 
            className="progress-bar-fill disk" 
            style={{ width: `${Math.min(100, Math.max(0, diskPercent))}%` }}
          />
        </div>
      </div>

      {/* Uptime */}
      <div className="uptime-widget">
        <span className="stat-label" style={{ fontWeight: 600 }}>System Uptime</span>
        <span className="stat-value" style={{ fontFamily: 'monospace', fontSize: '0.95rem', color: 'var(--glow-cyan)' }}>
          {formatUptime(stats?.uptime)}
        </span>
      </div>
    </aside>
  );
}
