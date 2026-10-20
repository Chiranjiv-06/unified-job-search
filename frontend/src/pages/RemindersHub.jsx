import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getRemindersAlertsApi,
  draftFollowUpApi,
  logFollowUpActionApi,
  getApplicationsApi
} from '../services/api';
import {
  Bell,
  Clock,
  Calendar,
  Video,
  AlertTriangle,
  CheckCircle2,
  Copy,
  ExternalLink,
  Send,
  Mail,
  RotateCw,
  Building2,
  Sparkles,
  X,
  Loader2,
  Check,
  FileText,
  Layers,
  ArrowRight
} from 'lucide-react';

const TABS = [
  { key: 'ALL', label: 'All Alerts' },
  { key: 'URGENT', label: 'Urgent Action' },
  { key: 'FOLLOW_UP', label: 'Follow-Ups Needed' },
  { key: 'INTERVIEWS', label: 'Interviews' },
  { key: 'ASSESSMENTS', label: 'Assessments' },
];

export default function RemindersHub() {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState([]);
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Filter state
  const [activeTab, setActiveTab] = useState('ALL');

  // Follow-Up Drafter Modal State
  const [activeDrafterApp, setActiveDrafterApp] = useState(null);
  const [selectedTone, setSelectedTone] = useState('professional');
  const [customNotes, setCustomNotes] = useState('');
  const [draftSubject, setDraftSubject] = useState('');
  const [draftBody, setDraftBody] = useState('');
  const [recipientEmail, setRecipientEmail] = useState('');
  const [mailtoLink, setMailtoLink] = useState('');
  const [draftingLoading, setDraftingLoading] = useState(false);
  const [copiedSuccess, setCopiedSuccess] = useState(false);
  const [loggingAction, setLoggingAction] = useState(false);

  const fetchAlertsData = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [alertsData, appsData] = await Promise.all([
        getRemindersAlertsApi(),
        getApplicationsApi({ limit: 100 })
      ]);
      setAlerts(alertsData.alerts || []);
      setApplications(appsData.items || []);
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to load reminders and alerts.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchAlertsData();
    }, 50);
    return () => clearTimeout(timer);
  }, [fetchAlertsData]);

  // Statistics calculation
  const stats = useMemo(() => {
    let urgent = 0;
    let followUp = 0;
    let interview = 0;
    let assessment = 0;

    alerts.forEach((a) => {
      if (a.priority === 'URGENT') urgent++;
      if (a.alert_type === 'FOLLOW_UP_NEEDED' || a.alert_type === 'STALE_LEAD') followUp++;
      if (a.alert_type === 'INTERVIEW_UPCOMING') interview++;
      if (a.alert_type === 'ASSESSMENT_DUE') assessment++;
    });

    return { total: alerts.length, urgent, followUp, interview, assessment };
  }, [alerts]);

  // Filtered alerts
  const filteredAlerts = useMemo(() => {
    return alerts.filter((a) => {
      if (activeTab === 'URGENT') return a.priority === 'URGENT';
      if (activeTab === 'FOLLOW_UP') return a.alert_type === 'FOLLOW_UP_NEEDED' || a.alert_type === 'STALE_LEAD';
      if (activeTab === 'INTERVIEWS') return a.alert_type === 'INTERVIEW_UPCOMING';
      if (activeTab === 'ASSESSMENTS') return a.alert_type === 'ASSESSMENT_DUE';
      return true;
    });
  }, [alerts, activeTab]);

  // Generate / Refresh draft
  const handleOpenDrafter = async (applicationId, initialTone = 'professional') => {
    const matchedApp = applications.find((app) => app.id === applicationId);
    if (!matchedApp) {
      // Find from alert
      const matchedAlert = alerts.find((a) => a.application_id === applicationId);
      if (matchedAlert) {
        setActiveDrafterApp({
          id: matchedAlert.application_id,
          company_name: matchedAlert.company_name,
          job_title: matchedAlert.job_title,
          status: matchedAlert.stage
        });
      }
    } else {
      setActiveDrafterApp(matchedApp);
    }

    setSelectedTone(initialTone);
    setDraftingLoading(true);
    setCopiedSuccess(false);
    setErrorMsg(null);

    try {
      const data = await draftFollowUpApi(applicationId, {
        tone: initialTone,
        custom_notes: customNotes
      });
      setDraftSubject(data.subject);
      setDraftBody(data.body);
      setRecipientEmail(data.recipient_email || '');
      setMailtoLink(data.mailto_link);
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to generate follow-up draft.');
    } finally {
      setDraftingLoading(false);
    }
  };

  // Re-generate draft with new tone
  const handleToneChange = async (tone) => {
    setSelectedTone(tone);
    if (!activeDrafterApp) return;

    setDraftingLoading(true);
    try {
      const data = await draftFollowUpApi(activeDrafterApp.id, {
        tone,
        custom_notes: customNotes
      });
      setDraftSubject(data.subject);
      setDraftBody(data.body);
      setMailtoLink(data.mailto_link);
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to update draft tone.');
    } finally {
      setDraftingLoading(false);
    }
  };

  // Copy to clipboard
  const handleCopyClipboard = async () => {
    const fullText = `Subject: ${draftSubject}\n\n${draftBody}`;
    try {
      await navigator.clipboard.writeText(fullText);
      setCopiedSuccess(true);
      setTimeout(() => setCopiedSuccess(false), 3000);
      setSuccessMsg('Email draft copied to clipboard!');
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch {
      setErrorMsg('Failed to copy to clipboard.');
    }
  };

  // Log follow-up in pipeline
  const handleLogFollowUp = async () => {
    if (!activeDrafterApp) return;
    setLoggingAction(true);
    setErrorMsg(null);
    try {
      await logFollowUpActionApi(activeDrafterApp.id, {
        notes: `Follow-up email sent (${selectedTone} tone): "${draftSubject}"`
      });
      setSuccessMsg(`Follow-up logged in ${activeDrafterApp.company_name || 'application'} pipeline!`);
      setTimeout(() => setSuccessMsg(null), 3500);
      setActiveDrafterApp(null);
      fetchAlertsData();
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to log follow-up action.');
    } finally {
      setLoggingAction(false);
    }
  };

  return (
    <div style={styles.container}>
      {/* Page Header */}
      <div style={styles.pageHeader}>
        <div>
          <div style={styles.titleBadge}>
            <Bell size={16} color="#d97706" />
            <span>Intelligent Alerts & Aging Rules</span>
          </div>
          <h1 style={styles.pageTitle}>Reminders & Action Center</h1>
          <p style={styles.pageSubtitle}>
            Never miss a test deadline or critical interview round. Monitor application aging and draft polite, context-aware follow-up emails.
          </p>
        </div>
        <div style={styles.headerActions}>
          <button
            onClick={fetchAlertsData}
            style={styles.refreshBtn}
            disabled={loading}
            title="Refresh active reminders"
          >
            <RotateCw size={15} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {errorMsg && (
        <div style={styles.errorBanner}>
          <AlertTriangle size={18} color="#dc2626" />
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} style={styles.bannerCloseBtn}>
            <X size={15} />
          </button>
        </div>
      )}
      {successMsg && (
        <div style={styles.successBanner}>
          <CheckCircle2 size={18} color="#059669" />
          <span>{successMsg}</span>
          <button onClick={() => setSuccessMsg(null)} style={styles.bannerCloseBtn}>
            <X size={15} />
          </button>
        </div>
      )}

      {/* Stats KPI Grid */}
      <div style={styles.statsGrid}>
        <div style={styles.statCard}>
          <div style={{ ...styles.statIconWrap, backgroundColor: '#eff6ff', color: '#2563eb' }}>
            <Layers size={20} />
          </div>
          <div>
            <span style={styles.statLabel}>Pending Action Items</span>
            <div style={styles.statValue}>{stats.total}</div>
          </div>
        </div>

        <div style={styles.statCard}>
          <div style={{ ...styles.statIconWrap, backgroundColor: '#fef2f2', color: '#dc2626' }}>
            <AlertTriangle size={20} />
          </div>
          <div>
            <span style={styles.statLabel}>Urgent Action (&lt;24h)</span>
            <div style={styles.statValue}>{stats.urgent}</div>
          </div>
        </div>

        <div style={styles.statCard}>
          <div style={{ ...styles.statIconWrap, backgroundColor: '#fffbeb', color: '#d97706' }}>
            <Clock size={20} />
          </div>
          <div>
            <span style={styles.statLabel}>Follow-Ups Suggested</span>
            <div style={styles.statValue}>{stats.followUp}</div>
          </div>
        </div>

        <div style={styles.statCard}>
          <div style={{ ...styles.statIconWrap, backgroundColor: '#f0fdf4', color: '#059669' }}>
            <Video size={20} />
          </div>
          <div>
            <span style={styles.statLabel}>Upcoming Interviews</span>
            <div style={styles.statValue}>{stats.interview}</div>
          </div>
        </div>

        <div style={styles.statCard}>
          <div style={{ ...styles.statIconWrap, backgroundColor: '#f5f3ff', color: '#7c3aed' }}>
            <Calendar size={20} />
          </div>
          <div>
            <span style={styles.statLabel}>Active Tests / Coding</span>
            <div style={styles.statValue}>{stats.assessment}</div>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div style={styles.tabsContainer}>
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            style={{
              ...styles.tabBtn,
              ...(activeTab === t.key ? styles.tabBtnActive : {}),
            }}
          >
            {t.label}
            {t.key === 'URGENT' && stats.urgent > 0 && (
              <span style={styles.badgeUrgent}>{stats.urgent}</span>
            )}
            {t.key === 'FOLLOW_UP' && stats.followUp > 0 && (
              <span style={styles.badgeFollowUp}>{stats.followUp}</span>
            )}
          </button>
        ))}
      </div>

      {/* Alerts Feed */}
      {loading ? (
        <div style={styles.loadingContainer}>
          <Loader2 size={36} className="spin" color="#2563eb" />
          <p style={styles.loadingText}>Evaluating pipeline aging and active deadlines...</p>
        </div>
      ) : filteredAlerts.length === 0 ? (
        <div style={styles.emptyContainer}>
          <CheckCircle2 size={48} color="#059669" />
          <h3 style={styles.emptyTitle}>All Caught Up!</h3>
          <p style={styles.emptySubtitle}>
            No action items or stalled leads require attention right now. Your job search pipeline is completely up to date.
          </p>
          <button
            onClick={() => navigate('/tracker')}
            style={styles.primaryBtn}
          >
            <span>View Tracker Pipeline</span>
            <ArrowRight size={15} />
          </button>
        </div>
      ) : (
        <div style={styles.alertsList}>
          {filteredAlerts.map((alert) => {
            const isUrgent = alert.priority === 'URGENT';
            const isInterview = alert.alert_type === 'INTERVIEW_UPCOMING';
            const isAssessment = alert.alert_type === 'ASSESSMENT_DUE';
            const isFollowUp = alert.alert_type === 'FOLLOW_UP_NEEDED' || alert.alert_type === 'STALE_LEAD';

            return (
              <div
                key={alert.id}
                style={{
                  ...styles.alertCard,
                  borderColor: isUrgent ? '#fca5a5' : '#e5e7eb',
                  borderLeftColor: isUrgent ? '#dc2626' : isInterview ? '#d97706' : isAssessment ? '#7c3aed' : '#2563eb',
                  borderLeftWidth: '4px',
                }}
              >
                <div style={styles.alertCardHeader}>
                  <div style={styles.companyRoleWrap}>
                    <div style={styles.companyRow}>
                      <Building2 size={14} color="#4b5563" />
                      <span style={styles.companyName}>{alert.company_name}</span>
                      <span style={styles.stageTag}>{alert.stage}</span>
                    </div>
                    <h3 style={styles.alertJobTitle}>{alert.job_title}</h3>
                  </div>

                  <div style={styles.priorityBadgeWrap}>
                    {isUrgent && (
                      <span style={{ ...styles.priorityPill, backgroundColor: '#fef2f2', color: '#dc2626', borderColor: '#fecaca' }}>
                        <AlertTriangle size={12} />
                        <span>URGENT</span>
                      </span>
                    )}
                    {alert.priority === 'HIGH' && (
                      <span style={{ ...styles.priorityPill, backgroundColor: '#fffbeb', color: '#d97706', borderColor: '#fde68a' }}>
                        <span>HIGH PRIORITY</span>
                      </span>
                    )}
                    {alert.priority === 'MEDIUM' && (
                      <span style={{ ...styles.priorityPill, backgroundColor: '#eff6ff', color: '#2563eb', borderColor: '#bfdbfe' }}>
                        <span>ACTION SUGGESTED</span>
                      </span>
                    )}
                  </div>
                </div>

                <div style={styles.alertContent}>
                  <h4 style={styles.alertHeading}>{alert.title}</h4>
                  <p style={styles.alertMessage}>{alert.message}</p>
                </div>

                {/* Metadata Row: Due date, meeting link, activity */}
                <div style={styles.alertMetaRow}>
                  {alert.due_date && (
                    <div style={styles.metaTag}>
                      <Clock size={12} color="#7c3aed" />
                      <span>{alert.due_date}</span>
                    </div>
                  )}

                  {alert.meeting_link && (
                    <a
                      href={alert.meeting_link}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={styles.meetingLinkBtn}
                    >
                      <Video size={12} />
                      <span>Launch Video Call</span>
                      <ExternalLink size={11} />
                    </a>
                  )}

                  <div style={styles.metaTag}>
                    <Calendar size={12} color="#6b7280" />
                    <span>
                      {alert.days_since_activity === 0
                        ? 'Updated today'
                        : `${alert.days_since_activity} days since activity`}
                    </span>
                  </div>
                </div>

                {/* Action Buttons */}
                <div style={styles.alertFooter}>
                  {isFollowUp && (
                    <button
                      onClick={() => handleOpenDrafter(alert.application_id)}
                      style={styles.draftBtn}
                    >
                      <Sparkles size={14} />
                      <span>Draft Professional Follow-Up</span>
                    </button>
                  )}

                  {isAssessment && (
                    <button
                      onClick={() => navigate('/tracker')}
                      style={styles.assessmentBtn}
                    >
                      <FileText size={14} />
                      <span>Review Assessment in Tracker</span>
                    </button>
                  )}

                  {isInterview && (
                    <button
                      onClick={() => navigate('/tracker')}
                      style={styles.interviewBtn}
                    >
                      <Video size={14} />
                      <span>Prepare Interview Questions</span>
                    </button>
                  )}

                  <button
                    onClick={() => navigate('/tracker')}
                    style={styles.viewPipelineBtn}
                  >
                    <span>View in Pipeline</span>
                    <ArrowRight size={13} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal: Professional Follow-Up Email Drafter */}
      {activeDrafterApp && (
        <div style={styles.modalOverlay} onClick={() => setActiveDrafterApp(null)}>
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <h2 style={styles.modalTitle}>Professional Follow-Up Assistant</h2>
                  <span style={styles.stageTag}>{activeDrafterApp.status || activeDrafterApp.stage}</span>
                </div>
                <p style={styles.modalSub}>
                  {activeDrafterApp.job_title} at {activeDrafterApp.company_name}
                </p>
              </div>
              <button onClick={() => setActiveDrafterApp(null)} style={styles.modalCloseBtn}>
                <X size={20} />
              </button>
            </div>

            <div style={styles.modalBody}>
              {/* Tone Selector */}
              <div style={styles.toneSelectorRow}>
                <span style={styles.toneLabel}>Email Tone:</span>
                <button
                  type="button"
                  onClick={() => handleToneChange('polite')}
                  style={{
                    ...styles.toneBtn,
                    ...(selectedTone === 'polite' ? styles.toneBtnActive : {}),
                  }}
                >
                  Polite & Enthusiastic
                </button>
                <button
                  type="button"
                  onClick={() => handleToneChange('professional')}
                  style={{
                    ...styles.toneBtn,
                    ...(selectedTone === 'professional' ? styles.toneBtnActive : {}),
                  }}
                >
                  Professional & Balanced
                </button>
                <button
                  type="button"
                  onClick={() => handleToneChange('firm')}
                  style={{
                    ...styles.toneBtn,
                    ...(selectedTone === 'firm' ? styles.toneBtnActive : {}),
                  }}
                >
                  Firm & Time-Sensitive
                </button>
              </div>

              {/* Recipient */}
              {recipientEmail && (
                <div style={styles.recipientRow}>
                  <Mail size={13} color="#6b7280" />
                  <span style={styles.recipientLabel}>Recipient:</span>
                  <span style={styles.recipientVal}>{recipientEmail}</span>
                </div>
              )}

              {/* Custom Notes */}
              <div style={styles.formGroup}>
                <label style={styles.formLabel}>Custom Notes / Discussion Points (Optional)</label>
                <input
                  type="text"
                  placeholder="e.g. Followed up on discussion about distributed systems..."
                  value={customNotes}
                  onChange={(e) => setCustomNotes(e.target.value)}
                  style={styles.formInput}
                />
              </div>

              {/* Subject Line */}
              <div style={styles.formGroup}>
                <label style={styles.formLabel}>Subject Line</label>
                <input
                  type="text"
                  value={draftSubject}
                  onChange={(e) => setDraftSubject(e.target.value)}
                  style={styles.formInput}
                />
              </div>

              {/* Email Body */}
              <div style={styles.formGroup}>
                <label style={styles.formLabel}>Message Body</label>
                {draftingLoading ? (
                  <div style={styles.draftLoadingBox}>
                    <Loader2 size={24} className="spin" color="#2563eb" />
                    <span>Personalizing follow-up template...</span>
                  </div>
                ) : (
                  <textarea
                    rows={10}
                    value={draftBody}
                    onChange={(e) => setDraftBody(e.target.value)}
                    style={styles.formTextarea}
                  />
                )}
              </div>

              {/* Strict Candidate Consent Notice */}
              <div style={styles.consentNotice}>
                <CheckCircle2 size={15} color="#059669" />
                <span>
                  <strong>Strict Candidate-Consent Enforced:</strong> Antigravity will never auto-send emails. You retain full control to edit, copy, or send through your default email client.
                </span>
              </div>

              {/* Modal Actions */}
              <div style={styles.modalActionRow}>
                <button
                  type="button"
                  onClick={handleCopyClipboard}
                  style={styles.copyBtn}
                >
                  {copiedSuccess ? <Check size={16} color="#059669" /> : <Copy size={16} />}
                  <span>{copiedSuccess ? 'Copied to Clipboard!' : 'Copy Email Draft'}</span>
                </button>

                {mailtoLink && (
                  <a
                    href={mailtoLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={styles.mailtoBtn}
                  >
                    <Send size={15} />
                    <span>Open in Email App</span>
                  </a>
                )}

                <button
                  type="button"
                  onClick={handleLogFollowUp}
                  disabled={loggingAction}
                  style={styles.logActionBtn}
                >
                  {loggingAction ? (
                    <Loader2 size={15} className="spin" />
                  ) : (
                    <CheckCircle2 size={15} />
                  )}
                  <span>Mark as Followed-Up</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  container: {
    maxWidth: '1240px',
    margin: '0 auto',
    padding: '24px 20px 48px',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  pageHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '20px',
    flexWrap: 'wrap',
    gap: '16px',
  },
  titleBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    backgroundColor: '#fffbeb',
    color: '#d97706',
    fontSize: '12px',
    fontWeight: '600',
    padding: '4px 10px',
    borderRadius: '16px',
    marginBottom: '8px',
  },
  pageTitle: {
    fontSize: '28px',
    fontWeight: '700',
    color: '#111827',
    margin: '0 0 6px 0',
  },
  pageSubtitle: {
    fontSize: '14px',
    color: '#6b7280',
    margin: 0,
    maxWidth: '680px',
  },
  headerActions: {
    display: 'flex',
    gap: '10px',
    alignItems: 'center',
  },
  refreshBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '9px 14px',
    backgroundColor: '#ffffff',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '500',
    color: '#374151',
    cursor: 'pointer',
  },
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '12px 16px',
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '8px',
    color: '#b91c1c',
    fontSize: '14px',
    marginBottom: '16px',
  },
  successBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '12px 16px',
    backgroundColor: '#ecfdf5',
    border: '1px solid #a7f3d0',
    borderRadius: '8px',
    color: '#047857',
    fontSize: '14px',
    marginBottom: '16px',
  },
  bannerCloseBtn: {
    marginLeft: 'auto',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: 'inherit',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '14px',
    marginBottom: '22px',
  },
  statCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '14px',
    padding: '16px',
    backgroundColor: '#ffffff',
    border: '1px solid #e5e7eb',
    borderRadius: '10px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.03)',
  },
  statIconWrap: {
    width: '42px',
    height: '42px',
    borderRadius: '10px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  statLabel: {
    fontSize: '12px',
    fontWeight: '500',
    color: '#6b7280',
    display: 'block',
  },
  statValue: {
    fontSize: '22px',
    fontWeight: '700',
    color: '#111827',
  },
  tabsContainer: {
    display: 'flex',
    gap: '8px',
    backgroundColor: '#ffffff',
    border: '1px solid #e5e7eb',
    borderRadius: '10px',
    padding: '8px 12px',
    marginBottom: '20px',
    flexWrap: 'wrap',
  },
  tabBtn: {
    padding: '6px 12px',
    fontSize: '13px',
    fontWeight: '500',
    backgroundColor: 'transparent',
    border: 'none',
    borderRadius: '6px',
    color: '#6b7280',
    cursor: 'pointer',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
  },
  tabBtnActive: {
    backgroundColor: '#eff6ff',
    color: '#2563eb',
    fontWeight: '600',
  },
  badgeUrgent: {
    fontSize: '11px',
    fontWeight: '700',
    backgroundColor: '#dc2626',
    color: '#ffffff',
    padding: '1px 6px',
    borderRadius: '10px',
  },
  badgeFollowUp: {
    fontSize: '11px',
    fontWeight: '700',
    backgroundColor: '#d97706',
    color: '#ffffff',
    padding: '1px 6px',
    borderRadius: '10px',
  },
  loadingContainer: {
    textAlign: 'center',
    padding: '60px 20px',
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    border: '1px solid #e5e7eb',
  },
  loadingText: {
    marginTop: '12px',
    fontSize: '14px',
    color: '#6b7280',
  },
  emptyContainer: {
    textAlign: 'center',
    padding: '60px 20px',
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    border: '1px solid #e5e7eb',
  },
  emptyTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#111827',
    marginTop: '12px',
  },
  emptySubtitle: {
    fontSize: '14px',
    color: '#6b7280',
    margin: '6px 0 18px 0',
  },
  primaryBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '9px 16px',
    backgroundColor: '#2563eb',
    border: 'none',
    borderRadius: '8px',
    fontSize: '14px',
    fontWeight: '600',
    color: '#ffffff',
    cursor: 'pointer',
  },
  alertsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  alertCard: {
    backgroundColor: '#ffffff',
    borderRadius: '10px',
    border: '1px solid #e5e7eb',
    padding: '16px 20px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  alertCardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    flexWrap: 'wrap',
    gap: '8px',
  },
  companyRoleWrap: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  companyRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  companyName: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#4b5563',
  },
  stageTag: {
    fontSize: '10px',
    fontWeight: '700',
    padding: '2px 6px',
    backgroundColor: '#eff6ff',
    color: '#2563eb',
    borderRadius: '4px',
  },
  alertJobTitle: {
    fontSize: '16px',
    fontWeight: '700',
    color: '#111827',
    margin: 0,
  },
  priorityBadgeWrap: {
    display: 'flex',
    gap: '6px',
  },
  priorityPill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '11px',
    fontWeight: '700',
    padding: '2px 7px',
    borderRadius: '10px',
    border: '1px solid',
  },
  alertContent: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  alertHeading: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#1f2937',
    margin: 0,
  },
  alertMessage: {
    fontSize: '13px',
    color: '#4b5563',
    margin: 0,
    lineHeight: 1.4,
  },
  alertMetaRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    flexWrap: 'wrap',
    paddingTop: '6px',
    borderTop: '1px solid #f3f4f6',
  },
  metaTag: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '12px',
    color: '#6b7280',
    backgroundColor: '#f9fafb',
    padding: '3px 8px',
    borderRadius: '6px',
    border: '1px solid #e5e7eb',
  },
  meetingLinkBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '5px',
    padding: '3px 8px',
    backgroundColor: '#eff6ff',
    color: '#2563eb',
    border: '1px solid #bfdbfe',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: '600',
    textDecoration: 'none',
  },
  alertFooter: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '8px',
    paddingTop: '8px',
    borderTop: '1px solid #f3f4f6',
  },
  draftBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '7px 14px',
    backgroundColor: '#eff6ff',
    color: '#2563eb',
    border: '1px solid #bfdbfe',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  assessmentBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '7px 14px',
    backgroundColor: '#f5f3ff',
    color: '#7c3aed',
    border: '1px solid #ddd6fe',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  interviewBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '7px 14px',
    backgroundColor: '#fffbeb',
    color: '#d97706',
    border: '1px solid #fde68a',
    borderRadius: '6px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  viewPipelineBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '12px',
    fontWeight: '600',
    color: '#4b5563',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.45)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 100,
    padding: '16px',
  },
  modalContent: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    width: '100%',
    maxWidth: '680px',
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
    overflow: 'hidden',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: '18px 24px',
    borderBottom: '1px solid #e5e7eb',
  },
  modalTitle: {
    fontSize: '18px',
    fontWeight: '700',
    color: '#111827',
    margin: 0,
  },
  modalSub: {
    fontSize: '13px',
    color: '#6b7280',
    margin: '3px 0 0 0',
  },
  modalCloseBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#9ca3af',
  },
  modalBody: {
    padding: '20px 24px',
    overflowY: 'auto',
  },
  toneSelectorRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '16px',
    flexWrap: 'wrap',
  },
  toneLabel: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#4b5563',
  },
  toneBtn: {
    fontSize: '12px',
    fontWeight: '500',
    backgroundColor: '#f3f4f6',
    border: '1px solid #e5e7eb',
    borderRadius: '6px',
    padding: '5px 10px',
    color: '#374151',
    cursor: 'pointer',
  },
  toneBtnActive: {
    backgroundColor: '#eff6ff',
    color: '#2563eb',
    borderColor: '#bfdbfe',
    fontWeight: '600',
  },
  recipientRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '12px',
    color: '#4b5563',
    backgroundColor: '#f9fafb',
    border: '1px solid #e5e7eb',
    borderRadius: '6px',
    padding: '6px 10px',
    marginBottom: '14px',
  },
  recipientLabel: {
    fontWeight: '600',
  },
  recipientVal: {
    color: '#2563eb',
    fontWeight: '500',
  },
  formGroup: {
    marginBottom: '14px',
  },
  formLabel: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#4b5563',
    marginBottom: '4px',
    display: 'block',
  },
  formInput: {
    width: '100%',
    padding: '8px 10px',
    fontSize: '13px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    color: '#111827',
    outline: 'none',
    boxSizing: 'border-box',
  },
  formTextarea: {
    width: '100%',
    padding: '10px',
    fontSize: '13px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    color: '#111827',
    outline: 'none',
    fontFamily: 'inherit',
    boxSizing: 'border-box',
    resize: 'vertical',
    lineHeight: 1.5,
  },
  draftLoadingBox: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    padding: '40px 20px',
    backgroundColor: '#f9fafb',
    borderRadius: '6px',
    border: '1px solid #e5e7eb',
    fontSize: '13px',
    color: '#6b7280',
  },
  consentNotice: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '8px',
    backgroundColor: '#f0fdf4',
    border: '1px solid #bbf7d0',
    borderRadius: '6px',
    padding: '10px 12px',
    fontSize: '12px',
    color: '#166534',
    lineHeight: 1.4,
    marginBottom: '16px',
  },
  modalActionRow: {
    display: 'flex',
    justifyContent: 'flex-end',
    alignItems: 'center',
    gap: '10px',
    flexWrap: 'wrap',
  },
  copyBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '9px 14px',
    backgroundColor: '#ffffff',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '600',
    color: '#374151',
    cursor: 'pointer',
  },
  mailtoBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '9px 14px',
    backgroundColor: '#eff6ff',
    border: '1px solid #bfdbfe',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '600',
    color: '#2563eb',
    textDecoration: 'none',
  },
  logActionBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '9px 16px',
    backgroundColor: '#2563eb',
    border: 'none',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '600',
    color: '#ffffff',
    cursor: 'pointer',
  },
};
