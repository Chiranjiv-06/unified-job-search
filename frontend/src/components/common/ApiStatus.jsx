import React, { useState, useEffect } from 'react';
import { checkHealth, checkDbHealth } from '../../services/api';
import { Activity, Database, Server, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react';

export default function ApiStatus() {
  const [appStatus, setAppStatus] = useState({ loading: true, healthy: false, data: null, error: null });
  const [dbStatus, setDbStatus] = useState({ loading: true, connected: false, data: null, error: null });

  const fetchStatuses = async () => {
    setAppStatus((prev) => ({ ...prev, loading: true, error: null }));
    setDbStatus((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const appData = await checkHealth();
      setAppStatus({ loading: false, healthy: true, data: appData, error: null });
    } catch (err) {
      setAppStatus({
        loading: false,
        healthy: false,
        data: null,
        error: err.customMessage || 'Backend unreachable',
      });
    }

    try {
      const dbData = await checkDbHealth();
      setDbStatus({ loading: false, connected: true, data: dbData, error: null });
    } catch (err) {
      setDbStatus({
        loading: false,
        connected: false,
        data: null,
        error: err.customMessage || 'Database service unavailable',
      });
    }
  };

  useEffect(() => {
    let ignore = false;

    checkHealth()
      .then((data) => {
        if (!ignore) setAppStatus({ loading: false, healthy: true, data, error: null });
      })
      .catch((err) => {
        if (!ignore) setAppStatus({ loading: false, healthy: false, data: null, error: err.customMessage || 'Backend unreachable' });
      });

    checkDbHealth()
      .then((data) => {
        if (!ignore) setDbStatus({ loading: false, connected: true, data, error: null });
      })
      .catch((err) => {
        if (!ignore) setDbStatus({ loading: false, connected: false, data: null, error: err.customMessage || 'Database service unavailable' });
      });

    return () => {
      ignore = true;
    };
  }, []);

  return (
    <div style={styles.card}>
      <div style={styles.header}>
        <div style={styles.titleGroup}>
          <Activity size={20} color="#2563eb" />
          <h3 style={styles.title}>System Connectivity Status</h3>
        </div>
        <button
          onClick={fetchStatuses}
          style={styles.refreshBtn}
          title="Refresh connectivity status"
          disabled={appStatus.loading || dbStatus.loading}
        >
          <RefreshCw size={14} className={appStatus.loading ? 'spin' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      <div style={styles.grid}>
        {/* Backend API Service */}
        <div style={styles.statusBox}>
          <div style={styles.boxHeader}>
            <Server size={18} color="#4b5563" />
            <span style={styles.boxTitle}>Backend API</span>
          </div>
          {appStatus.loading ? (
            <div style={styles.badgeLoading}>Checking...</div>
          ) : appStatus.healthy ? (
            <div style={styles.badgeSuccess}>
              <CheckCircle2 size={14} />
              <span>Online (FastAPI)</span>
            </div>
          ) : (
            <div style={styles.badgeError}>
              <AlertCircle size={14} />
              <span>Offline</span>
            </div>
          )}
          {appStatus.error && <p style={styles.errorText}>{appStatus.error}</p>}
        </div>

        {/* Database Service */}
        <div style={styles.statusBox}>
          <div style={styles.boxHeader}>
            <Database size={18} color="#4b5563" />
            <span style={styles.boxTitle}>PostgreSQL DB</span>
          </div>
          {dbStatus.loading ? (
            <div style={styles.badgeLoading}>Checking...</div>
          ) : dbStatus.connected ? (
            <div style={styles.badgeSuccess}>
              <CheckCircle2 size={14} />
              <span>Connected (Port 6314)</span>
            </div>
          ) : (
            <div style={styles.badgeError}>
              <AlertCircle size={14} />
              <span>Unavailable</span>
            </div>
          )}
          {dbStatus.error && <p style={styles.errorText}>{dbStatus.error}</p>}
        </div>
      </div>
    </div>
  );
}

const styles = {
  card: {
    maxWidth: '560px',
    margin: '24px auto',
    padding: '20px',
    borderRadius: '12px',
    backgroundColor: '#ffffff',
    border: '1px solid #e5e7eb',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05)',
    fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
  },
  titleGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  title: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#111827',
    margin: 0,
  },
  refreshBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 12px',
    fontSize: '12px',
    fontWeight: '500',
    borderRadius: '6px',
    border: '1px solid #d1d5db',
    backgroundColor: '#f9fafb',
    color: '#374151',
    cursor: 'pointer',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
  },
  statusBox: {
    padding: '12px',
    borderRadius: '8px',
    backgroundColor: '#f9fafb',
    border: '1px solid #f3f4f6',
  },
  boxHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginBottom: '8px',
  },
  boxTitle: {
    fontSize: '13px',
    fontWeight: '500',
    color: '#374151',
  },
  badgeSuccess: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 8px',
    borderRadius: '9999px',
    backgroundColor: '#ecfdf5',
    color: '#065f46',
    fontSize: '12px',
    fontWeight: '600',
  },
  badgeError: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 8px',
    borderRadius: '9999px',
    backgroundColor: '#fef2f2',
    color: '#991b1b',
    fontSize: '12px',
    fontWeight: '600',
  },
  badgeLoading: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '4px 8px',
    borderRadius: '9999px',
    backgroundColor: '#f3f4f6',
    color: '#4b5563',
    fontSize: '12px',
    fontWeight: '500',
  },
  errorText: {
    margin: '6px 0 0 0',
    fontSize: '11px',
    color: '#b91c1c',
  },
};
