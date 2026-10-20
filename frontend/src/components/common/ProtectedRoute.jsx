import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import useAuth from '../../hooks/useAuth';
import { Loader2 } from 'lucide-react';

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <div style={styles.loadingContainer}>
        <Loader2 size={32} className="spin" color="#2563eb" />
        <p style={styles.loadingText}>Restoring session...</p>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
}

const styles = {
  loadingContainer: {
    minHeight: '60vh',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    color: '#4b5563',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  loadingText: {
    fontSize: '14px',
    margin: 0,
  },
};
