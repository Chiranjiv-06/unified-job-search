import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getApplicationsApi,
  getPipelineMetricsApi,
  getEmailsApi,
  createApplicationApi,
  updateApplicationStageApi,
  updateApplicationDetailsApi,
  deleteApplicationApi,
  draftFollowUpApi,
  logFollowUpActionApi
} from '../services/api';
import {
  Kanban,
  Building2,
  Calendar,
  Clock,
  PlusCircle,
  RotateCw,
  Search,
  ExternalLink,
  Edit3,
  Trash2,
  X,
  Loader2,
  AlertCircle,
  CheckCircle2,
  Mail,
  Phone,
  Video,
  Award,
  Layers,
  ArrowRight,
  FileText,
  Sparkles,
  Copy,
  Check
} from 'lucide-react';

const STAGES = [
  { key: 'APPLIED', label: 'Applied', color: '#2563eb', bg: '#eff6ff', border: '#bfdbfe' },
  { key: 'ASSESSMENT', label: 'Assessment', color: '#7c3aed', bg: '#f5f3ff', border: '#ddd6fe' },
  { key: 'INTERVIEW', label: 'Interview', color: '#d97706', bg: '#fffbeb', border: '#fde68a' },
  { key: 'OFFER', label: 'Offer Received', color: '#059669', bg: '#ecfdf5', border: '#a7f3d0' },
  { key: 'REJECTED', label: 'Rejected', color: '#dc2626', bg: '#fef2f2', border: '#fecaca' },
  { key: 'STALE', label: 'Stale / Inactive', color: '#4b5563', bg: '#f3f4f6', border: '#e5e7eb' },
];

export default function Tracker() {
  const navigate = useNavigate();
  const [applications, setApplications] = useState([]);
  const [emails, setEmails] = useState([]);
  const [metrics, setMetrics] = useState({
    total_applications: 0,
    active_interviews: 0,
    tests_due: 0,
    offers_received: 0,
    by_stage: {}
  });
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Filters
  const [searchTerm, setSearchTerm] = useState('');
  const [platformFilter, setPlatformFilter] = useState('All');

  // Modals
  const [activeModalApp, setActiveModalApp] = useState(null); // For Details / Edit modal
  const [showAddModal, setShowAddModal] = useState(false); // For Manual Add
  const [showStagePrompt, setShowStagePrompt] = useState(null); // { app, targetStage, note }

  // Details Modal Form State
  const [editNotes, setEditNotes] = useState('');
  const [editRecruiterName, setEditRecruiterName] = useState('');
  const [editRecruiterEmail, setEditRecruiterEmail] = useState('');
  const [editRecruiterPhone, setEditRecruiterPhone] = useState('');
  const [editInterviewPlatform, setEditInterviewPlatform] = useState('');
  const [editInterviewLink, setEditInterviewLink] = useState('');
  const [editInterviewDate, setEditInterviewDate] = useState('');
  const [editAssessmentDeadline, setEditAssessmentDeadline] = useState('');
  const [editResumeVersion, setEditResumeVersion] = useState('');

  // Add Manual Application Form State
  const [newTitle, setNewTitle] = useState('');
  const [newCompany, setNewCompany] = useState('');
  const [newPlatform, setNewPlatform] = useState('LinkedIn');
  const [newSourceUrl, setNewSourceUrl] = useState('');
  const [newInitialStage, setNewInitialStage] = useState('APPLIED');
  const [newNotes, setNewNotes] = useState('');
  const [newRecruiterEmail, setNewRecruiterEmail] = useState('');

  // Follow-Up Drafter Modal State
  const [followUpApp, setFollowUpApp] = useState(null);
  const [followUpTone, setFollowUpTone] = useState('professional');
  const [followUpSubject, setFollowUpSubject] = useState('');
  const [followUpBody, setFollowUpBody] = useState('');
  const [followUpRecipient, setFollowUpRecipient] = useState('');
  const [followUpMailto, setFollowUpMailto] = useState('');
  const [followUpLoading, setFollowUpLoading] = useState(false);
  const [followUpCopied, setFollowUpCopied] = useState(false);
  const [followUpLogging, setFollowUpLogging] = useState(false);

  const fetchTrackerData = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const [appsData, metricsData, emailsData] = await Promise.all([
        getApplicationsApi({ limit: 100 }),
        getPipelineMetricsApi(),
        getEmailsApi({ limit: 100 })
      ]);
      setApplications(appsData.items || []);
      setEmails(emailsData.items || []);
      setMetrics(metricsData || {
        total_applications: 0,
        active_interviews: 0,
        tests_due: 0,
        offers_received: 0,
        by_stage: {}
      });
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to load application tracker data.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = setTimeout(() => {
      fetchTrackerData();
    }, 50);
    return () => clearTimeout(timer);
  }, [fetchTrackerData]);

  // Open Details Modal and populate state
  const handleOpenDetails = (app) => {
    setActiveModalApp(app);
    setEditNotes(app.notes || '');
    setEditRecruiterName(app.recruiter_contact?.name || '');
    setEditRecruiterEmail(app.recruiter_contact?.email || '');
    setEditRecruiterPhone(app.recruiter_contact?.phone || '');
    setEditInterviewPlatform(app.interview_details?.platform || '');
    setEditInterviewLink(app.interview_details?.meeting_link || '');
    setEditInterviewDate(app.interview_details?.scheduled_at || '');
    setEditAssessmentDeadline(app.interview_details?.assessment_deadline || '');
    setEditResumeVersion(app.resume_version || '');
  };

  // Save Application Details
  const handleSaveDetails = async (e) => {
    e.preventDefault();
    if (!activeModalApp) return;
    setActionLoading(true);
    setErrorMsg(null);
    try {
      const payload = {
        notes: editNotes,
        resume_version: editResumeVersion,
        recruiter_contact: {
          name: editRecruiterName,
          email: editRecruiterEmail,
          phone: editRecruiterPhone
        },
        interview_details: {
          platform: editInterviewPlatform,
          meeting_link: editInterviewLink,
          scheduled_at: editInterviewDate,
          assessment_deadline: editAssessmentDeadline
        }
      };
      const updated = await updateApplicationDetailsApi(activeModalApp.id, payload);
      setApplications((prev) =>
        prev.map((item) => (item.id === updated.id ? updated : item))
      );
      setActiveModalApp(updated);
      setSuccessMsg(`Details updated for ${updated.job_title} at ${updated.company_name}.`);
      setTimeout(() => setSuccessMsg(null), 3500);
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to update application details.');
    } finally {
      setActionLoading(false);
    }
  };

  // Quick Stage Transition
  const handleInitiateStageChange = (app, targetStage) => {
    if (app.status === targetStage) return;
    setShowStagePrompt({
      app,
      targetStage,
      note: `Transitioned from ${app.status} to ${targetStage}`
    });
  };

  const handleConfirmStageChange = async () => {
    if (!showStagePrompt) return;
    const { app, targetStage, note } = showStagePrompt;
    setActionLoading(true);
    setErrorMsg(null);
    try {
      const updated = await updateApplicationStageApi(app.id, {
        stage: targetStage,
        notes: note.trim() || undefined
      });

      setApplications((prev) =>
        prev.map((item) => (item.id === updated.id ? updated : item))
      );
      if (activeModalApp && activeModalApp.id === updated.id) {
        setActiveModalApp(updated);
      }
      setShowStagePrompt(null);
      setSuccessMsg(`Advanced ${updated.company_name} application to ${targetStage}!`);
      setTimeout(() => setSuccessMsg(null), 3500);

      // Refresh metrics silently
      const updatedMetrics = await getPipelineMetricsApi();
      setMetrics(updatedMetrics);
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to update stage.');
    } finally {
      setActionLoading(false);
    }
  };

  // Delete Application
  const handleDeleteApplication = async (appId, companyName) => {
    if (!window.confirm(`Are you sure you want to remove the application for ${companyName}?`)) {
      return;
    }
    setActionLoading(true);
    setErrorMsg(null);
    try {
      await deleteApplicationApi(appId);
      setApplications((prev) => prev.filter((item) => item.id !== appId));
      if (activeModalApp && activeModalApp.id === appId) {
        setActiveModalApp(null);
      }
      setSuccessMsg(`Application removed.`);
      setTimeout(() => setSuccessMsg(null), 3000);

      const updatedMetrics = await getPipelineMetricsApi();
      setMetrics(updatedMetrics);
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to delete application.');
    } finally {
      setActionLoading(false);
    }
  };

  // Create Manual Application
  const handleCreateManualApp = async (e) => {
    e.preventDefault();
    if (!newTitle.trim() || !newCompany.trim()) {
      setErrorMsg('Role title and company name are required.');
      return;
    }
    setActionLoading(true);
    setErrorMsg(null);
    try {
      const payload = {
        job_title: newTitle.trim(),
        company_name: newCompany.trim(),
        source_platform: newPlatform,
        source_url: newSourceUrl.trim() || undefined,
        status: newInitialStage,
        notes: newNotes.trim() || undefined,
        recruiter_contact: newRecruiterEmail.trim()
          ? { email: newRecruiterEmail.trim() }
          : undefined
      };
      const created = await createApplicationApi(payload);
      setApplications((prev) => [created, ...prev]);
      setShowAddModal(false);
      setNewTitle('');
      setNewCompany('');
      setNewNotes('');
      setNewSourceUrl('');
      setNewRecruiterEmail('');
      setSuccessMsg(`Added "${created.job_title}" at "${created.company_name}" to your tracker.`);
      setTimeout(() => setSuccessMsg(null), 3500);

      const updatedMetrics = await getPipelineMetricsApi();
      setMetrics(updatedMetrics);
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to create application.');
    } finally {
      setActionLoading(false);
    }
  };

  // Follow-Up Assistant Handlers
  const handleOpenFollowUp = async (app, initialTone = 'professional') => {
    setFollowUpApp(app);
    setFollowUpTone(initialTone);
    setFollowUpLoading(true);
    setFollowUpCopied(false);
    setErrorMsg(null);
    try {
      const data = await draftFollowUpApi(app.id, { tone: initialTone });
      setFollowUpSubject(data.subject);
      setFollowUpBody(data.body);
      setFollowUpRecipient(data.recipient_email || '');
      setFollowUpMailto(data.mailto_link || '');
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to generate follow-up draft.');
    } finally {
      setFollowUpLoading(false);
    }
  };

  const handleToneChange = async (tone) => {
    setFollowUpTone(tone);
    if (!followUpApp) return;
    setFollowUpLoading(true);
    try {
      const data = await draftFollowUpApi(followUpApp.id, { tone });
      setFollowUpSubject(data.subject);
      setFollowUpBody(data.body);
      setFollowUpMailto(data.mailto_link || '');
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to update follow-up tone.');
    } finally {
      setFollowUpLoading(false);
    }
  };

  const handleCopyFollowUp = async () => {
    const fullText = `Subject: ${followUpSubject}\n\n${followUpBody}`;
    try {
      await navigator.clipboard.writeText(fullText);
      setFollowUpCopied(true);
      setTimeout(() => setFollowUpCopied(false), 3000);
      setSuccessMsg('Email draft copied to clipboard!');
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch {
      setErrorMsg('Failed to copy to clipboard.');
    }
  };

  const handleLogFollowUp = async () => {
    if (!followUpApp) return;
    setFollowUpLogging(true);
    setErrorMsg(null);
    try {
      await logFollowUpActionApi(followUpApp.id, {
        notes: `Follow-up email sent (${followUpTone} tone): "${followUpSubject}"`
      });
      setSuccessMsg(`Follow-up logged in ${followUpApp.company_name} timeline!`);
      setTimeout(() => setSuccessMsg(null), 3500);
      setFollowUpApp(null);
      fetchTrackerData();
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to log follow-up action.');
    } finally {
      setFollowUpLogging(false);
    }
  };

  // Filtered applications
  const filteredApps = useMemo(() => {
    return applications.filter((app) => {
      const matchesSearch =
        !searchTerm.trim() ||
        app.job_title?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        app.company_name?.toLowerCase().includes(searchTerm.toLowerCase());
      const matchesPlatform =
        platformFilter === 'All' ||
        app.source_platform?.toLowerCase() === platformFilter.toLowerCase();
      return matchesSearch && matchesPlatform;
    });
  }, [applications, searchTerm, platformFilter]);

  // Map of application ID to count of matched emails
  const emailCounts = useMemo(() => {
    const counts = {};
    emails.forEach((em) => {
      if (em.application_id) {
        counts[em.application_id] = (counts[em.application_id] || 0) + 1;
      }
    });
    return counts;
  }, [emails]);

  // Group applications by stage
  const appsByStage = useMemo(() => {
    const grouped = {};
    STAGES.forEach((s) => {
      grouped[s.key] = [];
    });
    filteredApps.forEach((app) => {
      if (grouped[app.status]) {
        grouped[app.status].push(app);
      } else {
        // Fallback for unexpected stage
        grouped['APPLIED'].push(app);
      }
    });
    return grouped;
  }, [filteredApps]);

  // Format date helper
  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
    } catch {
      return dateStr;
    }
  };

  return (
    <div style={styles.container}>
      {/* Page Header */}
      <div style={styles.pageHeader}>
        <div>
          <div style={styles.titleBadge}>
            <Kanban size={16} color="#2563eb" />
            <span>Interactive Application Pipeline</span>
          </div>
          <h1 style={styles.pageTitle}>Job Application Tracker</h1>
          <p style={styles.pageSubtitle}>
            Monitor your job pipeline stages, log recruiter communications, and prepare for upcoming interviews.
          </p>
        </div>
        <div style={styles.headerActions}>
          <button
            onClick={fetchTrackerData}
            style={styles.refreshBtn}
            disabled={loading}
            title="Refresh application data"
          >
            <RotateCw size={15} className={loading ? 'spin' : ''} />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            style={styles.primaryAddBtn}
          >
            <PlusCircle size={16} />
            <span>Track Application</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {errorMsg && (
        <div style={styles.errorBanner}>
          <AlertCircle size={18} color="#dc2626" />
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

      {/* Pipeline Metrics Overview */}
      <div style={styles.metricsGrid}>
        <div style={styles.metricCard}>
          <div style={{ ...styles.metricIconWrap, backgroundColor: '#eff6ff', color: '#2563eb' }}>
            <Layers size={20} />
          </div>
          <div>
            <span style={styles.metricLabel}>Total Applications</span>
            <div style={styles.metricValue}>{metrics.total_applications || 0}</div>
          </div>
        </div>

        <div style={styles.metricCard}>
          <div style={{ ...styles.metricIconWrap, backgroundColor: '#fffbeb', color: '#d97706' }}>
            <Video size={20} />
          </div>
          <div>
            <span style={styles.metricLabel}>Active Interviews</span>
            <div style={styles.metricValue}>{metrics.active_interviews || 0}</div>
          </div>
        </div>

        <div style={styles.metricCard}>
          <div style={{ ...styles.metricIconWrap, backgroundColor: '#f5f3ff', color: '#7c3aed' }}>
            <Clock size={20} />
          </div>
          <div>
            <span style={styles.metricLabel}>Assessments Due</span>
            <div style={styles.metricValue}>{metrics.tests_due || 0}</div>
          </div>
        </div>

        <div style={styles.metricCard}>
          <div style={{ ...styles.metricIconWrap, backgroundColor: '#ecfdf5', color: '#059669' }}>
            <Award size={20} />
          </div>
          <div>
            <span style={styles.metricLabel}>Offers Received</span>
            <div style={styles.metricValue}>{metrics.offers_received || 0}</div>
          </div>
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      <div style={styles.toolbar}>
        <div style={styles.searchWrap}>
          <Search size={16} color="#9ca3af" />
          <input
            type="text"
            placeholder="Filter by role title or company..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            style={styles.searchInput}
          />
          {searchTerm && (
            <button onClick={() => setSearchTerm('')} style={styles.clearSearchBtn}>
              <X size={14} />
            </button>
          )}
        </div>

        <div style={styles.filterGroup}>
          <span style={styles.filterLabel}>Source:</span>
          <select
            value={platformFilter}
            onChange={(e) => setPlatformFilter(e.target.value)}
            style={styles.selectFilter}
          >
            <option value="All">All Sources</option>
            <option value="LinkedIn">LinkedIn</option>
            <option value="Naukri">Naukri</option>
            <option value="Indeed">Indeed</option>
            <option value="Company Site">Company Career Site</option>
            <option value="Direct">Direct</option>
            <option value="Portal">Portal</option>
          </select>
        </div>

        <div style={styles.totalBadge}>
          {filteredApps.length} {filteredApps.length === 1 ? 'Card' : 'Cards'} Active
        </div>
      </div>

      {/* Kanban Board Container */}
      {loading ? (
        <div style={styles.loadingContainer}>
          <Loader2 size={36} className="spin" color="#2563eb" />
          <p style={styles.loadingText}>Loading candidate pipeline...</p>
        </div>
      ) : applications.length === 0 ? (
        <div style={styles.emptyKanban}>
          <Kanban size={48} color="#9ca3af" />
          <h3 style={styles.emptyTitle}>No Applications Tracked Yet</h3>
          <p style={styles.emptySubtitle}>
            Track jobs directly from Job Discovery or manually track your external applications here.
          </p>
          <button
            onClick={() => setShowAddModal(true)}
            style={styles.primaryAddBtn}
          >
            <PlusCircle size={16} />
            <span>Track First Application</span>
          </button>
        </div>
      ) : (
        <div style={styles.kanbanBoard}>
          {STAGES.map((col) => {
            const colApps = appsByStage[col.key] || [];
            return (
              <div key={col.key} style={styles.kanbanColumn}>
                {/* Column Header */}
                <div style={{ ...styles.columnHeader, borderTopColor: col.color }}>
                  <div style={styles.colTitleRow}>
                    <div style={{ ...styles.colIndicator, backgroundColor: col.color }} />
                    <span style={styles.colTitle}>{col.label}</span>
                    <span style={{ ...styles.colCountBadge, backgroundColor: col.bg, color: col.color }}>
                      {colApps.length}
                    </span>
                  </div>
                </div>

                {/* Column Card List */}
                <div style={styles.columnBody}>
                  {colApps.length === 0 ? (
                    <div style={styles.emptyColPlaceholder}>
                      <span>No applications</span>
                    </div>
                  ) : (
                    colApps.map((app) => (
                      <div key={app.id} style={styles.appCard}>
                        {/* Card Header */}
                        <div style={styles.cardHeader}>
                          <h4 style={styles.cardJobTitle} title={app.job_title}>
                            {app.job_title}
                          </h4>
                          <span
                            style={{
                              ...styles.platformTag,
                              backgroundColor:
                                app.source_platform?.toLowerCase() === 'linkedin'
                                  ? '#eff6ff'
                                  : app.source_platform?.toLowerCase() === 'naukri'
                                  ? '#fff7ed'
                                  : '#f3f4f6',
                              color:
                                app.source_platform?.toLowerCase() === 'linkedin'
                                  ? '#1d4ed8'
                                  : app.source_platform?.toLowerCase() === 'naukri'
                                  ? '#c2410c'
                                  : '#374151',
                            }}
                          >
                            {app.source_platform || 'Direct'}
                          </span>
                        </div>

                        {/* Company */}
                        <div style={styles.companyRow}>
                          <Building2 size={13} color="#6b7280" />
                          <span style={styles.companyName}>{app.company_name}</span>
                        </div>

                        {/* Metadata: Applied date & Inactivity */}
                        <div style={styles.cardMeta}>
                          <div style={styles.cardMetaItem} title="Applied Date">
                            <Calendar size={12} color="#9ca3af" />
                            <span>{formatDate(app.applied_at || app.created_at)}</span>
                          </div>
                          <div
                            style={{
                              ...styles.cardMetaItem,
                              color:
                                app.days_since_activity >= 14
                                  ? '#dc2626'
                                  : app.days_since_activity >= 7
                                  ? '#d97706'
                                  : '#6b7280',
                            }}
                            title="Days since last status update or activity"
                          >
                            <Clock size={12} />
                            <span>
                              {app.days_since_activity === 0
                                ? 'Active today'
                                : `${app.days_since_activity}d ago`}
                            </span>
                          </div>
                        </div>

                        {/* Interview or Assessment alert snippet if present */}
                        {app.interview_details?.scheduled_at && (
                          <div style={styles.cardInterviewBadge}>
                            <Video size={12} color="#d97706" />
                            <span>
                              Interview: {formatDate(app.interview_details.scheduled_at)}
                            </span>
                          </div>
                        )}

                        {app.interview_details?.assessment_deadline && (
                          <div style={styles.cardAssessmentBadge}>
                            <Clock size={12} color="#7c3aed" />
                            <span>
                              Due: {formatDate(app.interview_details.assessment_deadline)}
                            </span>
                          </div>
                        )}

                        {/* Resume version badge */}
                        {app.resume_version && (
                          <div style={styles.cardResumeBadge}>
                            <FileText size={11} color="#4b5563" />
                            <span>{app.resume_version}</span>
                          </div>
                        )}

                        {/* Incoming Communications Badge */}
                        {emailCounts[app.id] > 0 && (
                          <div
                            style={styles.cardEmailBadge}
                            onClick={(e) => {
                              e.stopPropagation();
                              navigate('/emails');
                            }}
                            title={`${emailCounts[app.id]} recruitment communication(s) linked. Click to inspect in Email Hub.`}
                          >
                            <Mail size={11} color="#1d4ed8" />
                            <span>
                              {emailCounts[app.id]} Incoming Comm{emailCounts[app.id] === 1 ? '' : 's'}
                            </span>
                          </div>
                        )}

                        {/* Visual Aging Indicator Pill */}
                        {app.status !== 'REJECTED' && app.status !== 'OFFER' && app.days_since_activity >= 3 && (
                          <div
                            style={
                              app.days_since_activity >= 14
                                ? styles.cardStaleLeadPill
                                : styles.cardStalledPill
                            }
                            title={
                              app.days_since_activity >= 14
                                ? `Stale Lead: ${app.days_since_activity} days inactive without status update`
                                : `Stalled: ${app.days_since_activity} days without update. Consider sending a follow-up inquiry.`
                            }
                          >
                            <Clock size={11} />
                            <span>
                              {app.days_since_activity >= 14
                                ? `Stale Lead: ${app.days_since_activity}d inactive`
                                : `Stalled: ${app.days_since_activity} days without update`}
                            </span>
                          </div>
                        )}

                        {/* Quick-Action: Draft Follow-Up Directly on Stalled Cards */}
                        {app.status !== 'REJECTED' && app.status !== 'OFFER' && app.days_since_activity >= 3 && (
                          <button
                            type="button"
                            onClick={() => handleOpenFollowUp(app)}
                            style={styles.cardFollowUpBtn}
                            title="Draft a professional follow-up email tailored to this application stage"
                          >
                            <Sparkles size={12} color="#7c3aed" />
                            <span>Draft Follow-Up</span>
                          </button>
                        )}

                        {/* Card Actions Footer */}
                        <div style={styles.cardFooter}>
                          {/* Quick Stage Mover */}
                          <div style={styles.stageMoverWrap}>
                            <select
                              value={app.status}
                              onChange={(e) => handleInitiateStageChange(app, e.target.value)}
                              style={styles.stageSelect}
                              title="Advance or transition pipeline stage"
                            >
                              {STAGES.map((s) => (
                                <option key={s.key} value={s.key}>
                                  → {s.label}
                                </option>
                              ))}
                            </select>
                          </div>

                          <div style={styles.cardActionBtns}>
                            <button
                              onClick={() => handleOpenDetails(app)}
                              style={styles.cardEditBtn}
                              title="View & Edit Details, Recruiter Notes, and Timeline"
                            >
                              <Edit3 size={13} />
                            </button>
                            <button
                              onClick={() => handleDeleteApplication(app.id, app.company_name)}
                              style={styles.cardDeleteBtn}
                              title="Delete application"
                            >
                              <Trash2 size={13} />
                            </button>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modal: Application Details, Recruiter Info, and Timeline */}
      {activeModalApp && (
        <div style={styles.modalOverlay} onClick={() => setActiveModalApp(null)}>
          <div style={styles.detailsModalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <h2 style={styles.modalTitle}>{activeModalApp.job_title}</h2>
                  <span
                    style={{
                      ...styles.stagePill,
                      backgroundColor:
                        STAGES.find((s) => s.key === activeModalApp.status)?.bg || '#eff6ff',
                      color:
                        STAGES.find((s) => s.key === activeModalApp.status)?.color || '#2563eb',
                      borderColor:
                        STAGES.find((s) => s.key === activeModalApp.status)?.border || '#bfdbfe',
                    }}
                  >
                    {activeModalApp.status}
                  </span>
                </div>
                <p style={styles.modalSub}>{activeModalApp.company_name}</p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <button
                  type="button"
                  onClick={() => handleOpenFollowUp(activeModalApp)}
                  style={styles.modalFollowUpBtn}
                  title="Draft context-aware follow-up email"
                >
                  <Sparkles size={13} color="#7c3aed" />
                  <span>Draft Follow-Up</span>
                </button>
                <button onClick={() => setActiveModalApp(null)} style={styles.modalCloseBtn}>
                  <X size={20} />
                </button>
              </div>
            </div>

            <div style={styles.modalBodyTwoCol}>
              {/* Left Column: Form Details */}
              <form onSubmit={handleSaveDetails} style={styles.detailsFormCol}>
                <h3 style={styles.sectionHeading}>Recruiter & Pipeline Details</h3>

                {/* Recruiter contact */}
                <div style={styles.formRow}>
                  <div style={styles.formField}>
                    <label style={styles.formLabel}>
                      <Mail size={12} style={{ marginRight: '4px' }} />
                      Recruiter Email
                    </label>
                    <input
                      type="email"
                      placeholder="e.g. talent@company.com"
                      value={editRecruiterEmail}
                      onChange={(e) => setEditRecruiterEmail(e.target.value)}
                      style={styles.formInput}
                    />
                  </div>
                  <div style={styles.formField}>
                    <label style={styles.formLabel}>Recruiter Name</label>
                    <input
                      type="text"
                      placeholder="e.g. Jane Doe"
                      value={editRecruiterName}
                      onChange={(e) => setEditRecruiterName(e.target.value)}
                      style={styles.formInput}
                    />
                  </div>
                </div>

                <div style={styles.formRow}>
                  <div style={styles.formField}>
                    <label style={styles.formLabel}>
                      <Phone size={12} style={{ marginRight: '4px' }} />
                      Recruiter Phone
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. +1 555-0192"
                      value={editRecruiterPhone}
                      onChange={(e) => setEditRecruiterPhone(e.target.value)}
                      style={styles.formInput}
                    />
                  </div>
                  <div style={styles.formField}>
                    <label style={styles.formLabel}>
                      <FileText size={12} style={{ marginRight: '4px' }} />
                      Resume Version
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. v2_fullstack.pdf"
                      value={editResumeVersion}
                      onChange={(e) => setEditResumeVersion(e.target.value)}
                      style={styles.formInput}
                    />
                  </div>
                </div>

                <h3 style={{ ...styles.sectionHeading, marginTop: '16px' }}>
                  Interview & Assessment Coordination
                </h3>

                <div style={styles.formRow}>
                  <div style={styles.formField}>
                    <label style={styles.formLabel}>Interview Platform / Tool</label>
                    <input
                      type="text"
                      placeholder="e.g. Google Meet, Zoom, HackerRank"
                      value={editInterviewPlatform}
                      onChange={(e) => setEditInterviewPlatform(e.target.value)}
                      style={styles.formInput}
                    />
                  </div>
                  <div style={styles.formField}>
                    <label style={styles.formLabel}>Meeting / Test Link</label>
                    <input
                      type="url"
                      placeholder="https://meet.google.com/..."
                      value={editInterviewLink}
                      onChange={(e) => setEditInterviewLink(e.target.value)}
                      style={styles.formInput}
                    />
                  </div>
                </div>

                <div style={styles.formRow}>
                  <div style={styles.formField}>
                    <label style={styles.formLabel}>
                      <Calendar size={12} style={{ marginRight: '4px' }} />
                      Scheduled Interview Date
                    </label>
                    <input
                      type="date"
                      value={editInterviewDate}
                      onChange={(e) => setEditInterviewDate(e.target.value)}
                      style={styles.formInput}
                    />
                  </div>
                  <div style={styles.formField}>
                    <label style={styles.formLabel}>
                      <Clock size={12} style={{ marginRight: '4px' }} />
                      Assessment Due Date
                    </label>
                    <input
                      type="date"
                      value={editAssessmentDeadline}
                      onChange={(e) => setEditAssessmentDeadline(e.target.value)}
                      style={styles.formInput}
                    />
                  </div>
                </div>

                <div style={{ marginTop: '14px' }}>
                  <label style={styles.formLabel}>Candidate Notes & Interview Prep</label>
                  <textarea
                    rows={4}
                    placeholder="Log recruiter notes, questions asked, salary discussed, or follow-up items..."
                    value={editNotes}
                    onChange={(e) => setEditNotes(e.target.value)}
                    style={styles.formTextarea}
                  />
                </div>

                {activeModalApp.source_url && (
                  <div style={{ marginTop: '14px' }}>
                    <a
                      href={activeModalApp.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={styles.externalLinkBtn}
                    >
                      <span>View Original Job Posting</span>
                      <ExternalLink size={14} />
                    </a>
                  </div>
                )}

                <div style={styles.modalBtnRow}>
                  <button
                    type="submit"
                    disabled={actionLoading}
                    style={styles.modalSaveBtn}
                  >
                    {actionLoading ? <Loader2 size={16} className="spin" /> : <CheckCircle2 size={16} />}
                    <span>Save Application Details</span>
                  </button>
                </div>
              </form>

              {/* Right Column: Stage Timeline History */}
              <div style={styles.timelineCol}>
                <h3 style={styles.sectionHeading}>Stage Transition History</h3>
                <div style={styles.timelineList}>
                  {activeModalApp.timeline_events && activeModalApp.timeline_events.length > 0 ? (
                    activeModalApp.timeline_events.map((evt, idx) => (
                      <div key={idx} style={styles.timelineItem}>
                        <div style={styles.timelineMarker} />
                        <div style={styles.timelineCard}>
                          <div style={styles.timelineHeader}>
                            <span style={styles.timelineStageBadge}>{evt.stage}</span>
                            <span style={styles.timelineTimestamp}>
                              {formatDate(evt.timestamp)}
                            </span>
                          </div>
                          {evt.notes && (
                            <p style={styles.timelineNotes}>{evt.notes}</p>
                          )}
                        </div>
                      </div>
                    ))
                  ) : (
                    <p style={styles.timelineEmpty}>No stage changes recorded yet.</p>
                  )}
                </div>

                {/* Direct Stage Advancement from Modal */}
                <div style={styles.modalStageMoverBox}>
                  <label style={styles.formLabel}>Advance Stage:</label>
                  <div style={styles.modalStageButtons}>
                    {STAGES.map((s) => (
                      <button
                        key={s.key}
                        type="button"
                        onClick={() => handleInitiateStageChange(activeModalApp, s.key)}
                        disabled={activeModalApp.status === s.key || actionLoading}
                        style={{
                          ...styles.stageChoiceBtn,
                          backgroundColor: activeModalApp.status === s.key ? s.color : '#ffffff',
                          color: activeModalApp.status === s.key ? '#ffffff' : '#374151',
                          borderColor: s.border,
                        }}
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Confirm Stage Transition with Note */}
      {showStagePrompt && (
        <div style={styles.modalOverlay} onClick={() => setShowStagePrompt(null)}>
          <div style={styles.confirmModalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div>
                <h3 style={styles.modalTitle}>Confirm Stage Transition</h3>
                <p style={styles.modalSub}>
                  Advancing {showStagePrompt.app.company_name} from{' '}
                  <strong>{showStagePrompt.app.status}</strong> to{' '}
                  <strong style={{ color: '#2563eb' }}>{showStagePrompt.targetStage}</strong>
                </p>
              </div>
              <button onClick={() => setShowStagePrompt(null)} style={styles.modalCloseBtn}>
                <X size={18} />
              </button>
            </div>

            <div style={{ marginTop: '16px' }}>
              <label style={styles.formLabel}>Transition Note (optional):</label>
              <textarea
                rows={3}
                placeholder="e.g. Completed technical round 1 with hiring manager..."
                value={showStagePrompt.note}
                onChange={(e) =>
                  setShowStagePrompt((prev) => ({ ...prev, note: e.target.value }))
                }
                style={styles.formTextarea}
              />
            </div>

            <div style={styles.modalActionRow}>
              <button
                type="button"
                onClick={() => setShowStagePrompt(null)}
                style={styles.cancelBtn}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmStageChange}
                disabled={actionLoading}
                style={styles.primaryAddBtn}
              >
                {actionLoading ? <Loader2 size={16} className="spin" /> : <ArrowRight size={16} />}
                <span>Advance to {showStagePrompt.targetStage}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Add Manual Application */}
      {showAddModal && (
        <div style={styles.modalOverlay} onClick={() => setShowAddModal(false)}>
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div>
                <h2 style={styles.modalTitle}>Track New Application</h2>
                <p style={styles.modalSub}>
                  Record an application you submitted externally or via company career site
                </p>
              </div>
              <button onClick={() => setShowAddModal(false)} style={styles.modalCloseBtn}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleCreateManualApp} style={styles.modalBody}>
              <div style={styles.formRow}>
                <div style={styles.formField}>
                  <label style={styles.formLabel}>Role / Job Title *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Software Engineer"
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    style={styles.formInput}
                  />
                </div>
                <div style={styles.formField}>
                  <label style={styles.formLabel}>Company Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Microsoft, Razorpay"
                    value={newCompany}
                    onChange={(e) => setNewCompany(e.target.value)}
                    style={styles.formInput}
                  />
                </div>
              </div>

              <div style={styles.formRow}>
                <div style={styles.formField}>
                  <label style={styles.formLabel}>Source Platform</label>
                  <select
                    value={newPlatform}
                    onChange={(e) => setNewPlatform(e.target.value)}
                    style={styles.formInput}
                  >
                    <option value="LinkedIn">LinkedIn</option>
                    <option value="Naukri">Naukri</option>
                    <option value="Indeed">Indeed</option>
                    <option value="Company Site">Company Career Site</option>
                    <option value="Referral">Referral</option>
                    <option value="Direct">Direct</option>
                  </select>
                </div>
                <div style={styles.formField}>
                  <label style={styles.formLabel}>Initial Pipeline Stage</label>
                  <select
                    value={newInitialStage}
                    onChange={(e) => setNewInitialStage(e.target.value)}
                    style={styles.formInput}
                  >
                    {STAGES.map((s) => (
                      <option key={s.key} value={s.key}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div style={styles.formRow}>
                <div style={styles.formField}>
                  <label style={styles.formLabel}>Source Job URL</label>
                  <input
                    type="url"
                    placeholder="https://..."
                    value={newSourceUrl}
                    onChange={(e) => setNewSourceUrl(e.target.value)}
                    style={styles.formInput}
                  />
                </div>
                <div style={styles.formField}>
                  <label style={styles.formLabel}>Recruiter Contact Email</label>
                  <input
                    type="email"
                    placeholder="recruiter@company.com"
                    value={newRecruiterEmail}
                    onChange={(e) => setNewRecruiterEmail(e.target.value)}
                    style={styles.formInput}
                  />
                </div>
              </div>

              <div style={{ marginTop: '12px' }}>
                <label style={styles.formLabel}>Initial Notes & Details</label>
                <textarea
                  rows={3}
                  placeholder="Applied with resume v2, referral from alum..."
                  value={newNotes}
                  onChange={(e) => setNewNotes(e.target.value)}
                  style={styles.formTextarea}
                />
              </div>

              <div style={styles.modalBtnRow}>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  style={styles.cancelBtn}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={actionLoading}
                  style={styles.primaryAddBtn}
                >
                  {actionLoading ? <Loader2 size={16} className="spin" /> : <PlusCircle size={16} />}
                  <span>Save to Pipeline</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Follow-Up Email Drafter */}
      {followUpApp && (
        <div style={styles.modalOverlay} onClick={() => setFollowUpApp(null)}>
          <div style={styles.followUpModalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <h2 style={styles.modalTitle}>Professional Follow-Up Assistant</h2>
                  <span style={styles.followUpStageTag}>{followUpApp.status}</span>
                </div>
                <p style={styles.modalSub}>
                  {followUpApp.job_title} at {followUpApp.company_name}
                </p>
              </div>
              <button onClick={() => setFollowUpApp(null)} style={styles.modalCloseBtn}>
                <X size={20} />
              </button>
            </div>

            <div style={styles.followUpModalBody}>
              {/* Tone Selector */}
              <div style={styles.toneSelectorRow}>
                <span style={styles.toneLabel}>Email Tone:</span>
                <button
                  type="button"
                  onClick={() => handleToneChange('polite')}
                  style={{
                    ...styles.toneBtn,
                    ...(followUpTone === 'polite' ? styles.toneBtnActive : {}),
                  }}
                >
                  Polite & Enthusiastic
                </button>
                <button
                  type="button"
                  onClick={() => handleToneChange('professional')}
                  style={{
                    ...styles.toneBtn,
                    ...(followUpTone === 'professional' ? styles.toneBtnActive : {}),
                  }}
                >
                  Professional & Balanced
                </button>
                <button
                  type="button"
                  onClick={() => handleToneChange('firm')}
                  style={{
                    ...styles.toneBtn,
                    ...(followUpTone === 'firm' ? styles.toneBtnActive : {}),
                  }}
                >
                  Firm & Time-Sensitive
                </button>
              </div>

              {/* Recipient */}
              {followUpRecipient && (
                <div style={styles.recipientRow}>
                  <Mail size={13} color="#6b7280" />
                  <span style={styles.recipientLabel}>Recipient:</span>
                  <span style={styles.recipientVal}>{followUpRecipient}</span>
                </div>
              )}

              {/* Subject */}
              <div style={styles.followUpFieldGroup}>
                <label style={styles.formLabel}>Subject Line</label>
                <input
                  type="text"
                  value={followUpSubject}
                  onChange={(e) => setFollowUpSubject(e.target.value)}
                  style={styles.formInput}
                />
              </div>

              {/* Body */}
              <div style={styles.followUpFieldGroup}>
                <label style={styles.formLabel}>Message Body</label>
                {followUpLoading ? (
                  <div style={styles.draftLoadingBox}>
                    <Loader2 size={24} className="spin" color="#2563eb" />
                    <span>Personalizing follow-up template...</span>
                  </div>
                ) : (
                  <textarea
                    rows={9}
                    value={followUpBody}
                    onChange={(e) => setFollowUpBody(e.target.value)}
                    style={styles.formTextarea}
                  />
                )}
              </div>

              {/* Strict Candidate Consent Notice */}
              <div style={styles.consentNotice}>
                <CheckCircle2 size={15} color="#059669" />
                <span>
                  <strong>Strict Candidate-Consent Enforced:</strong> Unified Job Search never sends emails automatically. You retain full control to edit, copy, or send through your default email client.
                </span>
              </div>

              {/* Actions Footer */}
              <div style={styles.followUpActionsRow}>
                <button
                  type="button"
                  onClick={handleCopyFollowUp}
                  style={styles.copyBtn}
                >
                  {followUpCopied ? <Check size={15} color="#059669" /> : <Copy size={15} />}
                  <span>{followUpCopied ? 'Copied to Clipboard!' : 'Copy to Clipboard'}</span>
                </button>

                {followUpMailto && (
                  <a
                    href={followUpMailto}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={styles.mailtoBtn}
                  >
                    <ExternalLink size={15} />
                    <span>Open in Email Client</span>
                  </a>
                )}

                <button
                  type="button"
                  onClick={handleLogFollowUp}
                  disabled={followUpLogging}
                  style={styles.logTimelineBtn}
                  title="Record follow-up outreach in application timeline"
                >
                  {followUpLogging ? (
                    <Loader2 size={15} className="spin" />
                  ) : (
                    <CheckCircle2 size={15} />
                  )}
                  <span>Log Follow-Up Sent</span>
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
    maxWidth: '1440px',
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
    maxWidth: '650px',
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
    transition: 'all 0.15s ease',
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
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
    gap: '14px',
    marginBottom: '22px',
  },
  metricCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '14px',
    padding: '16px 20px',
    backgroundColor: '#ffffff',
    border: '1px solid #e5e7eb',
    borderRadius: '10px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.03)',
  },
  metricIconWrap: {
    width: '44px',
    height: '44px',
    borderRadius: '10px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  metricLabel: {
    fontSize: '12px',
    fontWeight: '500',
    color: '#6b7280',
    display: 'block',
  },
  metricValue: {
    fontSize: '22px',
    fontWeight: '700',
    color: '#111827',
  },
  toolbar: {
    display: 'flex',
    alignItems: 'center',
    gap: '14px',
    backgroundColor: '#ffffff',
    padding: '12px 18px',
    borderRadius: '10px',
    border: '1px solid #e5e7eb',
    marginBottom: '22px',
    flexWrap: 'wrap',
  },
  searchWrap: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flex: '1',
    minWidth: '240px',
  },
  searchInput: {
    width: '100%',
    border: 'none',
    outline: 'none',
    fontSize: '14px',
    color: '#111827',
  },
  clearSearchBtn: {
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#9ca3af',
  },
  filterGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  filterLabel: {
    fontSize: '13px',
    color: '#6b7280',
    fontWeight: '500',
  },
  selectFilter: {
    padding: '6px 10px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    fontSize: '13px',
    color: '#374151',
    backgroundColor: '#ffffff',
    outline: 'none',
  },
  totalBadge: {
    marginLeft: 'auto',
    fontSize: '12px',
    fontWeight: '600',
    color: '#6b7280',
    backgroundColor: '#f3f4f6',
    padding: '4px 10px',
    borderRadius: '12px',
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
  emptyKanban: {
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
  kanbanBoard: {
    display: 'grid',
    gridTemplateColumns: 'repeat(6, minmax(230px, 1fr))',
    gap: '14px',
    alignItems: 'start',
    overflowX: 'auto',
    paddingBottom: '16px',
  },
  kanbanColumn: {
    backgroundColor: '#f9fafb',
    borderRadius: '10px',
    border: '1px solid #e5e7eb',
    minHeight: '480px',
    display: 'flex',
    flexDirection: 'column',
  },
  columnHeader: {
    padding: '12px 14px',
    backgroundColor: '#ffffff',
    borderTopLeftRadius: '10px',
    borderTopRightRadius: '10px',
    borderBottom: '1px solid #e5e7eb',
    borderTop: '3px solid transparent',
  },
  colTitleRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  colIndicator: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
  },
  colTitle: {
    fontSize: '13px',
    fontWeight: '700',
    color: '#1f2937',
    flex: 1,
  },
  colCountBadge: {
    fontSize: '11px',
    fontWeight: '700',
    padding: '2px 7px',
    borderRadius: '10px',
  },
  columnBody: {
    padding: '12px 10px',
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
    flex: 1,
  },
  emptyColPlaceholder: {
    textAlign: 'center',
    padding: '30px 10px',
    color: '#9ca3af',
    fontSize: '12px',
    border: '1px dashed #e5e7eb',
    borderRadius: '8px',
  },
  appCard: {
    backgroundColor: '#ffffff',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    padding: '12px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    transition: 'transform 0.15s ease, box-shadow 0.15s ease',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: '6px',
  },
  cardJobTitle: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#111827',
    margin: 0,
    lineHeight: 1.3,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    display: '-webkit-box',
    WebkitLineClamp: 2,
    WebkitBoxOrient: 'vertical',
  },
  platformTag: {
    fontSize: '10px',
    fontWeight: '700',
    padding: '2px 6px',
    borderRadius: '4px',
    textTransform: 'uppercase',
    letterSpacing: '0.4px',
    whiteSpace: 'nowrap',
  },
  companyRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '5px',
  },
  companyName: {
    fontSize: '12px',
    color: '#4b5563',
    fontWeight: '500',
  },
  cardMeta: {
    display: 'flex',
    justifyContent: 'space-between',
    fontSize: '11px',
    color: '#6b7280',
    paddingTop: '4px',
    borderTop: '1px solid #f3f4f6',
  },
  cardMetaItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  cardInterviewBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '5px',
    fontSize: '11px',
    fontWeight: '600',
    color: '#92400e',
    backgroundColor: '#fef3c7',
    padding: '4px 7px',
    borderRadius: '5px',
  },
  cardAssessmentBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '5px',
    fontSize: '11px',
    fontWeight: '600',
    color: '#5b21b6',
    backgroundColor: '#ede9fe',
    padding: '4px 7px',
    borderRadius: '5px',
  },
  cardResumeBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '11px',
    color: '#4b5563',
    backgroundColor: '#f3f4f6',
    padding: '2px 6px',
    borderRadius: '4px',
    width: 'fit-content',
  },
  cardEmailBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '11px',
    fontWeight: '600',
    color: '#1d4ed8',
    backgroundColor: '#eff6ff',
    border: '1px solid #bfdbfe',
    padding: '3px 7px',
    borderRadius: '5px',
    cursor: 'pointer',
    width: 'fit-content',
    transition: 'all 0.15s ease',
  },
  cardFooter: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: '6px',
    borderTop: '1px solid #f3f4f6',
    gap: '6px',
  },
  stageMoverWrap: {
    flex: 1,
  },
  stageSelect: {
    width: '100%',
    padding: '4px 6px',
    fontSize: '11px',
    fontWeight: '600',
    color: '#374151',
    backgroundColor: '#f9fafb',
    border: '1px solid #d1d5db',
    borderRadius: '4px',
    cursor: 'pointer',
  },
  cardActionBtns: {
    display: 'flex',
    gap: '4px',
  },
  cardEditBtn: {
    padding: '4px 6px',
    backgroundColor: '#f3f4f6',
    border: '1px solid #e5e7eb',
    borderRadius: '4px',
    color: '#4b5563',
    cursor: 'pointer',
  },
  cardDeleteBtn: {
    padding: '4px 6px',
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '4px',
    color: '#dc2626',
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
  detailsModalContent: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    width: '100%',
    maxWidth: '920px',
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
    overflow: 'hidden',
  },
  confirmModalContent: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    width: '100%',
    maxWidth: '480px',
    padding: '24px',
    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
  },
  modalContent: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    width: '100%',
    maxWidth: '620px',
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
    fontSize: '20px',
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
  stagePill: {
    fontSize: '11px',
    fontWeight: '700',
    padding: '2px 8px',
    borderRadius: '12px',
    border: '1px solid',
  },
  modalBodyTwoCol: {
    display: 'grid',
    gridTemplateColumns: '1.2fr 0.8fr',
    gap: '24px',
    padding: '24px',
    overflowY: 'auto',
  },
  detailsFormCol: {
    display: 'flex',
    flexDirection: 'column',
  },
  timelineCol: {
    borderLeft: '1px solid #e5e7eb',
    paddingLeft: '20px',
    display: 'flex',
    flexDirection: 'column',
  },
  sectionHeading: {
    fontSize: '14px',
    fontWeight: '700',
    color: '#1f2937',
    marginBottom: '12px',
  },
  formRow: {
    display: 'flex',
    gap: '12px',
    marginBottom: '12px',
  },
  formField: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
  },
  formLabel: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#4b5563',
    marginBottom: '4px',
    display: 'flex',
    alignItems: 'center',
  },
  formInput: {
    padding: '8px 10px',
    fontSize: '13px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
    color: '#111827',
    outline: 'none',
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
    resize: 'vertical',
  },
  externalLinkBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '13px',
    fontWeight: '600',
    color: '#2563eb',
    textDecoration: 'none',
  },
  modalBtnRow: {
    marginTop: '20px',
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px',
  },
  modalSaveBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 18px',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    border: 'none',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  timelineList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
    flex: 1,
    overflowY: 'auto',
    maxHeight: '340px',
    paddingRight: '6px',
  },
  timelineItem: {
    display: 'flex',
    gap: '10px',
    position: 'relative',
  },
  timelineMarker: {
    width: '10px',
    height: '10px',
    borderRadius: '50%',
    backgroundColor: '#2563eb',
    marginTop: '4px',
    flexShrink: 0,
  },
  timelineCard: {
    flex: 1,
    backgroundColor: '#f9fafb',
    padding: '8px 12px',
    borderRadius: '6px',
    border: '1px solid #e5e7eb',
  },
  timelineHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '4px',
  },
  timelineStageBadge: {
    fontSize: '11px',
    fontWeight: '700',
    color: '#1d4ed8',
  },
  timelineTimestamp: {
    fontSize: '10px',
    color: '#9ca3af',
  },
  timelineNotes: {
    fontSize: '12px',
    color: '#4b5563',
    margin: 0,
  },
  timelineEmpty: {
    fontSize: '13px',
    color: '#9ca3af',
    fontStyle: 'italic',
  },
  modalStageMoverBox: {
    marginTop: '16px',
    paddingTop: '16px',
    borderTop: '1px solid #e5e7eb',
  },
  modalStageButtons: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '6px',
    marginTop: '6px',
  },
  stageChoiceBtn: {
    padding: '6px 8px',
    fontSize: '11px',
    fontWeight: '600',
    borderRadius: '6px',
    border: '1px solid',
    cursor: 'pointer',
    textAlign: 'center',
    transition: 'all 0.15s ease',
  },
  modalActionRow: {
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
  modalBody: {
    padding: '24px',
    overflowY: 'auto',
  },
  cardStalledPill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '11px',
    fontWeight: '600',
    color: '#b45309',
    backgroundColor: '#fffbeb',
    border: '1px solid #fde68a',
    padding: '3px 8px',
    borderRadius: '12px',
    width: 'fit-content',
  },
  cardStaleLeadPill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '11px',
    fontWeight: '600',
    color: '#b91c1c',
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    padding: '3px 8px',
    borderRadius: '12px',
    width: 'fit-content',
  },
  cardFollowUpBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '5px',
    padding: '4px 8px',
    backgroundColor: '#f5f3ff',
    border: '1px solid #ddd6fe',
    borderRadius: '6px',
    color: '#6d28d9',
    fontSize: '11px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    width: '100%',
  },
  modalFollowUpBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 12px',
    backgroundColor: '#f5f3ff',
    border: '1px solid #ddd6fe',
    borderRadius: '6px',
    color: '#6d28d9',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  followUpModalContent: {
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
  followUpModalBody: {
    padding: '20px 24px 24px',
    overflowY: 'auto',
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  followUpStageTag: {
    fontSize: '11px',
    fontWeight: '700',
    padding: '2px 8px',
    borderRadius: '12px',
    backgroundColor: '#eff6ff',
    color: '#2563eb',
    border: '1px solid #bfdbfe',
  },
  followUpFieldGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  followUpActionsRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'flex-end',
    gap: '10px',
    marginTop: '6px',
    flexWrap: 'wrap',
  },
  logTimelineBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 14px',
    backgroundColor: '#059669',
    border: 'none',
    borderRadius: '8px',
    color: '#ffffff',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  draftLoadingBox: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '10px',
    padding: '36px 16px',
    backgroundColor: '#f9fafb',
    borderRadius: '8px',
    border: '1px solid #e5e7eb',
    color: '#6b7280',
    fontSize: '13px',
  },
  toneSelectorRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    flexWrap: 'wrap',
  },
  toneLabel: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#374151',
  },
  toneBtn: {
    padding: '6px 12px',
    borderRadius: '6px',
    border: '1px solid #d1d5db',
    backgroundColor: '#ffffff',
    fontSize: '12px',
    fontWeight: '500',
    color: '#4b5563',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  toneBtnActive: {
    backgroundColor: '#eff6ff',
    borderColor: '#2563eb',
    color: '#2563eb',
    fontWeight: '600',
  },
  recipientRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 10px',
    backgroundColor: '#f9fafb',
    borderRadius: '6px',
    border: '1px solid #e5e7eb',
    fontSize: '12px',
  },
  recipientLabel: {
    color: '#6b7280',
    fontWeight: '500',
  },
  recipientVal: {
    color: '#111827',
    fontWeight: '600',
  },
  consentNotice: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '8px',
    padding: '10px 14px',
    backgroundColor: '#ecfdf5',
    border: '1px solid #a7f3d0',
    borderRadius: '8px',
    fontSize: '12px',
    color: '#065f46',
    lineHeight: 1.4,
  },
  copyBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 14px',
    backgroundColor: '#ffffff',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '500',
    color: '#374151',
    cursor: 'pointer',
  },
  mailtoBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 14px',
    backgroundColor: '#2563eb',
    border: 'none',
    borderRadius: '8px',
    fontSize: '13px',
    fontWeight: '600',
    color: '#ffffff',
    textDecoration: 'none',
    cursor: 'pointer',
  },
};
