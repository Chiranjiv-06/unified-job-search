import React from 'react';
import { Link } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import ApiStatus from '../components/common/ApiStatus';
import {
  User,
  ArrowRight,
  FileText,
  Search,
  Sparkles,
  Kanban,
  Mail,
  Bell
} from 'lucide-react';

export default function Dashboard() {
  const { user } = useAuth();

  return (
    <div style={styles.container}>
      {/* Welcome Banner */}
      <div style={styles.welcomeBanner}>
        <div>
          <div style={styles.badge}>
            <Sparkles size={14} />
            <span>Unified Platform Active</span>
          </div>
          <h1 style={styles.welcomeTitle}>
            Welcome back, {user?.full_name || 'Candidate'}!
          </h1>
          <p style={styles.welcomeSub}>
            Your centralized personal job-search assistant and application management system.
          </p>
        </div>
        <Link to="/profile" style={styles.profileBtn}>
          <User size={16} />
          <span>Edit Profile</span>
          <ArrowRight size={16} />
        </Link>
      </div>

      {/* Grid of Workflows & Modules */}
      <div style={styles.modulesGrid}>
        <div style={styles.moduleCard}>
          <div style={styles.moduleHeader}>
            <div style={{ ...styles.moduleIcon, backgroundColor: '#dbeafe', color: '#1d4ed8' }}>
              <User size={20} />
            </div>
            <span style={styles.statusBadgeCompleted}>Active</span>
          </div>
          <h3 style={styles.moduleTitle}>Candidate Profile</h3>
          <p style={styles.moduleDesc}>
            Manage your education, preferred roles, target locations, work modes, and skills.
          </p>
          <Link to="/profile" style={styles.cardLink}>
            Manage profile →
          </Link>
        </div>

        <div style={styles.moduleCard}>
          <div style={styles.moduleHeader}>
            <div style={{ ...styles.moduleIcon, backgroundColor: '#fef3c7', color: '#b45309' }}>
              <FileText size={20} />
            </div>
            <span style={styles.statusBadgeCompleted}>Active</span>
          </div>
          <h3 style={styles.moduleTitle}>Resume Management</h3>
          <p style={styles.moduleDesc}>
            PDF resume upload, text extraction with PyPDF, and candidate-reviewed skill extraction.
          </p>
          <Link to="/profile" style={styles.cardLink}>
            Upload & extract skills →
          </Link>
        </div>

        <div style={styles.moduleCard}>
          <div style={styles.moduleHeader}>
            <div style={{ ...styles.moduleIcon, backgroundColor: '#f3e8ff', color: '#7e22ce' }}>
              <Search size={20} />
            </div>
            <span style={styles.statusBadgeCompleted}>Active</span>
          </div>
          <h3 style={styles.moduleTitle}>Job Discovery & Records</h3>
          <p style={styles.moduleDesc}>
            Multi-source job discovery, stack and location filters, URL import, and explainable fit matching.
          </p>
          <Link to="/jobs" style={styles.cardLink}>
            Explore jobs →
          </Link>
        </div>

        <div style={styles.moduleCard}>
          <div style={styles.moduleHeader}>
            <div style={{ ...styles.moduleIcon, backgroundColor: '#ecfdf5', color: '#047857' }}>
              <Kanban size={20} />
            </div>
            <span style={styles.statusBadgeCompleted}>Active</span>
          </div>
          <h3 style={styles.moduleTitle}>Application Pipeline</h3>
          <p style={styles.moduleDesc}>
            Kanban workflow tracking applications across Draft, Applied, Interview, Offer, and Rejected.
          </p>
          <Link to="/tracker" style={styles.cardLink}>
            Open tracker →
          </Link>
        </div>

        <div style={styles.moduleCard}>
          <div style={styles.moduleHeader}>
            <div style={{ ...styles.moduleIcon, backgroundColor: '#e0e7ff', color: '#4338ca' }}>
              <Mail size={20} />
            </div>
            <span style={styles.statusBadgeCompleted}>Active</span>
          </div>
          <h3 style={styles.moduleTitle}>Email Intelligence</h3>
          <p style={styles.moduleDesc}>
            Recruiter email classification, automated interview/test event tracking, and scam detection.
          </p>
          <Link to="/emails" style={styles.cardLink}>
            View email hub →
          </Link>
        </div>

        <div style={styles.moduleCard}>
          <div style={styles.moduleHeader}>
            <div style={{ ...styles.moduleIcon, backgroundColor: '#fee2e2', color: '#b91c1c' }}>
              <Bell size={20} />
            </div>
            <span style={styles.statusBadgeCompleted}>Active</span>
          </div>
          <h3 style={styles.moduleTitle}>Reminders & Follow-Ups</h3>
          <p style={styles.moduleDesc}>
            Application aging alerts, response deadlines, and intelligent follow-up email draft generator.
          </p>
          <Link to="/reminders" style={styles.cardLink}>
            View reminders →
          </Link>
        </div>
      </div>


      {/* Backend & DB Health Monitor */}
      <div style={styles.statusSection}>
        <ApiStatus />
      </div>
    </div>
  );
}

const styles = {
  container: {
    maxWidth: '1200px',
    margin: '32px auto',
    padding: '0 24px',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  welcomeBanner: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '32px',
    borderRadius: '16px',
    background: 'linear-gradient(135deg, #1e40af 0%, #3b82f6 100%)',
    color: '#ffffff',
    boxShadow: '0 10px 15px -3px rgba(37, 99, 235, 0.2)',
    marginBottom: '32px',
    flexWrap: 'wrap',
    gap: '20px',
  },
  badge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '4px 10px',
    borderRadius: '20px',
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    fontSize: '12px',
    fontWeight: '600',
    marginBottom: '12px',
  },
  welcomeTitle: {
    fontSize: '28px',
    fontWeight: '800',
    margin: '0 0 8px 0',
    lineHeight: 1.2,
  },
  welcomeSub: {
    fontSize: '15px',
    color: '#e0e7ff',
    margin: 0,
    maxWidth: '600px',
  },
  profileBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px 20px',
    borderRadius: '10px',
    backgroundColor: '#ffffff',
    color: '#1e40af',
    fontSize: '14px',
    fontWeight: '600',
    textDecoration: 'none',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
  },
  modulesGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
    gap: '20px',
    marginBottom: '24px',
  },
  moduleCard: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    border: '1px solid #e5e7eb',
    padding: '24px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
  },
  moduleHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
  },
  moduleIcon: {
    width: '42px',
    height: '42px',
    borderRadius: '10px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  statusBadgeCompleted: {
    padding: '4px 8px',
    borderRadius: '9999px',
    backgroundColor: '#ecfdf5',
    color: '#065f46',
    fontSize: '11px',
    fontWeight: '600',
  },
  statusBadgeUpcoming: {
    padding: '4px 8px',
    borderRadius: '9999px',
    backgroundColor: '#fef3c7',
    color: '#92400e',
    fontSize: '11px',
    fontWeight: '600',
  },
  moduleTitle: {
    fontSize: '17px',
    fontWeight: '700',
    color: '#111827',
    margin: '0 0 8px 0',
  },
  moduleDesc: {
    fontSize: '13px',
    color: '#6b7280',
    lineHeight: 1.5,
    margin: '0 0 16px 0',
    flex: 1,
  },
  cardLink: {
    color: '#2563eb',
    fontSize: '13px',
    fontWeight: '600',
    textDecoration: 'none',
  },
  mutedText: {
    color: '#9ca3af',
    fontSize: '12px',
    fontStyle: 'italic',
  },
  statusSection: {
    marginTop: '12px',
  },
};
