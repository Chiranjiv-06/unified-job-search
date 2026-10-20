import React, { useState, useEffect } from 'react';
import useAuth from '../hooks/useAuth';
import { getProfileApi, updateProfileApi, uploadResumeApi, confirmSkillsApi } from '../services/api';
import {
  User,
  GraduationCap,
  Briefcase,
  MapPin,
  IndianRupee,
  Plus,
  X,
  Save,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Layers,
  FileText,
  Upload,
  Check
} from 'lucide-react';

export default function Profile() {
  const { user } = useAuth();

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [successMsg, setSuccessMsg] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);

  // Form states
  const [education, setEducation] = useState('');
  const [experienceLevel, setExperienceLevel] = useState('Entry-Level');
  const [preferredRoles, setPreferredRoles] = useState('');
  const [preferredLocations, setPreferredLocations] = useState('');
  const [preferredWorkMode, setPreferredWorkMode] = useState('Any');
  const [salaryExpectation, setSalaryExpectation] = useState('');

  // Skills state
  const [skills, setSkills] = useState([]);
  const [newSkillName, setNewSkillName] = useState('');
  const [newSkillProficiency, setNewSkillProficiency] = useState('Intermediate');

  // Resume upload & draft suggestions state
  const [resumeFile, setResumeFile] = useState(null);
  const [resumeUploading, setResumeUploading] = useState(false);
  const [resumeNotice, setResumeNotice] = useState(null);
  const [draftSkills, setDraftSkills] = useState([]);
  const [selectedDraftSkills, setSelectedDraftSkills] = useState(new Set());
  const [extractedPreview, setExtractedPreview] = useState('');


  useEffect(() => {
    let ignore = false;

    const fetchProfile = async () => {
      try {
        const data = await getProfileApi();
        if (!ignore) {
          setEducation(data.education || '');
          setExperienceLevel(data.experience_level || 'Entry-Level');
          setPreferredRoles(data.preferred_roles || '');
          setPreferredLocations(data.preferred_locations || '');
          setPreferredWorkMode(data.preferred_work_mode || 'Any');
          setSalaryExpectation(data.salary_expectation || '');
          setSkills(data.skills || []);
        }
      } catch (err) {
        if (!ignore) {
          setErrorMsg(err.customMessage || 'Failed to load profile.');
        }
      } finally {
        if (!ignore) {
          setLoading(false);
        }
      }
    };

    fetchProfile();

    return () => {
      ignore = true;
    };
  }, []);

  const handleResumeFileSelect = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setErrorMsg('Only PDF documents (.pdf) are allowed.');
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      setErrorMsg('Resume file size exceeds the 5MB maximum limit.');
      return;
    }
    setErrorMsg(null);
    setResumeNotice(null);
    setResumeFile(file);
  };

  const handleUploadResume = async () => {
    if (!resumeFile) return;
    setResumeUploading(true);
    setResumeNotice(null);

    try {
      const data = await uploadResumeApi(resumeFile);
      setExtractedPreview(data.extracted_text_preview || '');
      setResumeNotice({
        type: data.warning ? 'warning' : 'success',
        text: data.warning || data.message || 'Resume uploaded and processed successfully!',
      });

      if (data.draft_suggestions && data.draft_suggestions.length > 0) {
        setDraftSkills(data.draft_suggestions);
        const existingSet = new Set(skills.map((s) => s.skill_name.toLowerCase()));
        const initialSelected = new Set();
        data.draft_suggestions.forEach((item) => {
          if (!existingSet.has(item.skill_name.toLowerCase())) {
            initialSelected.add(item.skill_name);
          }
        });
        setSelectedDraftSkills(initialSelected);
      }
    } catch (err) {
      setResumeNotice({
        type: 'error',
        text: err.customMessage || 'Failed to upload and parse resume.',
      });
    } finally {
      setResumeUploading(false);
    }
  };

  const handleToggleDraftSkill = (skillName) => {
    setSelectedDraftSkills((prev) => {
      const next = new Set(prev);
      if (next.has(skillName)) {
        next.delete(skillName);
      } else {
        next.add(skillName);
      }
      return next;
    });
  };

  const handleConfirmSelectedDraftSkills = async () => {
    const toConfirm = draftSkills.filter((d) => selectedDraftSkills.has(d.skill_name));
    if (toConfirm.length === 0) return;

    try {
      const updated = await confirmSkillsApi(toConfirm);
      setSkills(updated.skills || []);
      setDraftSkills((prev) => prev.filter((d) => !selectedDraftSkills.has(d.skill_name)));
      setSelectedDraftSkills(new Set());
      setSuccessMsg(`Added ${toConfirm.length} skills from your resume to your profile!`);
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to confirm selected skills.');
    }
  };

  const handleAddSkill = (e) => {

    e.preventDefault();
    const trimmed = newSkillName.trim();
    if (!trimmed) return;

    // Prevent duplicates
    if (skills.some((s) => s.skill_name.toLowerCase() === trimmed.toLowerCase())) {
      return;
    }

    setSkills([
      ...skills,
      { skill_name: trimmed, proficiency_level: newSkillProficiency },
    ]);
    setNewSkillName('');
    setNewSkillProficiency('Intermediate');
  };

  const handleRemoveSkill = (skillToRemove) => {
    setSkills(skills.filter((s) => s.skill_name !== skillToRemove));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    setSuccessMsg(null);
    setErrorMsg(null);

    try {
      const payload = {
        education,
        experience_level: experienceLevel,
        preferred_roles: preferredRoles,
        preferred_locations: preferredLocations,
        preferred_work_mode: preferredWorkMode,
        salary_expectation: salaryExpectation,
        skills: skills.map((s) => ({
          skill_name: s.skill_name,
          proficiency_level: s.proficiency_level,
        })),
      };

      const updated = await updateProfileApi(payload);
      setSkills(updated.skills || []);
      setSuccessMsg('Profile and preferences updated successfully!');
      setTimeout(() => setSuccessMsg(null), 4000);
    } catch (err) {
      setErrorMsg(err.customMessage || 'Failed to update profile.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={styles.loadingContainer}>
        <Loader2 size={32} className="spin" color="#2563eb" />
        <p>Loading candidate profile...</p>
      </div>
    );
  }

  return (
    <div style={styles.container}>
      <div style={styles.pageHeader}>
        <div>
          <h1 style={styles.pageTitle}>Candidate Profile</h1>
          <p style={styles.pageSub}>
            Define your qualifications, technical skills, and target job preferences
          </p>
        </div>
      </div>

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

      <form onSubmit={handleSubmit} style={styles.formGrid}>
        {/* Basic Candidate Info Card */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <User size={18} color="#2563eb" />
            <h3 style={styles.cardTitle}>Personal Details</h3>
          </div>
          <div style={styles.row}>
            <div style={styles.fieldGroup}>
              <label style={styles.label}>Full Name</label>
              <input
                type="text"
                value={user?.full_name || ''}
                disabled
                style={styles.disabledInput}
              />
            </div>
            <div style={styles.fieldGroup}>
              <label style={styles.label}>Email Address</label>
              <input
                type="text"
                value={user?.email || ''}
                disabled
                style={styles.disabledInput}
              />
            </div>
          </div>
        </div>

        {/* Education & Experience Card */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <GraduationCap size={18} color="#2563eb" />
            <h3 style={styles.cardTitle}>Education & Career Level</h3>
          </div>

          <div style={styles.fieldGroup}>
            <label style={styles.label}>Degree & Institution</label>
            <input
              type="text"
              placeholder="e.g. B.Tech in Information Technology, 2026"
              value={education}
              onChange={(e) => setEducation(e.target.value)}
              style={styles.input}
            />
          </div>

          <div style={styles.row}>
            <div style={styles.fieldGroup}>
              <label style={styles.label}>Experience Level</label>
              <select
                value={experienceLevel}
                onChange={(e) => setExperienceLevel(e.target.value)}
                style={styles.select}
              >
                <option value="Intern">Intern</option>
                <option value="Entry-Level">Entry-Level (0 - 2 yrs)</option>
                <option value="Mid-Level">Mid-Level (2 - 5 yrs)</option>
                <option value="Senior">Senior (5+ yrs)</option>
              </select>
            </div>

            <div style={styles.fieldGroup}>
              <label style={styles.label}>Preferred Work Mode</label>
              <select
                value={preferredWorkMode}
                onChange={(e) => setPreferredWorkMode(e.target.value)}
                style={styles.select}
              >
                <option value="Any">Any / Open</option>
                <option value="Remote">Remote</option>
                <option value="Hybrid">Hybrid</option>
                <option value="On-site">On-site</option>
              </select>
            </div>
          </div>
        </div>

        {/* Job Preferences Card */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <Briefcase size={18} color="#2563eb" />
            <h3 style={styles.cardTitle}>Target Job Preferences</h3>
          </div>

          <div style={styles.fieldGroup}>
            <label style={styles.label}>
              <Briefcase size={14} style={{ marginRight: '6px' }} />
              Preferred Roles (comma-separated)
            </label>
            <input
              type="text"
              placeholder="e.g. Software Engineer, Full Stack Developer, Python Developer"
              value={preferredRoles}
              onChange={(e) => setPreferredRoles(e.target.value)}
              style={styles.input}
            />
          </div>

          <div style={styles.row}>
            <div style={styles.fieldGroup}>
              <label style={styles.label}>
                <MapPin size={14} style={{ marginRight: '6px' }} />
                Target Locations (comma-separated)
              </label>
              <input
                type="text"
                placeholder="e.g. Bengaluru, Pune, Hyderabad, Remote"
                value={preferredLocations}
                onChange={(e) => setPreferredLocations(e.target.value)}
                style={styles.input}
              />
            </div>

            <div style={styles.fieldGroup}>
              <label style={styles.label}>
                <IndianRupee size={14} style={{ marginRight: '6px' }} />
                Salary Expectation (optional)
              </label>
              <input
                type="text"
                placeholder="e.g. 6 - 10 LPA"
                value={salaryExpectation}
                onChange={(e) => setSalaryExpectation(e.target.value)}
                style={styles.input}
              />
            </div>
          </div>
        </div>

        {/* Resume & Skill Auto-Extraction Card */}
        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <FileText size={18} color="#2563eb" />
            <h3 style={styles.cardTitle}>Resume & Skill Auto-Extraction (PDF)</h3>
          </div>
          <p style={{ fontSize: '13px', color: '#6b7280', margin: '0 0 16px 0' }}>
            Upload your PDF resume (max 5MB). Our parser extracts plain text and provides draft skill suggestions for your manual review before updating profile data.
          </p>

          <div style={styles.resumeUploadRow}>
            <input
              type="file"
              accept=".pdf,application/pdf"
              id="resume-file-input"
              onChange={handleResumeFileSelect}
              style={{ display: 'none' }}
            />
            <label htmlFor="resume-file-input" style={styles.chooseFileBtn}>
              <Upload size={16} />
              <span>{resumeFile ? resumeFile.name : 'Choose PDF Resume'}</span>
            </label>
            <button
              type="button"
              onClick={handleUploadResume}
              disabled={!resumeFile || resumeUploading}
              style={(!resumeFile || resumeUploading) ? styles.uploadBtnDisabled : styles.uploadBtn}
            >
              {resumeUploading ? (
                <>
                  <Loader2 size={15} className="spin" />
                  <span>Extracting Skills...</span>
                </>
              ) : (
                <>
                  <FileText size={15} />
                  <span>Upload & Extract</span>
                </>
              )}
            </button>
          </div>

          {resumeNotice && (
            <div
              style={
                resumeNotice.type === 'error'
                  ? styles.errorBanner
                  : resumeNotice.type === 'warning'
                  ? styles.warningBanner
                  : styles.successBanner
              }
            >
              {resumeNotice.type === 'error' ? (
                <AlertCircle size={16} color="#b91c1c" />
              ) : (
                <CheckCircle2 size={16} color="#059669" />
              )}
              <span>{resumeNotice.text}</span>
            </div>
          )}

          {draftSkills.length > 0 && (
            <div style={styles.draftSection}>
              <div style={styles.draftHeader}>
                <span style={styles.draftTitle}>
                  Draft Skill Suggestions ({draftSkills.length} found)
                </span>
                <span style={styles.draftSub}>
                  Select skills to include in your profile:
                </span>
              </div>
              <div style={styles.draftChipsContainer}>
                {draftSkills.map((draft, idx) => {
                  const isSelected = selectedDraftSkills.has(draft.skill_name);
                  return (
                    <button
                      type="button"
                      key={idx}
                      onClick={() => handleToggleDraftSkill(draft.skill_name)}
                      style={isSelected ? styles.draftChipSelected : styles.draftChip}
                    >
                      {isSelected && <Check size={13} style={{ marginRight: '4px' }} />}
                      <span>{draft.skill_name}</span>
                    </button>
                  );
                })}
              </div>
              <div style={{ marginTop: '12px', display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                <button
                  type="button"
                  onClick={handleConfirmSelectedDraftSkills}
                  disabled={selectedDraftSkills.size === 0}
                  style={selectedDraftSkills.size === 0 ? styles.confirmBtnDisabled : styles.confirmBtn}
                >
                  <Check size={14} />
                  <span>Confirm Selected ({selectedDraftSkills.size})</span>
                </button>
                {extractedPreview && (
                  <span style={{ fontSize: '12px', color: '#6b7280' }}>
                    Preview: &quot;{extractedPreview.slice(0, 70)}...&quot;
                  </span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Skills Card */}

        <div style={styles.card}>
          <div style={styles.cardHeader}>
            <Layers size={18} color="#2563eb" />
            <h3 style={styles.cardTitle}>Technical Skills & Competencies</h3>
          </div>

          <div style={styles.skillInputRow}>
            <input
              type="text"
              placeholder="Skill name (e.g. Python, React, SQL)"
              value={newSkillName}
              onChange={(e) => setNewSkillName(e.target.value)}
              style={{ ...styles.input, flex: 2 }}
            />
            <select
              value={newSkillProficiency}
              onChange={(e) => setNewSkillProficiency(e.target.value)}
              style={{ ...styles.select, flex: 1 }}
            >
              <option value="Beginner">Beginner</option>
              <option value="Intermediate">Intermediate</option>
              <option value="Advanced">Advanced</option>
            </select>
            <button
              type="button"
              onClick={handleAddSkill}
              style={styles.addSkillBtn}
            >
              <Plus size={16} />
              <span>Add</span>
            </button>
          </div>

          <div style={styles.skillsChipContainer}>
            {skills.length === 0 ? (
              <span style={styles.noSkillsText}>
                No skills added yet. Add your programming languages, frameworks, and databases above.
              </span>
            ) : (
              skills.map((s, idx) => (
                <div key={idx} style={styles.skillChip}>
                  <span style={styles.skillChipName}>{s.skill_name}</span>
                  <span style={styles.skillChipLevel}>({s.proficiency_level})</span>
                  <button
                    type="button"
                    onClick={() => handleRemoveSkill(s.skill_name)}
                    style={styles.removeSkillBtn}
                    title="Remove skill"
                  >
                    <X size={12} />
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Submit Actions */}
        <div style={styles.actionRow}>
          <button type="submit" style={styles.saveBtn} disabled={saving}>
            {saving ? (
              <>
                <Loader2 size={16} className="spin" />
                <span>Saving Changes...</span>
              </>
            ) : (
              <>
                <Save size={16} />
                <span>Save Candidate Profile</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

const styles = {
  container: {
    maxWidth: '900px',
    margin: '32px auto',
    padding: '0 24px',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  pageHeader: {
    marginBottom: '24px',
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
    fontWeight: '500',
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
  formGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '20px',
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    border: '1px solid #e5e7eb',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.04)',
    padding: '24px',
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '16px',
    borderBottom: '1px solid #f3f4f6',
    paddingBottom: '12px',
  },
  cardTitle: {
    fontSize: '16px',
    fontWeight: '600',
    color: '#111827',
    margin: 0,
  },
  row: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '16px',
  },
  fieldGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
    marginBottom: '14px',
  },
  label: {
    display: 'flex',
    alignItems: 'center',
    fontSize: '13px',
    fontWeight: '500',
    color: '#374151',
  },
  input: {
    padding: '10px 12px',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    fontSize: '14px',
    outline: 'none',
    boxSizing: 'border-box',
    transition: 'border-color 0.15s ease',
  },
  disabledInput: {
    padding: '10px 12px',
    borderRadius: '8px',
    border: '1px solid #e5e7eb',
    backgroundColor: '#f9fafb',
    color: '#6b7280',
    fontSize: '14px',
    boxSizing: 'border-box',
  },
  select: {
    padding: '10px 12px',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    fontSize: '14px',
    backgroundColor: '#ffffff',
    outline: 'none',
  },
  skillInputRow: {
    display: 'flex',
    gap: '10px',
    marginBottom: '16px',
  },
  addSkillBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    padding: '10px 16px',
    borderRadius: '8px',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    fontSize: '13px',
    fontWeight: '600',
    border: 'none',
    cursor: 'pointer',
  },
  skillsChipContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
    minHeight: '44px',
    padding: '12px',
    borderRadius: '8px',
    backgroundColor: '#f9fafb',
    border: '1px solid #e5e7eb',
  },
  noSkillsText: {
    fontSize: '13px',
    color: '#9ca3af',
  },
  skillChip: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 10px',
    borderRadius: '20px',
    backgroundColor: '#eff6ff',
    border: '1px solid #bfdbfe',
    color: '#1e40af',
    fontSize: '13px',
  },
  skillChipName: {
    fontWeight: '600',
  },
  skillChipLevel: {
    fontSize: '11px',
    color: '#3b82f6',
  },
  removeSkillBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '18px',
    height: '18px',
    borderRadius: '50%',
    border: 'none',
    backgroundColor: '#dbeafe',
    color: '#1e40af',
    cursor: 'pointer',
    padding: 0,
  },
  actionRow: {
    display: 'flex',
    justifyContent: 'flex-end',
    marginTop: '12px',
  },
  saveBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px 24px',
    borderRadius: '8px',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    fontSize: '14px',
    fontWeight: '600',
    border: 'none',
    cursor: 'pointer',
    boxShadow: '0 2px 4px rgba(37, 99, 235, 0.2)',
  },
  resumeUploadRow: {
    display: 'flex',
    gap: '12px',
    alignItems: 'center',
    marginBottom: '14px',
    flexWrap: 'wrap',
  },
  chooseFileBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '9px 14px',
    borderRadius: '8px',
    backgroundColor: '#f3f4f6',
    border: '1px solid #d1d5db',
    fontSize: '13px',
    fontWeight: '500',
    color: '#374151',
    cursor: 'pointer',
  },
  uploadBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '9px 16px',
    borderRadius: '8px',
    backgroundColor: '#1d4ed8',
    color: '#ffffff',
    fontSize: '13px',
    fontWeight: '600',
    border: 'none',
    cursor: 'pointer',
  },
  uploadBtnDisabled: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '9px 16px',
    borderRadius: '8px',
    backgroundColor: '#93c5fd',
    color: '#ffffff',
    fontSize: '13px',
    fontWeight: '600',
    border: 'none',
    cursor: 'not-allowed',
  },
  warningBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '12px 16px',
    backgroundColor: '#fffbeb',
    border: '1px solid #fde68a',
    borderRadius: '8px',
    color: '#92400e',
    fontSize: '13px',
    marginBottom: '16px',
  },
  draftSection: {
    backgroundColor: '#f8fafc',
    borderRadius: '8px',
    border: '1px dashed #cbd5e1',
    padding: '16px',
    marginTop: '12px',
  },
  draftHeader: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
    marginBottom: '12px',
  },
  draftTitle: {
    fontSize: '14px',
    fontWeight: '600',
    color: '#0f172a',
  },
  draftSub: {
    fontSize: '12px',
    color: '#64748b',
  },
  draftChipsContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
  },
  draftChip: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '6px 12px',
    borderRadius: '20px',
    backgroundColor: '#ffffff',
    border: '1px solid #cbd5e1',
    color: '#475569',
    fontSize: '13px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  draftChipSelected: {
    display: 'inline-flex',
    alignItems: 'center',
    padding: '6px 12px',
    borderRadius: '20px',
    backgroundColor: '#dbeafe',
    border: '1px solid #2563eb',
    color: '#1d4ed8',
    fontSize: '13px',
    fontWeight: '600',
    cursor: 'pointer',
    boxShadow: '0 1px 2px rgba(37, 99, 235, 0.15)',
  },
  confirmBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 14px',
    borderRadius: '6px',
    backgroundColor: '#059669',
    color: '#ffffff',
    fontSize: '12px',
    fontWeight: '600',
    border: 'none',
    cursor: 'pointer',
  },
  confirmBtnDisabled: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '8px 14px',
    borderRadius: '6px',
    backgroundColor: '#a7f3d0',
    color: '#ffffff',
    fontSize: '12px',
    fontWeight: '600',
    border: 'none',
    cursor: 'not-allowed',
  },
};

