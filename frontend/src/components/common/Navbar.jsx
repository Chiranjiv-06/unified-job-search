import React from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import useAuth from '../../hooks/useAuth';
import { Briefcase, User as UserIcon, LogOut, LayoutDashboard } from 'lucide-react';

export default function Navbar() {
  const { user, isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header style={styles.header}>
      <div style={styles.container}>
        <Link to="/" style={styles.brand}>
          <div style={styles.brandIcon}>
            <Briefcase size={20} color="#ffffff" />
          </div>
          <div>
            <span style={styles.brandTitle}>Unified Job Search</span>
            <span style={styles.brandSub}>Career Assistant</span>
          </div>
        </Link>

        {isAuthenticated && (
          <nav style={styles.nav}>
            <Link
              to="/"
              style={{
                ...styles.navLink,
                ...(location.pathname === '/' ? styles.navLinkActive : {}),
              }}
            >
              <LayoutDashboard size={16} />
              <span>Dashboard</span>
            </Link>

            <Link
              to="/profile"
              style={{
                ...styles.navLink,
                ...(location.pathname === '/profile' ? styles.navLinkActive : {}),
              }}
            >
              <UserIcon size={16} />
              <span>Profile</span>
            </Link>

            <div style={styles.userSection}>
              <span style={styles.userName} title={user?.email}>
                {user?.full_name || 'Candidate'}
              </span>
              <button onClick={handleLogout} style={styles.logoutBtn} title="Sign Out">
                <LogOut size={16} />
                <span>Logout</span>
              </button>
            </div>
          </nav>
        )}
      </div>
    </header>
  );
}

const styles = {
  header: {
    backgroundColor: '#ffffff',
    borderBottom: '1px solid #e5e7eb',
    position: 'sticky',
    top: 0,
    zIndex: 40,
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  container: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: '12px 24px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  brand: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    textDecoration: 'none',
    color: '#111827',
  },
  brandIcon: {
    width: '36px',
    height: '36px',
    borderRadius: '8px',
    backgroundColor: '#2563eb',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  brandTitle: {
    fontSize: '16px',
    fontWeight: '700',
    color: '#111827',
    display: 'block',
    lineHeight: 1.2,
  },
  brandSub: {
    fontSize: '11px',
    color: '#6b7280',
    display: 'block',
  },
  nav: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
  },
  navLink: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 12px',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: '500',
    color: '#4b5563',
    textDecoration: 'none',
    transition: 'all 0.15s ease',
  },
  navLinkActive: {
    color: '#2563eb',
    backgroundColor: '#eff6ff',
    fontWeight: '600',
  },
  userSection: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginLeft: '12px',
    paddingLeft: '16px',
    borderLeft: '1px solid #e5e7eb',
  },
  userName: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#374151',
  },
  logoutBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 12px',
    borderRadius: '6px',
    border: '1px solid #e5e7eb',
    backgroundColor: '#ffffff',
    color: '#dc2626',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'background-color 0.15s ease',
  },
};
