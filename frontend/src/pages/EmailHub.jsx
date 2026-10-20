import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getEmailsApi,
  ingestEmailApi,
  linkEmailToApplicationApi,
  getApplicationsApi
} from '../services/api';
import {
  Mail,
  Video,
  Clock,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ExternalLink,
  Link2,
  Search,
  RotateCw,
  Plus,
  Building2,
  Calendar,
  X,
  Loader2,
  Send,
  HelpCircle,
  ArrowRight
} from 'lucide-react';

const TABS = [
  { key: 'ALL', label: 'All Emails' },
  { key: 'INTERVIEWS', label: 'Interviews' },
  { key: 'ASSESSMENTS', label: 'Assessments' },
  { key: 'CONFIRMATIONS', label: 'Confirmations' },
  { key: 'REJECTIONS', label: 'Rejections' },
  { key: 'SCAM', label: 'Scam Warnings' },
  { key: 'REVIEW', label: 'Needs Review' },
];

export default function EmailHub() {
  const navigate = useNavigate();
  const [emails, setEmails] = useState([]);
  const [applications, setApplications] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Filter & Search states
  const [activeTab, setActiveTab] = useState('ALL');
  const [searchTerm, setSearchTerm] = useState('');

  // Modals state
  const [showSimulateModal, setShowSimulateModal] = useState(false);
  const [linkingEmail, setLinkingEmail] = useState(null); // When manual link drawer is open
  const [selectedAppId, setSelectedAppId] = useState('');
  const [submittingAction, setSubmittingAction] = useState(false);

  // Ingestion simulation form state
  const [simSender, setSimSender] = useState('');
  const [simSubject, setSimSubject] = useState('');
  const [simBody, setSimBody] = useState('');

  const fetchEmailData = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [emailData, appsData] = await Promise.all([
        getEmailsApi({ limit: 100 }),
        getApplicationsApi({ limit: 100 })
      ]);
      setEmails(emailData.items || []);
      setApplications(appsData.items || []);
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to load email communications.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchEmailData();
    }, 50);
    return () => clearTimeout(timer);
  }, [fetchEmailData]);

  // Tab Filtering & Search
  const filteredEmails = useMemo(() => {
    return emails.filter((item) => {
      // Tab matching
      if (activeTab === 'INTERVIEWS' && !['INTERVIEW', 'INTERVIEW_INVITE'].includes(item.detected_category)) {
        return false;
      }
      if (activeTab === 'ASSESSMENTS' && !['ASSESSMENT', 'ASSESSMENT_INVITE'].includes(item.detected_category)) {
        return false;
      }
      if (activeTab === 'CONFIRMATIONS' && !['CONFIRMATION', 'APPLICATION_CONFIRMATION'].includes(item.detected_category)) {
        return false;
      }
      if (activeTab === 'REJECTIONS' && item.detected_category !== 'REJECTION') {
        return false;
      }
      if (activeTab === 'SCAM' && item.detected_category !== 'SCAM_ALERT') {
        return false;
      }
      if (activeTab === 'REVIEW' && !item.parsed_details?.requires_review) {
        return false;
      }

      // Search matching
      if (searchTerm.trim()) {
        const query = searchTerm.toLowerCase();
        const matchesSubject = item.subject?.toLowerCase().includes(query);
        const matchesSender = item.sender_email?.toLowerCase().includes(query);
        const matchesCompany = item.application_company_name?.toLowerCase().includes(query);
        const matchesJob = item.application_job_title?.toLowerCase().includes(query);
        return matchesSubject || matchesSender || matchesCompany || matchesJob;
      }

      return true;
    });
  }, [emails, activeTab, searchTerm]);

  // Statistics calculation
  const stats = useMemo(() => {
    let interviews = 0;
    let assessments = 0;
    let scams = 0;
    let requiresReview = 0;

    emails.forEach((e) => {
      if (['INTERVIEW', 'INTERVIEW_INVITE'].includes(e.detected_category)) interviews++;
      if (['ASSESSMENT', 'ASSESSMENT_INVITE'].includes(e.detected_category)) assessments++;
      if (e.detected_category === 'SCAM_ALERT') scams++;
      if (e.parsed_details?.requires_review) requiresReview++;
    });

    return { total: emails.length, interviews, assessments, scams, requiresReview };
  }, [emails]);

  // Manual link action
  const handleLinkApplication = async (e) => {
    e.preventDefault();
    if (!linkingEmail || !selectedAppId) return;

    setSubmittingAction(true);
    setErrorMsg(null);
    try {
      const updated = await linkEmailToApplicationApi(linkingEmail.id, parseInt(selectedAppId, 10));
      setEmails((prev) =>
        prev.map((item) => (item.id === updated.id ? updated : item))
      );
      setLinkingEmail(null);
      setSelectedAppId('');
      setSuccessMsg(`Email successfully linked to application and stage updated!`);
      setTimeout(() => setSuccessMsg(null), 3500);
      fetchEmailData();
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to link email to application.');
    } finally {
      setSubmittingAction(false);
    }
  };

  // Test simulation handler
  const handleSimulateSubmit = async (e) => {
    e.preventDefault();
    if (!simSubject.trim() || !simBody.trim()) {
      setErrorMsg('Subject and Body are required.');
      return;
    }

    setSubmittingAction(true);
    setErrorMsg(null);
    try {
      await ingestEmailApi({
        sender: simSender.trim() || 'recruiter@company.com',
        subject: simSubject.trim(),
        body: simBody.trim(),
      });
      setShowSimulateModal(false);
      setSimSender('');
      setSimSubject('');
      setSimBody('');
      setSuccessMsg('Test email ingested! Classified and synchronized to pipeline.');
      setTimeout(() => setSuccessMsg(null), 3500);
      fetchEmailData();
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to ingest test email.');
    } finally {
      setSubmittingAction(false);
    }
  };

  // Quick preset loader for demo
  const loadPreset = (type) => {
    if (type === 'interview') {
      setSimSender('talent@stripe.com');
      setSimSubject('Stripe Technical Round Interview Invitation');
      setSimBody('Hi Candidate,\n\nWe would love to schedule an interview with you. Please join our video call via Google Meet: https://meet.google.com/abc-stripe-xyz on Friday, Nov 10 at 2:00 PM.');
    } else if (type === 'assessment') {
      setSimSender('noreply@hackerrankmail.com');
      setSimSubject('Goldman Sachs Online Coding Assessment Invitation');
      setSimBody('Hello,\n\nPlease complete your HackerRank technical test within 48 hours. Deadline: 2026-11-15.\nLink: https://www.hackerrank.com/tests/gs-coder-88');
    } else if (type === 'scam') {
      setSimSender('recruiter_direct@free-job-portal.net');
      setSimSubject('Immediate Job Offer: Equipment Deposit Required');
      setSimBody('Congratulations! You have been selected. Please wire transfer $350 for home office setup and contact @hr_manager on telegram for telegram interview.');
    }
  };

  // Format date helper
  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      const d = new Date(dateStr);
      return d.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit'
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.pageHeader}>
        <div>
          <div style={styles.titleBadge}>
            <Mail size={16} color="#2563eb" />
            <span>Automated Inbox Intelligence</span>
          </div>
          <h1 style={styles.pageTitle}>Recruitment Email Hub</h1>
          <p style={styles.pageSubtitle}>
            Intelligent parsing of recruiter communications, automatic stage progression, and fraudulent message detection.
          </p>
        </div>
        <div style={styles.headerActions}>
          <button
            onClick={fetchEmailData}
            style={styles.refreshBtn}
            disabled={loading}
            title="Refresh communications"
          >
            <RotateCw size={15} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setShowSimulateModal(true)}
            style={styles.primaryAddBtn}
          >
            <Plus size={16} />
            <span>Simulate / Ingest Email</span>
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

      {/* Statistics Bar */}
      <div style={styles.statsGrid}>
        <div style={styles.statCard}>
          <div style={{ ...styles.statIconWrap, backgroundColor: '#eff6ff', color: '#2563eb' }}>
            <Mail size={20} />
          </div>
          <div>
            <span style={styles.statLabel}>Total Ingested</span>
            <div style={styles.statValue}>{stats.total}</div>
          </div>
        </div>

        <div style={styles.statCard}>
          <div style={{ ...styles.statIconWrap, backgroundColor: '#fffbeb', color: '#d97706' }}>
            <Video size={20} />
          </div>
          <div>
            <span style={styles.statLabel}>Interview Invites</span>
            <div style={styles.statValue}>{stats.interviews}</div>
          </div>
        </div>

        <div style={styles.statCard}>
          <div style={{ ...styles.statIconWrap, backgroundColor: '#f5f3ff', color: '#7c3aed' }}>
            <Clock size={20} />
          </div>
          <div>
            <span style={styles.statLabel}>Assessments</span>
            <div style={styles.statValue}>{stats.assessments}</div>
          </div>
        </div>

        <div style={styles.statCard}>
          <div style={{ ...styles.statIconWrap, backgroundColor: '#fef2f2', color: '#dc2626' }}>
            <ShieldAlert size={20} />
          </div>
          <div>
            <span style={styles.statLabel}>Scam Alerts</span>
            <div style={styles.statValue}>{stats.scams}</div>
          </div>
        </div>

        <div style={styles.statCard}>
          <div style={{ ...styles.statIconWrap, backgroundColor: '#f0fdf4', color: '#059669' }}>
            <HelpCircle size={20} />
          </div>
          <div>
            <span style={styles.statLabel}>Needs Review</span>
            <div style={styles.statValue}>{stats.requiresReview}</div>
          </div>
        </div>
      </div>

      {/* Filter Tabs & Search */}
      <div style={styles.filterToolbar}>
        <div style={styles.tabsWrap}>
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              style={{
                ...styles.tabBtn,
                ...(activeTab === tab.key ? styles.tabBtnActive : {}),
              }}
            >
              {tab.label}
              {tab.key === 'SCAM' && stats.scams > 0 && (
                <span style={styles.badgeAlert}>{stats.scams}</span>
              )}
              {tab.key === 'REVIEW' && stats.requiresReview > 0 && (
                <span style={styles.badgeReview}>{stats.requiresReview}</span>
              )}
            </button>
          ))}
        </div>

        <div style={styles.searchWrap}>
          <Search size={15} color="#9ca3af" />
          <input
            type="text"
            placeholder="Search by subject, sender, or company..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={styles.searchInput}
          />
          {searchTerm && (
            <button onClick={() => setSearchTerm('')} style={styles.clearBtn}>
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Communications List */}
      {loading ? (
        <div style={styles.loadingContainer}>
          <Loader2 size={36} className="spin" color="#2563eb" />
          <p style={styles.loadingText}>Loading recruitment emails...</p>
        </div>
      ) : filteredEmails.length === 0 ? (
        <div style={styles.emptyContainer}>
          <Mail size={48} color="#9ca3af" />
          <h3 style={styles.emptyTitle}>No Email Communications Found</h3>
          <p style={styles.emptySubtitle}>
            {searchTerm
              ? 'No emails match your search criteria. Try a different query.'
              : 'Ingest or simulate recruitment emails to automatically coordinate your job pipeline.'}
          </p>
          <button
            onClick={() => setShowSimulateModal(true)}
            style={styles.primaryAddBtn}
          >
            <Plus size={16} />
            <span>Simulate Inbound Email</span>
          </button>
        </div>
      ) : (
        <div style={styles.emailList}>
          {filteredEmails.map((email) => {
            const isInterview = ['INTERVIEW', 'INTERVIEW_INVITE'].includes(email.detected_category);
            const isAssessment = ['ASSESSMENT', 'ASSESSMENT_INVITE'].includes(email.detected_category);
            const isScam = email.detected_category === 'SCAM_ALERT';
            const isRejection = email.detected_category === 'REJECTION';
            const isConfirmation = ['CONFIRMATION', 'APPLICATION_CONFIRMATION'].includes(email.detected_category);

            return (
              <div
                key={email.id}
                style={{
                  ...styles.emailCard,
                  borderColor: isScam ? '#fca5a5' : '#e5e7eb',
                  backgroundColor: isScam ? '#fffafa' : '#ffffff',
                }}
              >
                {/* Top Row: Sender, Date, Category Badge */}
                <div style={styles.cardTopRow}>
                  <div style={styles.senderInfo}>
                    <span style={styles.senderEmail}>{email.sender_email}</span>
                    {email.parsed_details?.sender_domain && (
                      <span style={styles.domainBadge}>
                        @{email.parsed_details.sender_domain}
                      </span>
                    )}
                  </div>

                  <div style={styles.categoryPillsWrap}>
                    {/* Category Pill */}
                    {isInterview && (
                      <span style={{ ...styles.categoryPill, backgroundColor: '#fffbeb', color: '#b45309', borderColor: '#fde68a' }}>
                        <Video size={13} />
                        <span>Interview Invite</span>
                      </span>
                    )}
                    {isAssessment && (
                      <span style={{ ...styles.categoryPill, backgroundColor: '#f5f3ff', color: '#7c3aed', borderColor: '#ddd6fe' }}>
                        <Clock size={13} />
                        <span>Assessment Invite</span>
                      </span>
                    )}
                    {isConfirmation && (
                      <span style={{ ...styles.categoryPill, backgroundColor: '#eff6ff', color: '#2563eb', borderColor: '#bfdbfe' }}>
                        <CheckCircle2 size={13} />
                        <span>Confirmation</span>
                      </span>
                    )}
                    {isRejection && (
                      <span style={{ ...styles.categoryPill, backgroundColor: '#f3f4f6', color: '#4b5563', borderColor: '#e5e7eb' }}>
                        <XCircle size={13} />
                        <span>Rejection Notice</span>
                      </span>
                    )}
                    {isScam && (
                      <span style={{ ...styles.categoryPill, backgroundColor: '#fef2f2', color: '#dc2626', borderColor: '#fecaca' }}>
                        <ShieldAlert size={13} />
                        <span>Scam Warning</span>
                      </span>
                    )}

                    <span style={styles.dateLabel}>{formatDate(email.received_at)}</span>
                  </div>
                </div>

                {/* Subject Line */}
                <h3 style={styles.subjectText}>{email.subject}</h3>

                {/* Parsed Details Highlights */}
                {email.parsed_details && (
                  <div style={styles.detailsHighlightRow}>
                    {email.parsed_details.platform && (
                      <div style={styles.detailTag}>
                        <span style={styles.detailTagLabel}>Platform:</span>
                        <span style={styles.detailTagValue}>{email.parsed_details.platform}</span>
                      </div>
                    )}

                    {email.parsed_details.meeting_link && (
                      <a
                        href={email.parsed_details.meeting_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={styles.meetingLinkBtn}
                        title="Open meeting or video link"
                      >
                        <Video size={13} />
                        <span>Join Meeting</span>
                        <ExternalLink size={12} />
                      </a>
                    )}

                    {email.parsed_details.test_link && (
                      <a
                        href={email.parsed_details.test_link}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={styles.testLinkBtn}
                        title="Open assessment link"
                      >
                        <ExternalLink size={13} />
                        <span>Open Assessment</span>
                      </a>
                    )}

                    {email.parsed_details.assessment_deadline && (
                      <div style={styles.deadlineTag}>
                        <Clock size={13} color="#7c3aed" />
                        <span>Deadline: {email.parsed_details.assessment_deadline}</span>
                      </div>
                    )}

                    {email.parsed_details.scheduled_at && (
                      <div style={styles.scheduledTag}>
                        <Calendar size={13} color="#b45309" />
                        <span>Scheduled: {email.parsed_details.scheduled_at}</span>
                      </div>
                    )}
                  </div>
                )}

                {/* Fraud Red Flags Alert Box */}
                {isScam && (
                  <div style={styles.scamWarningBox}>
                    <div style={styles.scamHeader}>
                      <ShieldAlert size={16} color="#dc2626" />
                      <span style={styles.scamTitle}>High-Risk Fraud Flags Detected</span>
                    </div>
                    <p style={styles.scamDescription}>
                      {email.parsed_details?.warning_message ||
                        'This message triggered security alerts for upfront payment, wire transfer, or suspicious chat app redirects.'}
                    </p>
                    {email.parsed_details?.scam_indicators?.length > 0 && (
                      <div style={styles.indicatorsWrap}>
                        {email.parsed_details.scam_indicators.map((ind, i) => (
                          <span key={i} style={styles.scamPill}>
                            {ind}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}

                {/* Application Linkage Footer */}
                <div style={styles.cardFooter}>
                  {email.application_id ? (
                    <div style={styles.linkedAppRow}>
                      <div style={styles.linkedBadge}>
                        <Building2 size={14} color="#059669" />
                        <span style={styles.linkedAppText}>
                          Linked: <strong>{email.application_company_name}</strong> — {email.application_job_title}
                        </span>
                        {email.application_status && (
                          <span style={styles.statusPill}>{email.application_status}</span>
                        )}
                      </div>
                      <button
                        onClick={() => navigate('/tracker')}
                        style={styles.viewTrackerBtn}
                      >
                        <span>View in Tracker</span>
                        <ArrowRight size={13} />
                      </button>
                    </div>
                  ) : (
                    <div style={styles.unlinkedRow}>
                      <div style={styles.needsReviewNotice}>
                        <AlertTriangle size={14} color="#d97706" />
                        <span>Unmatched or ambiguous application</span>
                      </div>
                      <button
                        onClick={() => {
                          setLinkingEmail(email);
                          setSelectedAppId(applications[0]?.id || '');
                        }}
                        style={styles.manualLinkBtn}
                      >
                        <Link2 size={14} />
                        <span>Link to Application</span>
                      </button>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal: Manual Link Application */}
      {linkingEmail && (
        <div style={styles.modalOverlay} onClick={() => setLinkingEmail(null)}>
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div>
                <h2 style={styles.modalTitle}>Connect Email to Application</h2>
                <p style={styles.modalSub}>
                  Select the job application this communication belongs to.
                </p>
              </div>
              <button onClick={() => setLinkingEmail(null)} style={styles.modalCloseBtn}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleLinkApplication} style={styles.modalBody}>
              <div style={styles.selectedEmailPreview}>
                <span style={styles.previewLabel}>Email Subject:</span>
                <p style={styles.previewSubject}>{linkingEmail.subject}</p>
                <span style={styles.previewSender}>From: {linkingEmail.sender_email}</span>
              </div>

              <div style={{ marginTop: '16px' }}>
                <label style={styles.formLabel}>Select Candidate Application *</label>
                {applications.length === 0 ? (
                  <p style={{ fontSize: '13px', color: '#6b7280' }}>
                    No active applications found in your tracker. Track a job first!
                  </p>
                ) : (
                  <select
                    value={selectedAppId}
                    onChange={(e) => setSelectedAppId(e.target.value)}
                    style={styles.formSelect}
                    required
                  >
                    <option value="">-- Choose Application --</option>
                    {applications.map((app) => (
                      <option key={app.id} value={app.id}>
                        {app.company_name} — {app.job_title} ({app.status})
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div style={styles.modalBtnRow}>
                <button
                  type="button"
                  onClick={() => setLinkingEmail(null)}
                  style={styles.cancelBtn}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingAction || !selectedAppId}
                  style={styles.primaryAddBtn}
                >
                  {submittingAction ? (
                    <Loader2 size={16} className="spin" />
                  ) : (
                    <Link2 size={16} />
                  )}
                  <span>Connect & Advance Stage</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Ingest / Simulate Email */}
      {showSimulateModal && (
        <div style={styles.modalOverlay} onClick={() => setShowSimulateModal(false)}>
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div>
                <h2 style={styles.modalTitle}>Simulate Inbound Recruitment Email</h2>
                <p style={styles.modalSub}>
                  Paste or load realistic communication to test real-time classification and timeline sync
                </p>
              </div>
              <button onClick={() => setShowSimulateModal(false)} style={styles.modalCloseBtn}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSimulateSubmit} style={styles.modalBody}>
              {/* Preset Buttons */}
              <div style={styles.presetRow}>
                <span style={styles.presetLabel}>Quick Presets:</span>
                <button
                  type="button"
                  onClick={() => loadPreset('interview')}
                  style={styles.presetBtn}
                >
                  Interview Invite
                </button>
                <button
                  type="button"
                  onClick={() => loadPreset('assessment')}
                  style={styles.presetBtn}
                >
                  Coding Assessment
                </button>
                <button
                  type="button"
                  onClick={() => loadPreset('scam')}
                  style={{ ...styles.presetBtn, color: '#dc2626' }}
                >
                  Scam Fee Demand
                </button>
              </div>

              <div style={styles.formField}>
                <label style={styles.formLabel}>Sender Email Address</label>
                <input
                  type="email"
                  placeholder="e.g. recruiter@stripe.com"
                  value={simSender}
                  onChange={(e) => setSimSender(e.target.value)}
                  style={styles.formInput}
                  required
                />
              </div>

              <div style={styles.formField}>
                <label style={styles.formLabel}>Email Subject Line *</label>
                <input
                  type="text"
                  placeholder="e.g. Interview Invitation: Backend Engineer"
                  value={simSubject}
                  onChange={(e) => setSimSubject(e.target.value)}
                  style={styles.formInput}
                  required
                />
              </div>

              <div style={styles.formField}>
                <label style={styles.formLabel}>Email Body Content *</label>
                <textarea
                  rows={6}
                  placeholder="Paste email text, meeting links, or assessment deadlines..."
                  value={simBody}
                  onChange={(e) => setSimBody(e.target.value)}
                  style={styles.formTextarea}
                  required
                />
              </div>

              <div style={styles.modalBtnRow}>
                <button
                  type="button"
                  onClick={() => setShowSimulateModal(false)}
                  style={styles.cancelBtn}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingAction}
                  style={styles.primaryAddBtn}
                >
                  {submittingAction ? (
                    <Loader2 size={16} className="spin" />
                  ) : (
                    <Send size={16} />
                  )}
                  <span>Ingest & Process Email</span>
                </button>
              </div>
            </form>
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
    backgroundColor: '#eff6ff',
    color: '#2563eb',
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
  primaryAddBtn: {
    display: 'flex',
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
    boxShadow: '0 1px 2px rgba(37, 99, 235, 0.2)',
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
  filterToolbar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    border: '1px solid #e5e7eb',
    borderRadius: '10px',
    padding: '10px 14px',
    marginBottom: '20px',
    flexWrap: 'wrap',
    gap: '12px',
  },
  tabsWrap: {
    display: 'flex',
    gap: '6px',
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
    transition: 'all 0.15s ease',
  },
  tabBtnActive: {
    backgroundColor: '#eff6ff',
    color: '#2563eb',
    fontWeight: '600',
  },
  badgeAlert: {
    fontSize: '11px',
    fontWeight: '700',
    backgroundColor: '#dc2626',
    color: '#ffffff',
    padding: '1px 6px',
    borderRadius: '10px',
  },
  badgeReview: {
    fontSize: '11px',
    fontWeight: '700',
    backgroundColor: '#f59e0b',
    color: '#ffffff',
    padding: '1px 6px',
    borderRadius: '10px',
  },
  searchWrap: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    backgroundColor: '#f9fafb',
    border: '1px solid #e5e7eb',
    borderRadius: '6px',
    padding: '6px 10px',
    minWidth: '260px',
  },
  searchInput: {
    border: 'none',
    background: 'transparent',
    outline: 'none',
    fontSize: '13px',
    color: '#111827',
    width: '100%',
  },
  clearBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#9ca3af',
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
  emailList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  emailCard: {
    borderRadius: '10px',
    border: '1px solid #e5e7eb',
    padding: '16px 20px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  cardTopRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '8px',
  },
  senderInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  senderEmail: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#1f2937',
  },
  domainBadge: {
    fontSize: '11px',
    color: '#6b7280',
    backgroundColor: '#f3f4f6',
    padding: '2px 6px',
    borderRadius: '4px',
  },
  categoryPillsWrap: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  categoryPill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '5px',
    fontSize: '11px',
    fontWeight: '700',
    padding: '3px 8px',
    borderRadius: '12px',
    border: '1px solid',
  },
  dateLabel: {
    fontSize: '12px',
    color: '#9ca3af',
  },
  subjectText: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#111827',
    margin: '0',
    lineHeight: 1.3,
  },
  detailsHighlightRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    flexWrap: 'wrap',
  },
  detailTag: {
    display: 'inline-flex',
    gap: '4px',
    fontSize: '12px',
    backgroundColor: '#f9fafb',
    padding: '3px 8px',
    borderRadius: '6px',
    border: '1px solid #e5e7eb',
  },
  detailTagLabel: {
    color: '#6b7280',
    fontWeight: '500',
  },
  detailTagValue: {
    color: '#111827',
    fontWeight: '600',
  },
  meetingLinkBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '5px',
    padding: '4px 10px',
    backgroundColor: '#eff6ff',
    color: '#2563eb',
    border: '1px solid #bfdbfe',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: '600',
    textDecoration: 'none',
  },
  testLinkBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '5px',
    padding: '4px 10px',
    backgroundColor: '#f5f3ff',
    color: '#7c3aed',
    border: '1px solid #ddd6fe',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: '600',
    textDecoration: 'none',
  },
  deadlineTag: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '5px',
    fontSize: '12px',
    fontWeight: '600',
    color: '#7c3aed',
    backgroundColor: '#f5f3ff',
    padding: '3px 8px',
    borderRadius: '6px',
  },
  scheduledTag: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '5px',
    fontSize: '12px',
    fontWeight: '600',
    color: '#b45309',
    backgroundColor: '#fffbeb',
    padding: '3px 8px',
    borderRadius: '6px',
  },
  scamWarningBox: {
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '8px',
    padding: '12px 14px',
  },
  scamHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginBottom: '4px',
  },
  scamTitle: {
    fontSize: '13px',
    fontWeight: '700',
    color: '#b91c1c',
  },
  scamDescription: {
    fontSize: '12px',
    color: '#991b1b',
    margin: '0 0 8px 0',
    lineHeight: 1.4,
  },
  indicatorsWrap: {
    display: 'flex',
    gap: '6px',
    flexWrap: 'wrap',
  },
  scamPill: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#b91c1c',
    backgroundColor: '#fee2e2',
    padding: '2px 7px',
    borderRadius: '4px',
  },
  cardFooter: {
    paddingTop: '8px',
    borderTop: '1px solid #f3f4f6',
  },
  linkedAppRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '8px',
  },
  linkedBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '13px',
    color: '#065f46',
  },
  linkedAppText: {
    fontSize: '13px',
  },
  statusPill: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#047857',
    backgroundColor: '#d1fae5',
    padding: '2px 7px',
    borderRadius: '10px',
  },
  viewTrackerBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '12px',
    fontWeight: '600',
    color: '#2563eb',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
  },
  unlinkedRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '8px',
  },
  needsReviewNotice: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '12px',
    fontWeight: '500',
    color: '#b45309',
  },
  manualLinkBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '5px',
    padding: '5px 12px',
    backgroundColor: '#eff6ff',
    color: '#2563eb',
    border: '1px solid #bfdbfe',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: '600',
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
    maxWidth: '560px',
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
    padding: '20px 24px',
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
    margin: '4px 0 0 0',
  },
  modalCloseBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#9ca3af',
  },
  modalBody: {
    padding: '24px',
    overflowY: 'auto',
  },
  selectedEmailPreview: {
    backgroundColor: '#f9fafb',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    padding: '12px',
  },
  previewLabel: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#6b7280',
    textTransform: 'uppercase',
  },
  previewSubject: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#111827',
    margin: '4px 0',
  },
  previewSender: {
    fontSize: '12px',
    color: '#4b5563',
  },
  formLabel: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#4b5563',
    marginBottom: '6px',
    display: 'block',
  },
  formSelect: {
    width: '100%',
    padding: '8px 10px',
    fontSize: '13px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    color: '#111827',
    backgroundColor: '#ffffff',
    outline: 'none',
  },
  formField: {
    marginBottom: '14px',
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
    padding: '8px 10px',
    fontSize: '13px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    color: '#111827',
    outline: 'none',
    fontFamily: 'inherit',
    boxSizing: 'border-box',
    resize: 'vertical',
  },
  presetRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '16px',
    flexWrap: 'wrap',
  },
  presetLabel: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#6b7280',
  },
  presetBtn: {
    fontSize: '11px',
    fontWeight: '600',
    backgroundColor: '#f3f4f6',
    border: '1px solid #e5e7eb',
    borderRadius: '4px',
    padding: '4px 8px',
    color: '#374151',
    cursor: 'pointer',
  },
  modalBtnRow: {
    marginTop: '20px',
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px',
  },
  cancelBtn: {
    padding: '9px 14px',
    backgroundColor: '#ffffff',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '500',
    color: '#374151',
    cursor: 'pointer',
  },
};
