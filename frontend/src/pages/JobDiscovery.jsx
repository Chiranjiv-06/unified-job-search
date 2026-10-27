import React, { useState, useEffect, useCallback } from 'react';
import {
  getJobsApi,
  createJobApi,
  importJobUrlApi,
  matchJobApi,
  getRankedJobMatchesApi,
  verifyJobApi,
  getJobVerificationApi,
  trackJobApplyApi,
  syncJobSourcesApi
} from '../services/api';
import {
  Briefcase,
  Search,
  MapPin,
  Building2,
  ExternalLink,
  Plus,
  Globe,
  Layers,
  X,
  Loader2,
  IndianRupee,
  CheckCircle2,
  AlertCircle,
  Sparkles,
  Target,
  Lightbulb,
  AlertTriangle,
  Check,
  ShieldCheck,
  ShieldAlert,
  Shield,
  RotateCw,
  BookmarkCheck,
  ArrowUpDown,
  User
} from 'lucide-react';
import { Link } from 'react-router-dom';

export default function JobDiscovery() {
  const [jobs, setJobs] = useState([]);
  const [totalJobs, setTotalJobs] = useState(0);
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  // Tab state: 'all' vs 'ranked'
  const [activeTab, setActiveTab] = useState('all');
  const [rankedJobs, setRankedJobs] = useState([]);
  const [loadingRanked, setLoadingRanked] = useState(false);

  // Matching Modal state
  const [matchModalJob, setMatchModalJob] = useState(null);
  const [matchBreakdown, setMatchBreakdown] = useState(null);
  const [loadingMatch, setLoadingMatch] = useState(false);

  // Verification Signals Modal state
  const [verificationModalJob, setVerificationModalJob] = useState(null);
  const [verificationAudit, setVerificationAudit] = useState(null);
  const [loadingVerification, setLoadingVerification] = useState(false);
  const [runningLiveAudit, setRunningLiveAudit] = useState(false);

  // Application Pipeline Tracking state
  const [trackingJobId, setTrackingJobId] = useState(null);
  const [trackedJobIds, setTrackedJobIds] = useState(new Set());

  // Search & Filter state
  const [searchTerm, setSearchTerm] = useState('');
  const [locationFilter, setLocationFilter] = useState('');
  const [workModeFilter, setWorkModeFilter] = useState('Any');
  const [skillFilter, setSkillFilter] = useState('');
  const [sourceFilter, setSourceFilter] = useState('All');
  const [employmentTypeFilter, setEmploymentTypeFilter] = useState('All');
  const [sortBy, setSortBy] = useState('recent');
  const [hasProfileSkills, setHasProfileSkills] = useState(true);

  // Ingestion sync state
  const [syncingSources, setSyncingSources] = useState(false);

  // Modals state
  const [showAddModal, setShowAddModal] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [selectedJob, setSelectedJob] = useState(null);

  // Form states for manual job
  const [manualTitle, setManualTitle] = useState('');
  const [manualCompany, setManualCompany] = useState('');
  const [manualDesc, setManualDesc] = useState('');
  const [manualLocation, setManualLocation] = useState('');
  const [manualWorkMode, setManualWorkMode] = useState('Remote');
  const [manualExperienceLevel, setManualExperienceLevel] = useState('Entry-Level');
  const [manualExperienceYears, setManualExperienceYears] = useState('0');
  const [manualSalary, setManualSalary] = useState('');
  const [manualSkills, setManualSkills] = useState('');
  const [manualSourceUrl, setManualSourceUrl] = useState('');
  const [submittingManual, setSubmittingManual] = useState(false);

  // Form state for URL import
  const [importUrl, setImportUrl] = useState('');
  const [importingUrl, setImportingUrl] = useState(false);


  const fetchJobs = useCallback(async () => {
    setLoading(true);
    setErrorMsg(null);
    try {
      const params = {};
      if (searchTerm.trim()) params.q = searchTerm.trim();
      if (locationFilter.trim()) params.location = locationFilter.trim();
      if (workModeFilter && workModeFilter !== 'Any') params.work_mode = workModeFilter;
      if (skillFilter.trim()) params.skill = skillFilter.trim();
      if (sourceFilter && sourceFilter !== 'All') params.source = sourceFilter;
      if (employmentTypeFilter && employmentTypeFilter !== 'All') params.employment_type = employmentTypeFilter;
      if (sortBy) params.sort_by = sortBy;

      const data = await getJobsApi(params);
      setJobs(data.jobs || []);
      setTotalJobs(data.total || 0);
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to fetch job opportunities.');
    } finally {
      setLoading(false);
    }
  }, [searchTerm, locationFilter, workModeFilter, skillFilter, sourceFilter, employmentTypeFilter, sortBy]);

  const fetchRankedMatches = useCallback(async () => {
    setLoadingRanked(true);
    setErrorMsg(null);
    try {
      const params = {};
      if (searchTerm.trim()) params.q = searchTerm.trim();
      if (locationFilter.trim()) params.location = locationFilter.trim();
      if (workModeFilter && workModeFilter !== 'Any') params.work_mode = workModeFilter;
      if (skillFilter.trim()) params.skill = skillFilter.trim();
      if (sourceFilter && sourceFilter !== 'All') params.source = sourceFilter;
      if (employmentTypeFilter && employmentTypeFilter !== 'All') params.employment_type = employmentTypeFilter;

      const data = await getRankedJobMatchesApi(params);
      setRankedJobs(data.rankings || []);
      setHasProfileSkills(data.has_profile_skills !== false);
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to load ranked job matches.');
    } finally {
      setLoadingRanked(false);
    }
  }, [searchTerm, locationFilter, workModeFilter, skillFilter, sourceFilter, employmentTypeFilter]);

  useEffect(() => {
    const timer = setTimeout(() => {
      if (activeTab === 'all') {
        fetchJobs();
      } else {
        fetchRankedMatches();
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [activeTab, fetchJobs, fetchRankedMatches]);

  const handleCheckMatch = async (job) => {
    setMatchModalJob(job);
    setLoadingMatch(true);
    setMatchBreakdown(null);
    setErrorMsg(null);
    try {
      const data = await matchJobApi(job.id);
      setMatchBreakdown(data);
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to compute match breakdown.');
    } finally {
      setLoadingMatch(false);
    }
  };

  const handleTabChange = (tab) => {
    setActiveTab(tab);
    if (tab === 'ranked') {
      setSortBy('match');
    }
  };

  const handleCheckVerification = async (job) => {
    setVerificationModalJob(job);
    setLoadingVerification(true);
    setVerificationAudit(null);
    setErrorMsg(null);
    try {
      const data = await getJobVerificationApi(job.id);
      setVerificationAudit(data);
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to fetch verification audit signals.');
    } finally {
      setLoadingVerification(false);
    }
  };

  const handleReRunVerification = async (jobId) => {
    setRunningLiveAudit(true);
    setErrorMsg(null);
    try {
      const data = await verifyJobApi(jobId);
      setVerificationAudit(data);
      setSuccessMsg('Live verification audit refreshed!');
      setTimeout(() => setSuccessMsg(null), 3000);
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to re-run live verification audit.');
    } finally {
      setRunningLiveAudit(false);
    }
  };

  const handleTrackJob = async (job) => {
    setTrackingJobId(job.id);
    setErrorMsg(null);
    try {
      await trackJobApplyApi(job.id, {
        notes: `Tracked directly from Job Discovery (${job.source_platform || 'Portal'})`
      });
      setTrackedJobIds((prev) => new Set([...prev, job.id]));
      setSuccessMsg(`Added "${job.title}" at "${job.company_name}" to your Tracker pipeline!`);
      setTimeout(() => setSuccessMsg(null), 3500);
    } catch (err) {
      if (err.status === 409 || err.response?.status === 409) {
        setErrorMsg(`Already tracked: Active application already exists for ${job.company_name} - ${job.title}.`);
      } else {
        setErrorMsg(err.customMessage || 'Failed to track job application.');
      }
    } finally {
      setTrackingJobId(null);
    }
  };

  const handleManualSubmit = async (e) => {

    e.preventDefault();
    if (!manualTitle.trim() || !manualCompany.trim()) {
      setErrorMsg('Job title and company name are required.');
      return;
    }
    setSubmittingManual(true);
    setErrorMsg(null);

    const skillsArray = manualSkills
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);

    try {
      await createJobApi({
        title: manualTitle.trim(),
        company_name: manualCompany.trim(),
        description: manualDesc.trim() || null,
        location: manualLocation.trim() || null,
        work_mode: manualWorkMode,
        experience_level: manualExperienceLevel,
        experience_years_required: parseFloat(manualExperienceYears) || 0.0,
        salary_range: manualSalary.trim() || null,
        required_skills: skillsArray,
        source_url: manualSourceUrl.trim() || null,
        source_platform: 'Manual Entry'
      });

      setSuccessMsg('Job posting created successfully!');
      setTimeout(() => setSuccessMsg(null), 4000);
      setShowAddModal(false);
      // Reset form
      setManualTitle('');
      setManualCompany('');
      setManualDesc('');
      setManualLocation('');
      setManualSalary('');
      setManualSkills('');
      setManualSourceUrl('');
      fetchJobs();
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to create job posting.');
    } finally {
      setSubmittingManual(false);
    }
  };

  const handleImportSubmit = async (e) => {
    e.preventDefault();
    const url = importUrl.trim();
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      setErrorMsg('Please enter a valid URL starting with http:// or https://');
      return;
    }
    setImportingUrl(true);
    setErrorMsg(null);

    try {
      const imported = await importJobUrlApi({ url });
      setSuccessMsg(`Imported "${imported.title}" at ${imported.company_name}!`);
      setTimeout(() => setSuccessMsg(null), 4000);
      setShowImportModal(false);
      setImportUrl('');
      fetchJobs();
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to import job from URL.');
    } finally {
      setImportingUrl(false);
    }
  };

  const handleSyncSources = async () => {
    setSyncingSources(true);
    setErrorMsg(null);
    try {
      const res = await syncJobSourcesApi();
      setSuccessMsg(res.message || 'Job feeds synchronized successfully!');
      setTimeout(() => setSuccessMsg(null), 5000);
      fetchJobs();
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to synchronize external job sources.');
    } finally {
      setSyncingSources(false);
    }
  };

  const handleClearFilters = () => {
    setSearchTerm('');
    setLocationFilter('');
    setWorkModeFilter('Any');
    setSkillFilter('');
    setSourceFilter('All');
    setEmploymentTypeFilter('All');
    setSortBy('recent');
  };

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.pageHeader}>
        <div>
          <h1 style={styles.pageTitle}>Job Discovery & Records</h1>
          <p style={styles.pageSub}>
            Discover verified tech opportunities across RemoteOK, Jobicy, imported URLs, and manual records
          </p>
        </div>
        <div style={styles.headerActions}>
          <button
            onClick={handleSyncSources}
            disabled={syncingSources}
            style={{ ...styles.outlineBtn, borderColor: '#7c3aed', color: '#7c3aed' }}
            title="Fetch latest opportunities from RemoteOK and Jobicy"
          >
            <RotateCw size={16} className={syncingSources ? 'spin' : ''} />
            <span>{syncingSources ? 'Syncing Feeds...' : 'Sync Feeds'}</span>
          </button>
          <button
            onClick={() => setShowImportModal(true)}
            style={styles.outlineBtn}
          >
            <Globe size={16} />
            <span>Import from URL</span>
          </button>
          <button
            onClick={() => setShowAddModal(true)}
            style={styles.primaryBtn}
          >
            <Plus size={16} />
            <span>Add Job Manually</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {successMsg && (
        <div style={styles.successBanner}>
          <CheckCircle2 size={18} color="#059669" />
          <span>{successMsg}</span>
        </div>
      )}

      {errorMsg && (
        <div style={styles.errorBanner}>
          <AlertCircle size={18} color="#b91c1c" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Tab Switcher: All Jobs vs Ranked Matches */}
      <div style={styles.tabContainer}>
        <button
          type="button"
          onClick={() => handleTabChange('all')}
          style={activeTab === 'all' ? styles.tabActive : styles.tabInactive}
        >
          <Briefcase size={15} />
          <span>All Discovered Jobs ({totalJobs})</span>
        </button>
        <button
          type="button"
          onClick={() => handleTabChange('ranked')}
          style={activeTab === 'ranked' ? styles.tabActive : styles.tabInactive}
        >
          <Sparkles size={15} color={activeTab === 'ranked' ? '#2563eb' : '#7c3aed'} />
          <span>Ranked by Fit (Explainable Match)</span>
        </button>
      </div>

      {/* Profile Prompt Banner if profile skills missing */}
      {!hasProfileSkills && (
        <div style={styles.profilePromptBanner}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <User size={20} color="#b45309" />
            <div>
              <strong style={{ display: 'block', fontSize: '13px', color: '#92400e' }}>
                Candidate Profile Needs Skills / Target Roles
              </strong>
              <span style={{ fontSize: '12px', color: '#b45309' }}>
                Add your technical skills and role preferences to unlock personalized, explainable job fit rankings.
              </span>
            </div>
          </div>
          <Link to="/profile" style={styles.profilePromptLink}>
            Complete Profile &rarr;
          </Link>
        </div>
      )}

      {/* Search and Filters Bar */}
      <div style={styles.filterCard}>
        <div style={styles.searchRow}>
          <div style={styles.searchInputWrapper}>
            <Search size={18} color="#9ca3af" style={styles.searchIcon} />
            <input
              type="text"
              placeholder="Search by role, company name, or keywords (e.g. Python, SQL, React)..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={styles.searchInput}
            />
          </div>
        </div>

        <div style={styles.filterRow}>
          <div style={styles.filterGroup}>
            <MapPin size={15} color="#6b7280" />
            <input
              type="text"
              placeholder="Location (e.g. Bengaluru)"
              value={locationFilter}
              onChange={(e) => setLocationFilter(e.target.value)}
              style={styles.filterInput}
            />
          </div>

          <div style={styles.filterGroup}>
            <Layers size={15} color="#6b7280" />
            <input
              type="text"
              placeholder="Skill filter (e.g. Docker)"
              value={skillFilter}
              onChange={(e) => setSkillFilter(e.target.value)}
              style={styles.filterInput}
            />
          </div>

          <div style={styles.filterGroup}>
            <Globe size={15} color="#6b7280" />
            <select
              value={sourceFilter}
              onChange={(e) => setSourceFilter(e.target.value)}
              style={styles.filterSelect}
            >
              <option value="All">All Sources</option>
              <option value="RemoteOK">RemoteOK</option>
              <option value="Jobicy">Jobicy</option>
              <option value="Careers Portal">Imported URLs</option>
              <option value="Manual">Manual</option>
            </select>
          </div>

          <div style={styles.filterGroup}>
            <Briefcase size={15} color="#6b7280" />
            <select
              value={employmentTypeFilter}
              onChange={(e) => setEmploymentTypeFilter(e.target.value)}
              style={styles.filterSelect}
            >
              <option value="All">All Types</option>
              <option value="Full-time">Full-time</option>
              <option value="Contract">Contract</option>
              <option value="Part-time">Part-time</option>
              <option value="Internship">Internship</option>
            </select>
          </div>

          <div style={styles.filterGroup}>
            <Briefcase size={15} color="#6b7280" />
            <select
              value={workModeFilter}
              onChange={(e) => setWorkModeFilter(e.target.value)}
              style={styles.filterSelect}
            >
              <option value="Any">All Work Modes</option>
              <option value="Remote">Remote</option>
              <option value="Hybrid">Hybrid</option>
              <option value="On-site">On-site</option>
            </select>
          </div>

          <div style={styles.filterGroup}>
            <ArrowUpDown size={15} color="#6b7280" />
            <select
              value={activeTab === 'ranked' ? 'match' : sortBy}
              disabled={activeTab === 'ranked'}
              onChange={(e) => setSortBy(e.target.value)}
              style={styles.filterSelect}
              title={activeTab === 'ranked' ? 'Ranked tab automatically sorts by fit' : 'Sort opportunities'}
            >
              <option value="recent">Most Recent</option>
              <option value="match">Best Match (Relevance)</option>
            </select>
          </div>

          {(searchTerm || locationFilter || workModeFilter !== 'Any' || skillFilter || sourceFilter !== 'All' || employmentTypeFilter !== 'All' || sortBy !== 'recent') && (
            <button onClick={handleClearFilters} style={styles.clearBtn}>
              <X size={14} />
              <span>Clear</span>
            </button>
          )}
        </div>
      </div>

      {/* Results Header */}
      <div style={styles.resultsInfoRow}>
        <span style={styles.resultsCount}>
          {activeTab === 'all'
            ? `Showing ${jobs.length} of ${totalJobs} ${totalJobs === 1 ? 'Opportunity' : 'Opportunities'}`
            : `Showing ${rankedJobs.length} Opportunities Ranked by Match Score`}
        </span>
      </div>

      {/* Tab Content: All Jobs vs Ranked Jobs */}
      {activeTab === 'all' ? (
        loading ? (
          <div style={styles.loadingContainer}>
            <Loader2 size={32} className="spin" color="#2563eb" />
            <p>Loading job postings...</p>
          </div>
        ) : jobs.length === 0 ? (
          <div style={styles.emptyState}>
            <Briefcase size={44} color="#9ca3af" />
            <h3 style={styles.emptyTitle}>No matching job opportunities found</h3>
            <p style={styles.emptySub}>
              Try adjusting your search criteria, or add a new job manually or by URL.
            </p>
            <div style={{ marginTop: '16px', display: 'flex', gap: '10px' }}>
              <button onClick={() => setShowAddModal(true)} style={styles.primaryBtn}>
                <Plus size={16} />
                <span>Add Job</span>
              </button>
              <button onClick={() => setShowImportModal(true)} style={styles.outlineBtn}>
                <Globe size={16} />
                <span>Import URL</span>
              </button>
            </div>
          </div>
        ) : (
          <div style={styles.jobGrid}>
            {jobs.map((job) => (
              <div key={job.id} style={styles.jobCard}>
                <div style={styles.jobCardHeader}>
                  <div style={{ flex: 1, paddingRight: '8px' }}>
                    <h3 style={styles.jobTitle}>{job.title}</h3>
                    <div style={styles.companyRow}>
                      <Building2 size={15} color="#4b5563" />
                      <span style={styles.companyName}>{job.company_name}</span>
                      <span style={{
                        ...styles.platformBadge,
                        ...(job.source_platform?.toLowerCase().includes('remoteok')
                          ? { backgroundColor: '#f3e8ff', color: '#6b21a8', border: '1px solid #d8b4fe' }
                          : job.source_platform?.toLowerCase().includes('jobicy')
                          ? { backgroundColor: '#ecfdf5', color: '#047857', border: '1px solid #a7f3d0' }
                          : { backgroundColor: '#eff6ff', color: '#1d4ed8', border: '1px solid #bfdbfe' })
                      }}>
                        {job.source_platform || 'Portal'}
                      </span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {job.match_score !== null && job.match_score !== undefined && (
                      <div
                        style={{
                          ...styles.matchPill,
                          backgroundColor: job.match_score >= 75 ? '#ecfdf5' : job.match_score >= 50 ? '#fffbeb' : '#fef2f2',
                          borderColor: job.match_score >= 75 ? '#a7f3d0' : job.match_score >= 50 ? '#fde68a' : '#fecaca',
                          color: job.match_score >= 75 ? '#047857' : job.match_score >= 50 ? '#b45309' : '#b91c1c'
                        }}
                        title={job.match_summary || 'Relevance estimate'}
                      >
                        <Target size={13} />
                        <span>{Math.round(job.match_score)}% Match</span>
                      </div>
                    )}
                    {job.source_url && (
                      <a
                        href={job.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={styles.directLinkBtn}
                        title="Open original listing"
                      >
                        <ExternalLink size={15} />
                      </a>
                    )}
                  </div>
                </div>

                <div style={styles.metaRow}>
                  {job.location && (
                    <div style={styles.metaItem}>
                      <MapPin size={13} color="#6b7280" />
                      <span>{job.location}</span>
                    </div>
                  )}
                  {job.work_mode && (
                    <div style={styles.metaBadge}>
                      <span>{job.work_mode}</span>
                    </div>
                  )}
                  {job.employment_type && (
                    <div style={{ ...styles.metaBadge, backgroundColor: '#f0fdf4', color: '#15803d', border: '1px solid #bbf7d0' }}>
                      <span>{job.employment_type}</span>
                    </div>
                  )}
                  {job.is_expired && (
                    <div style={{ ...styles.metaBadge, backgroundColor: '#fef2f2', color: '#991b1b', border: '1px solid #fecaca' }}>
                      <span>Expired</span>
                    </div>
                  )}
                  {job.salary_range && (
                    <div style={styles.metaItem}>
                      <IndianRupee size={13} color="#059669" />
                      <span style={{ color: '#059669', fontWeight: '500' }}>{job.salary_range}</span>
                    </div>
                  )}
                  {job.experience_level && (
                    <div style={styles.metaItem}>
                      <Briefcase size={13} color="#6b7280" />
                      <span>{job.experience_level}</span>
                    </div>
                  )}
                </div>

                {job.description && (
                  <p style={styles.jobSnippet}>
                    {job.description.slice(0, 140)}...
                  </p>
                )}

                {/* Skills Tags */}
                {job.required_skills && job.required_skills.length > 0 && (
                  <div style={styles.skillsTagList}>
                    {job.required_skills.slice(0, 5).map((skill, sIdx) => (
                      <span key={sIdx} style={styles.skillTag}>
                        {skill}
                      </span>
                    ))}
                    {job.required_skills.length > 5 && (
                      <span style={styles.moreSkillsTag}>
                        +{job.required_skills.length - 5} more
                      </span>
                    )}
                  </div>
                )}

                <div style={styles.jobCardFooter}>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button
                      onClick={() => setSelectedJob(job)}
                      style={styles.detailsBtn}
                    >
                      View Details
                    </button>
                    <button
                      onClick={() => handleCheckMatch(job)}
                      style={styles.matchBtn}
                    >
                      <Sparkles size={13} color="#2563eb" />
                      <span>Check Match</span>
                    </button>
                    <button
                      onClick={() => handleCheckVerification(job)}
                      style={styles.verifyBtn}
                      title="Inspect legitimacy, DNS, MX, and scam signals"
                    >
                      <ShieldCheck size={13} color="#059669" />
                      <span>Verify Signals</span>
                    </button>
                    <button
                      onClick={() => handleTrackJob(job)}
                      disabled={trackingJobId === job.id || trackedJobIds.has(job.id)}
                      style={{
                        ...styles.trackBtn,
                        backgroundColor: trackedJobIds.has(job.id) ? '#ecfdf5' : '#eff6ff',
                        borderColor: trackedJobIds.has(job.id) ? '#a7f3d0' : '#bfdbfe',
                        color: trackedJobIds.has(job.id) ? '#059669' : '#2563eb',
                      }}
                      title="Track this job into your candidate pipeline"
                    >
                      {trackingJobId === job.id ? (
                        <Loader2 size={13} className="spin" />
                      ) : trackedJobIds.has(job.id) ? (
                        <Check size={13} />
                      ) : (
                        <BookmarkCheck size={13} />
                      )}
                      <span>{trackedJobIds.has(job.id) ? 'Tracked' : 'Track Application'}</span>
                    </button>
                  </div>
                  {job.source_url && (
                    <a
                      href={job.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={styles.externalLinkBtn}
                      title="Open original job link"
                    >
                      <span>Source</span>
                      <ExternalLink size={13} />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )
      ) : (
        /* Ranked Jobs Tab Content */
        loadingRanked ? (
          <div style={styles.loadingContainer}>
            <Loader2 size={32} className="spin" color="#2563eb" />
            <p>Evaluating active jobs against your verified candidate profile...</p>
          </div>
        ) : rankedJobs.length === 0 ? (
          <div style={styles.emptyState}>
            <Target size={44} color="#9ca3af" />
            <h3 style={styles.emptyTitle}>No ranked opportunities yet</h3>
            <p style={styles.emptySub}>
              {hasProfileSkills === false
                ? 'Your profile does not have technical skills configured yet. Add your skills to calculate relevance.'
                : 'No active job opportunities match your target roles and skills filter criteria.'}
            </p>
            <div style={{ marginTop: '16px' }}>
              <Link to="/profile" style={styles.primaryBtn}>
                <User size={16} />
                <span>Update Candidate Profile</span>
              </Link>
            </div>
          </div>
        ) : (
          <div style={styles.jobGrid}>
            {rankedJobs.map((item) => (
              <div key={item.job.id} style={styles.jobCard}>
                <div style={styles.jobCardHeader}>
                  <div>
                    <h3 style={styles.jobTitle}>{item.job.title}</h3>
                    <div style={styles.companyRow}>
                      <Building2 size={15} color="#4b5563" />
                      <span style={styles.companyName}>{item.job.company_name}</span>
                    </div>
                  </div>
                  <div style={{
                    ...styles.matchPill,
                    backgroundColor: item.match_score >= 75 ? '#ecfdf5' : item.match_score >= 50 ? '#fffbeb' : '#fef2f2',
                    borderColor: item.match_score >= 75 ? '#a7f3d0' : item.match_score >= 50 ? '#fde68a' : '#fecaca',
                    color: item.match_score >= 75 ? '#047857' : item.match_score >= 50 ? '#b45309' : '#b91c1c'
                  }}>
                    <Target size={13} />
                    <span>{item.match_score}% Match</span>
                  </div>
                </div>

                <div style={styles.metaRow}>
                  {item.job.location && (
                    <div style={styles.metaItem}>
                      <MapPin size={13} color="#6b7280" />
                      <span>{item.job.location}</span>
                    </div>
                  )}
                  {item.job.work_mode && (
                    <div style={styles.metaBadge}>
                      <span>{item.job.work_mode}</span>
                    </div>
                  )}
                  <div style={styles.metaItem}>
                    <CheckCircle2 size={13} color="#059669" />
                    <span>{item.matched_skills_count} Matched Skills</span>
                  </div>
                  {item.missing_critical_skills_count > 0 && (
                    <div style={styles.metaItem}>
                      <AlertCircle size={13} color="#b91c1c" />
                      <span>{item.missing_critical_skills_count} Missing</span>
                    </div>
                  )}
                </div>

                <p style={styles.quickSummaryText}>
                  {item.quick_summary}
                </p>

                {((item.positive_reasons && item.positive_reasons.length > 0) || (item.negative_reasons && item.negative_reasons.length > 0)) && (
                  <div style={{ margin: '8px 0', display: 'flex', flexDirection: 'column', gap: '3px' }}>
                    {item.positive_reasons?.slice(0, 2).map((pos, pIdx) => (
                      <span key={pIdx} style={{ fontSize: '11px', color: '#047857', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <Check size={11} strokeWidth={3} /> {pos}
                      </span>
                    ))}
                    {item.negative_reasons?.slice(0, 1).map((neg, nIdx) => (
                      <span key={nIdx} style={{ fontSize: '11px', color: '#b45309', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        <AlertTriangle size={11} /> {neg}
                      </span>
                    ))}
                  </div>
                )}

                <div style={styles.jobCardFooter}>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <button
                      onClick={() => setSelectedJob(item.job)}
                      style={styles.detailsBtn}
                    >
                      View Details
                    </button>
                    <button
                      onClick={() => handleCheckMatch(item.job)}
                      style={styles.matchBtnPrimary}
                    >
                      <Sparkles size={13} color="#ffffff" />
                      <span>Detailed Breakdown</span>
                    </button>
                    <button
                      onClick={() => handleCheckVerification(item.job)}
                      style={styles.verifyBtn}
                      title="Inspect legitimacy, DNS, MX, and scam signals"
                    >
                      <ShieldCheck size={13} color="#059669" />
                      <span>Verify Signals</span>
                    </button>
                    <button
                      onClick={() => handleTrackJob(item.job)}
                      disabled={trackingJobId === item.job.id || trackedJobIds.has(item.job.id)}
                      style={{
                        ...styles.trackBtn,
                        backgroundColor: trackedJobIds.has(item.job.id) ? '#ecfdf5' : '#eff6ff',
                        borderColor: trackedJobIds.has(item.job.id) ? '#a7f3d0' : '#bfdbfe',
                        color: trackedJobIds.has(item.job.id) ? '#059669' : '#2563eb',
                      }}
                      title="Track this job into your candidate pipeline"
                    >
                      {trackingJobId === item.job.id ? (
                        <Loader2 size={13} className="spin" />
                      ) : trackedJobIds.has(item.job.id) ? (
                        <Check size={13} />
                      ) : (
                        <BookmarkCheck size={13} />
                      )}
                      <span>{trackedJobIds.has(item.job.id) ? 'Tracked' : 'Track Application'}</span>
                    </button>
                  </div>
                  {item.job.source_url && (
                    <a
                      href={item.job.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={styles.externalLinkBtn}
                      title="Open original job link"
                    >
                      <span>Source</span>
                      <ExternalLink size={13} />
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )
      )}


      {/* Modal: Job Details */}
      {selectedJob && (
        <div style={styles.modalOverlay} onClick={() => setSelectedJob(null)}>
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div>
                <h2 style={styles.modalTitle}>{selectedJob.title}</h2>
                <p style={styles.modalSub}>{selectedJob.company_name}</p>
              </div>
              <button onClick={() => setSelectedJob(null)} style={styles.modalCloseBtn}>
                <X size={20} />
              </button>
            </div>

            <div style={styles.modalBody}>
              <div style={styles.modalMetaGrid}>
                <div>
                  <span style={styles.modalMetaLabel}>Location</span>
                  <span style={styles.modalMetaVal}>{selectedJob.location || 'Not Specified'}</span>
                </div>
                <div>
                  <span style={styles.modalMetaLabel}>Work Mode</span>
                  <span style={styles.modalMetaVal}>{selectedJob.work_mode || 'Any'}</span>
                </div>
                <div>
                  <span style={styles.modalMetaLabel}>Experience</span>
                  <span style={styles.modalMetaVal}>{selectedJob.experience_level || 'Entry-Level'} ({selectedJob.experience_years_required || 0} yrs)</span>
                </div>
                <div>
                  <span style={styles.modalMetaLabel}>Salary Range</span>
                  <span style={styles.modalMetaVal}>{selectedJob.salary_range || 'Not Disclosed'}</span>
                </div>
              </div>

              {selectedJob.required_skills && selectedJob.required_skills.length > 0 && (
                <div style={{ marginTop: '16px' }}>
                  <span style={styles.modalMetaLabel}>Required Technical Skills</span>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginTop: '6px' }}>
                    {selectedJob.required_skills.map((sk, i) => (
                      <span key={i} style={styles.skillTag}>
                        {sk}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {selectedJob.description && (
                <div style={{ marginTop: '20px' }}>
                  <span style={styles.modalMetaLabel}>Job Description</span>
                  <div style={styles.modalDescriptionText}>
                    {selectedJob.description}
                  </div>
                </div>
              )}

              {selectedJob && (
                <div style={{ marginTop: '20px', display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
                  <button
                    onClick={() => handleTrackJob(selectedJob)}
                    disabled={trackingJobId === selectedJob.id || trackedJobIds.has(selectedJob.id)}
                    style={{
                      ...styles.modalTrackBtn,
                      backgroundColor: trackedJobIds.has(selectedJob.id) ? '#ecfdf5' : '#2563eb',
                      color: trackedJobIds.has(selectedJob.id) ? '#059669' : '#ffffff',
                      borderColor: trackedJobIds.has(selectedJob.id) ? '#a7f3d0' : '#2563eb',
                    }}
                  >
                    {trackingJobId === selectedJob.id ? (
                      <Loader2 size={15} className="spin" />
                    ) : trackedJobIds.has(selectedJob.id) ? (
                      <Check size={15} />
                    ) : (
                      <BookmarkCheck size={15} />
                    )}
                    <span>{trackedJobIds.has(selectedJob.id) ? 'Application Tracked' : 'Track into Pipeline'}</span>
                  </button>

                  {selectedJob.source_url && (
                    <a
                      href={selectedJob.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={styles.applyExternalBtn}
                    >
                      <span>Visit Original Job Portal</span>
                      <ExternalLink size={15} />
                    </a>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Modal: Add Job Manually */}
      {showAddModal && (
        <div style={styles.modalOverlay} onClick={() => setShowAddModal(false)}>
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div>
                <h2 style={styles.modalTitle}>Add Job Opportunity</h2>
                <p style={styles.modalSub}>Enter role requirements and company details manually</p>
              </div>
              <button onClick={() => setShowAddModal(false)} style={styles.modalCloseBtn}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleManualSubmit} style={styles.modalBody}>
              <div style={styles.formRow}>
                <div style={styles.formField}>
                  <label style={styles.formLabel}>Job Title *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Backend Developer"
                    value={manualTitle}
                    onChange={(e) => setManualTitle(e.target.value)}
                    style={styles.formInput}
                  />
                </div>
                <div style={styles.formField}>
                  <label style={styles.formLabel}>Company Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Google, Infosys, TechCorp"
                    value={manualCompany}
                    onChange={(e) => setManualCompany(e.target.value)}
                    style={styles.formInput}
                  />
                </div>
              </div>

              <div style={styles.formRow}>
                <div style={styles.formField}>
                  <label style={styles.formLabel}>Location</label>
                  <input
                    type="text"
                    placeholder="e.g. Bengaluru, Pune, Remote"
                    value={manualLocation}
                    onChange={(e) => setManualLocation(e.target.value)}
                    style={styles.formInput}
                  />
                </div>
                <div style={styles.formField}>
                  <label style={styles.formLabel}>Work Mode</label>
                  <select
                    value={manualWorkMode}
                    onChange={(e) => setManualWorkMode(e.target.value)}
                    style={styles.formInput}
                  >
                    <option value="Remote">Remote</option>
                    <option value="Hybrid">Hybrid</option>
                    <option value="On-site">On-site</option>
                    <option value="Any">Any</option>
                  </select>
                </div>
              </div>

              <div style={styles.formRow}>
                <div style={styles.formField}>
                  <label style={styles.formLabel}>Experience Level</label>
                  <select
                    value={manualExperienceLevel}
                    onChange={(e) => setManualExperienceLevel(e.target.value)}
                    style={styles.formInput}
                  >
                    <option value="Intern">Intern</option>
                    <option value="Entry-Level">Entry-Level (0-2 yrs)</option>
                    <option value="Mid-Level">Mid-Level (2-5 yrs)</option>
                    <option value="Senior">Senior (5+ yrs)</option>
                  </select>
                </div>
                <div style={styles.formField}>
                  <label style={styles.formLabel}>Min Experience (Years)</label>
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    value={manualExperienceYears}
                    onChange={(e) => setManualExperienceYears(e.target.value)}
                    style={styles.formInput}
                  />
                </div>
                <div style={styles.formField}>
                  <label style={styles.formLabel}>Salary Range (optional)</label>
                  <input
                    type="text"
                    placeholder="e.g. 8 - 12 LPA"
                    value={manualSalary}
                    onChange={(e) => setManualSalary(e.target.value)}
                    style={styles.formInput}
                  />
                </div>
              </div>


              <div style={styles.formField}>
                <label style={styles.formLabel}>Required Skills (comma-separated)</label>
                <input
                  type="text"
                  placeholder="e.g. Python, FastAPI, Docker, PostgreSQL"
                  value={manualSkills}
                  onChange={(e) => setManualSkills(e.target.value)}
                  style={styles.formInput}
                />
              </div>

              <div style={styles.formField}>
                <label style={styles.formLabel}>Job Description</label>
                <textarea
                  rows={4}
                  placeholder="Paste job description, responsibilities, or eligibility..."
                  value={manualDesc}
                  onChange={(e) => setManualDesc(e.target.value)}
                  style={styles.formTextarea}
                />
              </div>

              <div style={styles.formField}>
                <label style={styles.formLabel}>Original Source URL</label>
                <input
                  type="url"
                  placeholder="https://company.com/careers/job-123"
                  value={manualSourceUrl}
                  onChange={(e) => setManualSourceUrl(e.target.value)}
                  style={styles.formInput}
                />
              </div>

              <div style={styles.modalFooter}>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  style={styles.outlineBtn}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingManual}
                  style={styles.primaryBtn}
                >
                  {submittingManual ? <Loader2 size={16} className="spin" /> : <Plus size={16} />}
                  <span>Save Job</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Import from URL */}
      {showImportModal && (
        <div style={styles.modalOverlay} onClick={() => setShowImportModal(false)}>
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div>
                <h2 style={styles.modalTitle}>Import Job from URL</h2>
                <p style={styles.modalSub}>
                  Paste any job posting or careers page link. We will extract metadata and tech skills.
                </p>
              </div>
              <button onClick={() => setShowImportModal(false)} style={styles.modalCloseBtn}>
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleImportSubmit} style={styles.modalBody}>
              <div style={styles.formField}>
                <label style={styles.formLabel}>Job Posting URL *</label>
                <input
                  type="url"
                  required
                  placeholder="https://example.com/careers/software-engineer"
                  value={importUrl}
                  onChange={(e) => setImportUrl(e.target.value)}
                  style={styles.formInput}
                />
                <span style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>
                  Supports Schema.org JobPosting, career sites, and public job portals.
                </span>
              </div>

              <div style={styles.modalFooter}>
                <button
                  type="button"
                  onClick={() => setShowImportModal(false)}
                  style={styles.outlineBtn}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={importingUrl}
                  style={styles.primaryBtn}
                >
                  {importingUrl ? (
                    <>
                      <Loader2 size={16} className="spin" />
                      <span>Parsing URL...</span>
                    </>
                  ) : (
                    <>
                      <Globe size={16} />
                      <span>Extract & Save</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal / Drawer: Explainable Match Breakdown */}
      {matchModalJob && (
        <div style={styles.modalOverlay} onClick={() => setMatchModalJob(null)}>
          <div
            style={{ ...styles.modalContent, maxWidth: '680px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={styles.modalHeader}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <Sparkles size={18} color="#2563eb" />
                  <span style={{ fontSize: '12px', fontWeight: '700', color: '#2563eb', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Explainable Fit Breakdown
                  </span>
                </div>
                <h2 style={styles.modalTitle}>{matchModalJob.title}</h2>
                <p style={styles.modalSub}>{matchModalJob.company_name}</p>
              </div>
              <button onClick={() => setMatchModalJob(null)} style={styles.modalCloseBtn}>
                <X size={20} />
              </button>
            </div>

            <div style={styles.modalBody}>
              {loadingMatch ? (
                <div style={styles.loadingContainer}>
                  <Loader2 size={32} className="spin" color="#2563eb" />
                  <p style={{ marginTop: '12px', color: '#4b5563', fontSize: '14px' }}>
                    Analyzing job criteria against your verified profile...
                  </p>
                </div>
              ) : matchBreakdown ? (
                <div>
                  {/* Score Meter & Weighted Breakdown */}
                  <div style={styles.meterCard}>
                    <div style={styles.meterHeader}>
                      <div>
                        <span style={styles.meterLabel}>Overall Match Score</span>
                        <div style={styles.scoreRow}>
                          <span
                            style={{
                              ...styles.meterScore,
                              color:
                                matchBreakdown.match_score >= 75
                                  ? '#059669'
                                  : matchBreakdown.match_score >= 50
                                  ? '#d97706'
                                  : '#dc2626'
                            }}
                          >
                            {matchBreakdown.match_score}%
                          </span>
                          <span style={styles.scoreTierBadge}>
                            {matchBreakdown.match_score >= 75
                              ? 'Strong Alignment'
                              : matchBreakdown.match_score >= 50
                              ? 'Moderate Alignment'
                              : 'Low Alignment'}
                          </span>
                        </div>
                      </div>

                      <div style={styles.weightPills}>
                        <div style={styles.weightPillItem}>
                          <span style={styles.weightVal}>{matchBreakdown.core_skills_score ?? 0}%</span>
                          <span style={styles.weightKey}>Core (50%)</span>
                        </div>
                        <div style={styles.weightPillItem}>
                          <span style={styles.weightVal}>{matchBreakdown.preferred_skills_score ?? 0}%</span>
                          <span style={styles.weightKey}>Preferred (15%)</span>
                        </div>
                        <div style={styles.weightPillItem}>
                          <span style={styles.weightVal}>{matchBreakdown.role_score ?? 0}%</span>
                          <span style={styles.weightKey}>Role (20%)</span>
                        </div>
                        <div style={styles.weightPillItem}>
                          <span style={styles.weightVal}>{matchBreakdown.experience_score ?? 0}%</span>
                          <span style={styles.weightKey}>Exp (15%)</span>
                        </div>
                      </div>
                    </div>

                    {/* Visual Progress Bar */}
                    <div style={styles.progressBarBg}>
                      <div
                        style={{
                          ...styles.progressBarFill,
                          width: `${Math.min(100, Math.max(0, matchBreakdown.match_score))}%`,
                          backgroundColor:
                            matchBreakdown.match_score >= 75
                              ? '#10b981'
                              : matchBreakdown.match_score >= 50
                              ? '#f59e0b'
                              : '#ef4444'
                        }}
                      />
                    </div>

                    {/* Human readable explanation */}
                    <div style={styles.explanationText}>
                      <Lightbulb size={16} color="#4b5563" style={{ flexShrink: 0, marginTop: '2px' }} />
                      <span>{matchBreakdown.explanation}</span>
                    </div>

                    {/* Positive Compatibility Factors */}
                    {matchBreakdown.positive_reasons && matchBreakdown.positive_reasons.length > 0 && (
                      <div style={{ marginTop: '12px', padding: '10px 14px', backgroundColor: '#f0fdf4', borderRadius: '8px', border: '1px solid #bbf7d0' }}>
                        <span style={{ fontSize: '12px', fontWeight: '700', color: '#166534', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <CheckCircle2 size={14} color="#16a34a" /> Positive Compatibility Factors:
                        </span>
                        <ul style={{ margin: '6px 0 0 16px', padding: 0, fontSize: '12px', color: '#15803d', lineHeight: '1.4' }}>
                          {matchBreakdown.positive_reasons.map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Mismatch & Uncertainty Factors */}
                    {matchBreakdown.negative_reasons && matchBreakdown.negative_reasons.length > 0 && (
                      <div style={{ marginTop: '8px', padding: '10px 14px', backgroundColor: '#fffbeb', borderRadius: '8px', border: '1px solid #fde68a' }}>
                        <span style={{ fontSize: '12px', fontWeight: '700', color: '#92400e', display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <AlertTriangle size={14} color="#d97706" /> Potential Mismatches & Uncertainty:
                        </span>
                        <ul style={{ margin: '6px 0 0 16px', padding: 0, fontSize: '12px', color: '#b45309', lineHeight: '1.4' }}>
                          {matchBreakdown.negative_reasons.map((r, i) => (
                            <li key={i}>{r}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>

                  {/* Experience Gap Warning / Eligibility Status */}
                  {matchBreakdown.experience_status === 'GAP_WARNING' && (
                    <div style={styles.expWarningAlert}>
                      <AlertTriangle size={18} color="#b45309" style={{ flexShrink: 0 }} />
                      <div>
                        <strong style={{ display: 'block', fontSize: '13px', color: '#92400e' }}>
                          Experience Gap Warning
                        </strong>
                        <span style={{ fontSize: '12px', color: '#b45309' }}>
                          Role requires {matchBreakdown.required_experience_years} years. Your verified experience is {matchBreakdown.candidate_experience_years} {matchBreakdown.candidate_experience_years === 1 ? 'year' : 'years'} (gap of {matchBreakdown.experience_gap_years} {matchBreakdown.experience_gap_years === 1 ? 'year' : 'years'}).
                        </span>
                      </div>
                    </div>
                  )}

                  {matchBreakdown.experience_status === 'ELIGIBLE' && (
                    <div style={styles.expSuccessAlert}>
                      <CheckCircle2 size={18} color="#059669" style={{ flexShrink: 0 }} />
                      <div>
                        <strong style={{ display: 'block', fontSize: '13px', color: '#065f46' }}>
                          Experience Requirement Met
                        </strong>
                        <span style={{ fontSize: '12px', color: '#047857' }}>
                          Your verified experience ({matchBreakdown.candidate_experience_years} yrs) satisfies or exceeds the required {matchBreakdown.required_experience_years} yrs.
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Skills Delta Breakdown */}
                  <div style={styles.sectionCard}>
                    <h4 style={styles.sectionCardTitle}>
                      <Target size={15} color="#2563eb" />
                      <span>Skills Delta Breakdown</span>
                    </h4>

                    {/* Matched Skills */}
                    <div style={{ marginBottom: '14px' }}>
                      <div style={styles.skillGroupHeader}>
                        <span style={styles.skillGroupLabelSuccess}>
                          Matched Skills ({matchBreakdown.matched_skills.length})
                        </span>
                      </div>
                      {matchBreakdown.matched_skills.length === 0 ? (
                        <span style={styles.emptySkillsNotice}>No overlapping skills found.</span>
                      ) : (
                        <div style={styles.chipsContainer}>
                          {matchBreakdown.matched_skills.map((skill, idx) => (
                            <span key={idx} style={styles.matchedChip}>
                              <Check size={12} strokeWidth={3} />
                              <span>{skill}</span>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Missing Critical Skills */}
                    <div style={{ marginBottom: '14px' }}>
                      <div style={styles.skillGroupHeader}>
                        <span style={styles.skillGroupLabelCritical}>
                          Missing Critical Skills ({matchBreakdown.missing_critical_skills.length})
                        </span>
                      </div>
                      {matchBreakdown.missing_critical_skills.length === 0 ? (
                        <span style={styles.allSkillsMetNotice}>All required skills present in your profile!</span>
                      ) : (
                        <div style={styles.chipsContainer}>
                          {matchBreakdown.missing_critical_skills.map((skill, idx) => (
                            <span key={idx} style={styles.missingCriticalChip}>
                              <AlertCircle size={12} />
                              <span>{skill}</span>
                            </span>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Missing Secondary Skills */}
                    {matchBreakdown.missing_secondary_skills.length > 0 && (
                      <div>
                        <div style={styles.skillGroupHeader}>
                          <span style={styles.skillGroupLabelSecondary}>
                            Missing Secondary / Preferred ({matchBreakdown.missing_secondary_skills.length})
                          </span>
                        </div>
                        <div style={styles.chipsContainer}>
                          {matchBreakdown.missing_secondary_skills.map((skill, idx) => (
                            <span key={idx} style={styles.missingSecondaryChip}>
                              <span>{skill}</span>
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Truthful Resume Advice */}
                  {matchBreakdown.resume_advice && matchBreakdown.resume_advice.length > 0 && (
                    <div style={styles.adviceCard}>
                      <div style={styles.adviceCardHeader}>
                        <Sparkles size={16} color="#7c3aed" />
                        <h4 style={styles.adviceCardTitle}>Truthful Resume Alignment Tips</h4>
                      </div>
                      <p style={styles.adviceDisclaimer}>
                        Suggestions based strictly on verified profile overlaps (never fabricated):
                      </p>
                      <ul style={styles.adviceList}>
                        {matchBreakdown.resume_advice.map((tip, idx) => (
                          <li key={idx} style={styles.adviceListItem}>
                            {tip}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Deterministic Rule-Based Fit Disclaimer */}
                  <div style={styles.ruleBasedDisclaimer}>
                    <Shield size={16} color="#6b7280" style={{ flexShrink: 0, marginTop: '2px' }} />
                    <span>
                      <strong>Deterministic Rule-Based Fit:</strong> Scores are calculated using verified candidate profile data (skills, role preferences, education, and experience) compared against extracted job requirements. Scores do not guarantee interview shortlisting, eligibility, or employer selection.
                    </span>
                  </div>
                </div>
              ) : (
                <div style={styles.emptyState}>
                  <p>No breakdown data available.</p>
                </div>
              )}
            </div>

            <div style={styles.modalFooter}>
              <button
                type="button"
                onClick={() => setMatchModalJob(null)}
                style={styles.primaryBtn}
              >
                Close Breakdown
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Job & Company Verification Evidence Audit */}
      {verificationModalJob && (
        <div style={styles.modalOverlay} onClick={() => setVerificationModalJob(null)}>
          <div
            style={{ ...styles.modalContent, maxWidth: '720px' }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={styles.modalHeader}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                  <ShieldCheck size={18} color="#059669" />
                  <span style={{ fontSize: '12px', fontWeight: '700', color: '#059669', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Job Legitimacy & Verification Audit
                  </span>
                </div>
                <h2 style={styles.modalTitle}>{verificationModalJob.title}</h2>
                <p style={styles.modalSub}>{verificationModalJob.company_name}</p>
              </div>
              <button onClick={() => setVerificationModalJob(null)} style={styles.modalCloseBtn}>
                <X size={20} />
              </button>
            </div>

            <div style={styles.modalBody}>
              {loadingVerification ? (
                <div style={styles.loadingContainer}>
                  <Loader2 size={32} className="spin" color="#059669" />
                  <p style={{ marginTop: '12px', color: '#4b5563', fontSize: '14px' }}>
                    Auditing domain records, DNS MX mail servers, ATS hosts, and scam heuristics...
                  </p>
                </div>
              ) : verificationAudit ? (
                <div>
                  {/* Risk Score & Evidence Banner */}
                  <div style={styles.meterCard}>
                    <div style={styles.meterHeader}>
                      <div>
                        <span style={styles.meterLabel}>Legitimacy & Scam Risk Score</span>
                        <div style={styles.scoreRow}>
                          <span
                            style={{
                              ...styles.meterScore,
                              color:
                                verificationAudit.risk_level === 'LOW_RISK'
                                  ? '#059669'
                                  : verificationAudit.risk_level === 'CAUTION'
                                  ? '#d97706'
                                  : '#dc2626'
                            }}
                          >
                            {verificationAudit.risk_score}% Risk
                          </span>
                          <span
                            style={{
                              ...styles.scoreTierBadge,
                              backgroundColor:
                                verificationAudit.risk_level === 'LOW_RISK'
                                  ? '#ecfdf5'
                                  : verificationAudit.risk_level === 'CAUTION'
                                  ? '#fffbeb'
                                  : '#fef2f2',
                              color:
                                verificationAudit.risk_level === 'LOW_RISK'
                                  ? '#047857'
                                  : verificationAudit.risk_level === 'CAUTION'
                                  ? '#b45309'
                                  : '#b91c1c',
                              borderColor:
                                verificationAudit.risk_level === 'LOW_RISK'
                                  ? '#a7f3d0'
                                  : verificationAudit.risk_level === 'CAUTION'
                                  ? '#fde68a'
                                  : '#fecaca'
                            }}
                          >
                            {verificationAudit.risk_level === 'LOW_RISK'
                              ? '✓ Low Risk (Verified Signals)'
                              : verificationAudit.risk_level === 'CAUTION'
                              ? '⚠️ Caution (Partial Signals)'
                              : verificationAudit.risk_level === 'HIGH_RISK'
                              ? '⚠️ High Risk Warning'
                              : '🚨 Critical Scam Warning'}
                          </span>
                        </div>
                      </div>

                      <div style={{ textAlign: 'right' }}>
                        <span style={{ fontSize: '11px', color: '#6b7280', display: 'block' }}>Audited At</span>
                        <span style={{ fontSize: '12px', fontWeight: '600', color: '#374151' }}>
                          {new Date(verificationAudit.checked_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    </div>

                    {/* Risk Bar (lower is safer) */}
                    <div style={styles.progressBarBg}>
                      <div
                        style={{
                          ...styles.progressBarFill,
                          width: `${Math.min(100, Math.max(5, verificationAudit.risk_score))}%`,
                          backgroundColor:
                            verificationAudit.risk_level === 'LOW_RISK'
                              ? '#10b981'
                              : verificationAudit.risk_level === 'CAUTION'
                              ? '#f59e0b'
                              : '#ef4444'
                        }}
                      />
                    </div>

                    <div style={styles.explanationText}>
                      <Lightbulb size={16} color="#4b5563" style={{ flexShrink: 0, marginTop: '2px' }} />
                      <span>{verificationAudit.evidence_summary}</span>
                    </div>
                  </div>

                  {/* Red Flag Scam Warning Banner */}
                  {verificationAudit.scam_flags && verificationAudit.scam_flags.length > 0 && (
                    <div style={styles.scamFlagsAlertBox}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                        <AlertTriangle size={18} color="#b91c1c" />
                        <strong style={{ fontSize: '13px', color: '#991b1b' }}>
                          Scam & Phishing Flags Detected ({verificationAudit.scam_flags.length})
                        </strong>
                      </div>
                      <ul style={styles.scamFlagsList}>
                        {verificationAudit.scam_flags.map((flag, idx) => (
                          <li key={idx} style={styles.scamFlagsListItem}>
                            {flag}
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* 4-Point Technical Verification Grid */}
                  <div style={styles.verificationGrid}>
                    <div style={styles.verifyMetricCard}>
                      <div style={styles.verifyMetricHeader}>
                        <span style={styles.verifyMetricTitle}>Domain & DNS</span>
                        {verificationAudit.domain_valid ? (
                          <CheckCircle2 size={16} color="#059669" />
                        ) : (
                          <AlertCircle size={16} color="#dc2626" />
                        )}
                      </div>
                      <span style={styles.verifyMetricVal}>
                        {verificationAudit.domain || 'Not Specified'}
                      </span>
                      <span style={styles.verifyMetricSub}>
                        {verificationAudit.domain_valid ? 'DNS Host Verified' : 'Unresolved / Missing'}
                      </span>
                    </div>

                    <div style={styles.verifyMetricCard}>
                      <div style={styles.verifyMetricHeader}>
                        <span style={styles.verifyMetricTitle}>Corporate MX Records</span>
                        {verificationAudit.mx_records_found ? (
                          <CheckCircle2 size={16} color="#059669" />
                        ) : (
                          <AlertCircle size={16} color="#f59e0b" />
                        )}
                      </div>
                      <span style={styles.verifyMetricVal}>
                        {verificationAudit.mx_records_found ? 'Active Mail Server' : 'No MX Records'}
                      </span>
                      <span style={styles.verifyMetricSub}>
                        {verificationAudit.mx_records_found ? 'Corporate email configured' : 'Unconfirmed mail routing'}
                      </span>
                    </div>

                    <div style={styles.verifyMetricCard}>
                      <div style={styles.verifyMetricHeader}>
                        <span style={styles.verifyMetricTitle}>Official Career Site / ATS</span>
                        {verificationAudit.official_posting_matched ? (
                          <CheckCircle2 size={16} color="#059669" />
                        ) : (
                          <AlertCircle size={16} color="#6b7280" />
                        )}
                      </div>
                      <span style={styles.verifyMetricVal}>
                        {verificationAudit.official_posting_matched ? 'Corroborated Host' : 'External / Unmatched'}
                      </span>
                      <span style={styles.verifyMetricSub}>
                        {verificationAudit.details?.job_host || 'Direct Link Unchecked'}
                      </span>
                    </div>

                    <div style={styles.verifyMetricCard}>
                      <div style={styles.verifyMetricHeader}>
                        <span style={styles.verifyMetricTitle}>Employer Status</span>
                        {verificationAudit.is_verified ? (
                          <ShieldCheck size={16} color="#059669" />
                        ) : (
                          <ShieldAlert size={16} color="#dc2626" />
                        )}
                      </div>
                      <span style={styles.verifyMetricVal}>
                        {verificationAudit.is_verified ? 'Verified Employer' : 'Unverified Listing'}
                      </span>
                      <span style={styles.verifyMetricSub}>
                        {verificationAudit.details?.flags_count === 0 ? 'Zero scam flags' : `${verificationAudit.details?.flags_count} flags detected`}
                      </span>
                    </div>
                  </div>

                  {/* Evidence Points Audit Trail */}
                  {verificationAudit.evidence_points && verificationAudit.evidence_points.length > 0 && (
                    <div style={styles.sectionCard}>
                      <h4 style={styles.sectionCardTitle}>
                        <Layers size={15} color="#059669" />
                        <span>Evidence Audit Trail</span>
                      </h4>
                      <div style={styles.evidencePointsContainer}>
                        {verificationAudit.evidence_points.map((pt, idx) => (
                          <div
                            key={idx}
                            style={{
                              ...styles.evidencePointRow,
                              backgroundColor:
                                pt.includes('CRITICAL') || pt.includes('🚨')
                                  ? '#fef2f2'
                                  : pt.includes('WARNING') || pt.includes('⚠️')
                                  ? '#fffbeb'
                                  : pt.includes('✓')
                                  ? '#f0fdf4'
                                  : '#f9fafb',
                              borderColor:
                                pt.includes('CRITICAL') || pt.includes('🚨')
                                  ? '#fecaca'
                                  : pt.includes('WARNING') || pt.includes('⚠️')
                                  ? '#fde68a'
                                  : pt.includes('✓')
                                  ? '#bbf7d0'
                                  : '#e5e7eb'
                            }}
                          >
                            <span style={{ fontSize: '13px', lineHeight: 1.5, color: '#1f2937' }}>
                              {pt}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Safety Guidance */}
                  <div style={styles.safetyNoticeBox}>
                    <Shield size={16} color="#047857" style={{ flexShrink: 0, marginTop: '2px' }} />
                    <p style={{ margin: 0, fontSize: '12px', color: '#065f46', lineHeight: 1.5 }}>
                      <strong>Candidate Safety Reminder:</strong> Legitimate corporate employers will never ask for payment, security deposits, or purchase of equipment. Always ensure official communications come from verified corporate email addresses.
                    </p>
                  </div>
                </div>
              ) : (
                <div style={styles.emptyState}>
                  <p>No verification evidence available.</p>
                </div>
              )}
            </div>

            <div style={styles.modalFooter}>
              <button
                type="button"
                onClick={() => handleReRunVerification(verificationModalJob.id)}
                disabled={runningLiveAudit}
                style={styles.outlineBtn}
              >
                {runningLiveAudit ? <Loader2 size={14} className="spin" /> : <RotateCw size={14} />}
                <span>{runningLiveAudit ? 'Re-auditing...' : 'Re-run Live Audit'}</span>
              </button>
              <button
                type="button"
                onClick={() => setVerificationModalJob(null)}
                style={styles.primaryBtn}
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
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
  pageHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '24px',
    flexWrap: 'wrap',
    gap: '16px',
  },
  pageTitle: {
    fontSize: '24px',
    fontWeight: '700',
    color: '#111827',
    margin: '0 0 6px 0',
  },
  pageSub: {
    fontSize: '14px',
    color: '#6b7280',
    margin: 0,
  },
  headerActions: {
    display: 'flex',
    gap: '10px',
    alignItems: 'center',
  },
  primaryBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 18px',
    borderRadius: '8px',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    fontSize: '13px',
    fontWeight: '600',
    border: 'none',
    cursor: 'pointer',
    boxShadow: '0 1px 3px rgba(37, 99, 235, 0.2)',
  },
  outlineBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '9px 16px',
    borderRadius: '8px',
    backgroundColor: '#ffffff',
    color: '#374151',
    fontSize: '13px',
    fontWeight: '500',
    border: '1px solid #d1d5db',
    cursor: 'pointer',
  },
  successBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px 16px',
    backgroundColor: '#ecfdf5',
    border: '1px solid #a7f3d0',
    borderRadius: '8px',
    color: '#065f46',
    fontSize: '13px',
    marginBottom: '20px',
  },
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px 16px',
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '8px',
    color: '#991b1b',
    fontSize: '13px',
    marginBottom: '20px',
  },
  filterCard: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    border: '1px solid #e5e7eb',
    padding: '16px',
    marginBottom: '20px',
    boxShadow: '0 1px 2px rgba(0,0,0,0.03)',
  },
  searchRow: {
    marginBottom: '12px',
  },
  searchInputWrapper: {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
  },
  searchIcon: {
    position: 'absolute',
    left: '12px',
  },
  searchInput: {
    width: '100%',
    padding: '12px 12px 12px 40px',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    fontSize: '14px',
    outline: 'none',
    boxSizing: 'border-box',
  },
  filterRow: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
    flexWrap: 'wrap',
  },
  filterGroup: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    backgroundColor: '#f9fafb',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    padding: '6px 12px',
    flex: '1 1 180px',
  },
  filterInput: {
    border: 'none',
    backgroundColor: 'transparent',
    outline: 'none',
    fontSize: '13px',
    width: '100%',
  },
  filterSelect: {
    border: 'none',
    backgroundColor: 'transparent',
    outline: 'none',
    fontSize: '13px',
    width: '100%',
    cursor: 'pointer',
  },
  clearBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '8px 12px',
    borderRadius: '6px',
    border: 'none',
    backgroundColor: '#f3f4f6',
    color: '#4b5563',
    fontSize: '12px',
    fontWeight: '500',
    cursor: 'pointer',
  },
  resultsInfoRow: {
    marginBottom: '16px',
  },
  resultsCount: {
    fontSize: '13px',
    color: '#6b7280',
    fontWeight: '500',
  },
  loadingContainer: {
    minHeight: '260px',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '12px',
    color: '#6b7280',
  },
  emptyState: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    border: '1px dashed #d1d5db',
    padding: '48px 24px',
    textAlign: 'center',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  emptyTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#374151',
    margin: '12px 0 6px 0',
  },
  emptySub: {
    fontSize: '13px',
    color: '#6b7280',
    margin: 0,
    maxWidth: '420px',
  },
  jobGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))',
    gap: '20px',
  },
  jobCard: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    border: '1px solid #e5e7eb',
    padding: '20px',
    boxShadow: '0 1px 3px rgba(0,0,0,0.03)',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'space-between',
    transition: 'transform 0.15s ease, box-shadow 0.15s ease',
  },
  jobCardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '10px',
  },
  jobTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#111827',
    margin: '0 0 4px 0',
  },
  companyRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
  },
  companyName: {
    fontSize: '13px',
    fontWeight: '500',
    color: '#4b5563',
  },
  platformBadge: {
    fontSize: '11px',
    fontWeight: '500',
    padding: '2px 8px',
    borderRadius: '12px',
    backgroundColor: '#f3f4f6',
    color: '#4b5563',
  },
  directLinkBtn: {
    color: '#6b7280',
    padding: '6px',
    borderRadius: '6px',
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    textDecoration: 'none',
    border: '1px solid #e5e7eb',
    backgroundColor: '#f9fafb',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  metaRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
    alignItems: 'center',
    margin: '10px 0',
  },
  metaItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    fontSize: '12px',
    color: '#6b7280',
  },
  metaBadge: {
    fontSize: '11px',
    fontWeight: '600',
    padding: '2px 8px',
    borderRadius: '4px',
    backgroundColor: '#eff6ff',
    color: '#1d4ed8',
  },
  jobSnippet: {
    fontSize: '13px',
    color: '#4b5563',
    lineHeight: 1.4,
    margin: '8px 0',
  },
  skillsTagList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
    margin: '12px 0',
  },
  skillTag: {
    fontSize: '11px',
    fontWeight: '500',
    padding: '4px 8px',
    borderRadius: '6px',
    backgroundColor: '#f1f5f9',
    color: '#334155',
  },
  moreSkillsTag: {
    fontSize: '11px',
    fontWeight: '500',
    padding: '4px 8px',
    borderRadius: '6px',
    backgroundColor: '#f8fafc',
    color: '#64748b',
  },
  jobCardFooter: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTop: '1px solid #f3f4f6',
    paddingTop: '12px',
    marginTop: '12px',
  },
  detailsBtn: {
    padding: '6px 14px',
    borderRadius: '6px',
    border: '1px solid #d1d5db',
    backgroundColor: '#ffffff',
    color: '#1f2937',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  externalLinkBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    color: '#2563eb',
    fontSize: '12px',
    fontWeight: '500',
    textDecoration: 'none',
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.5)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 50,
    padding: '16px',
  },
  modalContent: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    maxWidth: '620px',
    width: '100%',
    maxHeight: '90vh',
    overflowY: 'auto',
    boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    padding: '20px',
    borderBottom: '1px solid #f3f4f6',
  },
  modalTitle: {
    fontSize: '18px',
    fontWeight: '700',
    color: '#111827',
    margin: '0 0 4px 0',
  },
  modalSub: {
    fontSize: '13px',
    color: '#6b7280',
    margin: 0,
  },
  modalCloseBtn: {
    background: 'none',
    border: 'none',
    color: '#6b7280',
    cursor: 'pointer',
  },
  modalBody: {
    padding: '20px',
  },
  modalMetaGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '12px',
    backgroundColor: '#f9fafb',
    padding: '14px',
    borderRadius: '8px',
  },
  modalMetaLabel: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#6b7280',
    textTransform: 'uppercase',
    display: 'block',
    marginBottom: '2px',
  },
  modalMetaVal: {
    fontSize: '13px',
    fontWeight: '500',
    color: '#111827',
  },
  modalDescriptionText: {
    fontSize: '13px',
    lineHeight: 1.6,
    color: '#374151',
    whiteSpace: 'pre-wrap',
    marginTop: '6px',
    maxHeight: '200px',
    overflowY: 'auto',
    padding: '10px',
    backgroundColor: '#f9fafb',
    borderRadius: '6px',
  },
  applyExternalBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 18px',
    borderRadius: '8px',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    fontSize: '13px',
    fontWeight: '600',
    textDecoration: 'none',
  },
  formRow: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '12px',
  },
  formField: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    marginBottom: '12px',
  },
  formLabel: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#374151',
  },
  formInput: {
    padding: '9px 12px',
    borderRadius: '6px',
    border: '1px solid #d1d5db',
    fontSize: '13px',
    outline: 'none',
  },
  formTextarea: {
    padding: '9px 12px',
    borderRadius: '6px',
    border: '1px solid #d1d5db',
    fontSize: '13px',
    outline: 'none',
    resize: 'vertical',
    fontFamily: 'inherit',
  },
  modalFooter: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: '10px',
    marginTop: '16px',
  },
  tabContainer: {
    display: 'flex',
    gap: '8px',
    marginBottom: '20px',
    borderBottom: '1px solid #e5e7eb',
    paddingBottom: '8px',
  },
  tabActive: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 16px',
    borderRadius: '8px',
    backgroundColor: '#eff6ff',
    color: '#2563eb',
    border: '1px solid #bfdbfe',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  tabInactive: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 16px',
    borderRadius: '8px',
    backgroundColor: 'transparent',
    color: '#6b7280',
    border: '1px solid transparent',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer',
  },
  matchBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '6px 12px',
    borderRadius: '6px',
    border: '1px solid #bfdbfe',
    backgroundColor: '#f0f7ff',
    color: '#2563eb',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  matchBtnPrimary: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '6px 12px',
    borderRadius: '6px',
    border: 'none',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  matchPill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 10px',
    borderRadius: '20px',
    border: '1px solid #e5e7eb',
    fontSize: '12px',
    fontWeight: '700',
  },
  quickSummaryText: {
    fontSize: '12px',
    color: '#4b5563',
    lineHeight: 1.5,
    margin: '10px 0',
    padding: '8px 12px',
    backgroundColor: '#f9fafb',
    borderRadius: '6px',
    borderLeft: '3px solid #2563eb',
  },
  meterCard: {
    backgroundColor: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '10px',
    padding: '16px',
    marginBottom: '16px',
  },
  meterHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '12px',
    marginBottom: '12px',
  },
  meterLabel: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    display: 'block',
    marginBottom: '2px',
  },
  scoreRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  meterScore: {
    fontSize: '28px',
    fontWeight: '800',
  },
  scoreTierBadge: {
    fontSize: '11px',
    fontWeight: '600',
    padding: '3px 8px',
    borderRadius: '6px',
    backgroundColor: '#f1f5f9',
    color: '#475569',
  },
  weightPills: {
    display: 'flex',
    gap: '8px',
  },
  weightPillItem: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    backgroundColor: '#ffffff',
    border: '1px solid #e2e8f0',
    borderRadius: '6px',
    padding: '4px 10px',
    minWidth: '65px',
  },
  weightVal: {
    fontSize: '13px',
    fontWeight: '700',
    color: '#1e293b',
  },
  weightKey: {
    fontSize: '10px',
    color: '#64748b',
    fontWeight: '500',
  },
  progressBarBg: {
    width: '100%',
    height: '8px',
    backgroundColor: '#e2e8f0',
    borderRadius: '4px',
    overflow: 'hidden',
    marginBottom: '12px',
  },
  progressBarFill: {
    height: '100%',
    borderRadius: '4px',
    transition: 'width 0.4s ease',
  },
  explanationText: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '8px',
    fontSize: '12px',
    lineHeight: 1.5,
    color: '#334155',
    backgroundColor: '#ffffff',
    padding: '10px 12px',
    borderRadius: '6px',
    border: '1px solid #e2e8f0',
  },
  expWarningAlert: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '10px',
    padding: '12px 14px',
    backgroundColor: '#fffbeb',
    border: '1px solid #fde68a',
    borderRadius: '8px',
    marginBottom: '16px',
  },
  expSuccessAlert: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '10px',
    padding: '12px 14px',
    backgroundColor: '#ecfdf5',
    border: '1px solid #a7f3d0',
    borderRadius: '8px',
    marginBottom: '16px',
  },
  sectionCard: {
    backgroundColor: '#ffffff',
    border: '1px solid #e5e7eb',
    borderRadius: '10px',
    padding: '16px',
    marginBottom: '16px',
  },
  sectionCardTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '14px',
    fontWeight: '700',
    color: '#111827',
    margin: '0 0 14px 0',
  },
  skillGroupHeader: {
    marginBottom: '6px',
  },
  skillGroupLabelSuccess: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#065f46',
  },
  skillGroupLabelCritical: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#991b1b',
  },
  skillGroupLabelSecondary: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#4b5563',
  },
  chipsContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
  },
  matchedChip: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 9px',
    borderRadius: '6px',
    backgroundColor: '#ecfdf5',
    border: '1px solid #a7f3d0',
    color: '#065f46',
    fontSize: '12px',
    fontWeight: '500',
  },
  missingCriticalChip: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 9px',
    borderRadius: '6px',
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    color: '#b91c1c',
    fontSize: '12px',
    fontWeight: '500',
  },
  missingSecondaryChip: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '4px 9px',
    borderRadius: '6px',
    backgroundColor: '#f3f4f6',
    border: '1px solid #e5e7eb',
    color: '#4b5563',
    fontSize: '12px',
    fontWeight: '500',
  },
  emptySkillsNotice: {
    fontSize: '12px',
    color: '#9ca3af',
    fontStyle: 'italic',
  },
  allSkillsMetNotice: {
    fontSize: '12px',
    color: '#059669',
    fontWeight: '500',
  },
  adviceCard: {
    backgroundColor: '#f5f3ff',
    border: '1px solid #ddd6fe',
    borderRadius: '10px',
    padding: '16px',
  },
  adviceCardHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    marginBottom: '6px',
  },
  adviceCardTitle: {
    fontSize: '14px',
    fontWeight: '700',
    color: '#5b21b6',
    margin: 0,
  },
  adviceDisclaimer: {
    fontSize: '11px',
    color: '#6d28d9',
    margin: '0 0 10px 0',
  },
  adviceList: {
    margin: 0,
    paddingLeft: '18px',
  },
  adviceListItem: {
    fontSize: '12px',
    lineHeight: 1.6,
    color: '#4c1d95',
    marginBottom: '6px',
  },
  verifyBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '6px 12px',
    borderRadius: '6px',
    border: '1px solid #a7f3d0',
    backgroundColor: '#ecfdf5',
    color: '#065f46',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
  },
  trackBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '6px 12px',
    borderRadius: '6px',
    border: '1px solid #bfdbfe',
    backgroundColor: '#eff6ff',
    color: '#2563eb',
    fontSize: '12px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  modalTrackBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '10px 18px',
    borderRadius: '8px',
    border: '1px solid #2563eb',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  scamFlagsAlertBox: {
    backgroundColor: '#fef2f2',
    border: '1px solid #fecaca',
    borderRadius: '8px',
    padding: '14px',
    marginBottom: '16px',
  },
  scamFlagsList: {
    margin: 0,
    paddingLeft: '20px',
  },
  scamFlagsListItem: {
    fontSize: '12px',
    color: '#991b1b',
    lineHeight: 1.5,
    marginBottom: '4px',
  },
  verificationGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: '12px',
    marginBottom: '16px',
  },
  verifyMetricCard: {
    backgroundColor: '#ffffff',
    border: '1px solid #e5e7eb',
    borderRadius: '8px',
    padding: '12px 14px',
  },
  verifyMetricHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '4px',
  },
  verifyMetricTitle: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#6b7280',
    textTransform: 'uppercase',
    letterSpacing: '0.4px',
  },
  verifyMetricVal: {
    display: 'block',
    fontSize: '13px',
    fontWeight: '700',
    color: '#111827',
  },
  verifyMetricSub: {
    display: 'block',
    fontSize: '11px',
    color: '#6b7280',
    marginTop: '2px',
  },
  evidencePointsContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  evidencePointRow: {
    padding: '10px 12px',
    borderRadius: '6px',
    border: '1px solid #e5e7eb',
  },
  safetyNoticeBox: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '10px',
    padding: '12px 14px',
    backgroundColor: '#f0fdf4',
    border: '1px solid #bbf7d0',
    borderRadius: '8px',
    marginTop: '16px',
  },
  profilePromptBanner: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: '12px',
    padding: '12px 18px',
    backgroundColor: '#fffbeb',
    border: '1px solid #fde68a',
    borderRadius: '10px',
    marginBottom: '20px',
    flexWrap: 'wrap',
  },
  profilePromptLink: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '6px 14px',
    borderRadius: '6px',
    backgroundColor: '#d97706',
    color: '#ffffff',
    fontSize: '12px',
    fontWeight: '600',
    textDecoration: 'none',
  },
  ruleBasedDisclaimer: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '10px',
    padding: '12px 14px',
    backgroundColor: '#f8fafc',
    border: '1px solid #e2e8f0',
    borderRadius: '8px',
    fontSize: '12px',
    color: '#64748b',
    lineHeight: 1.5,
    marginTop: '18px',
  },
};


