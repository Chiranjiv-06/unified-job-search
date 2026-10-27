import React, { useState, useEffect, useRef } from 'react';
import useAuth from '../hooks/useAuth';
import { getProfileApi, updateProfileApi, uploadResumeApi, confirmSkillsApi, getTargetRolesApi } from '../services/api';
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
  Check,
  Search,
  Sparkles,
  Trash2
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
  const [preferredLocations, setPreferredLocations] = useState('');
  const [preferredWorkMode, setPreferredWorkMode] = useState('Any');
  const [salaryExpectation, setSalaryExpectation] = useState('');

  // Target Roles states
  const [targetRoles, setTargetRoles] = useState([]);
  const [roleSearchInput, setRoleSearchInput] = useState('');
  const [availableRoles, setAvailableRoles] = useState([
    'Backend Developer', 'Software Developer', 'Full Stack Developer',
    'Python Developer', 'Java Developer', 'Data Analyst', 'Data Scientist',
    'AI/ML Engineer', 'DevOps Engineer', 'QA / Test Engineer',
    'Database Developer', 'Cybersecurity Analyst', 'Frontend Developer',
    'Cloud Engineer', 'Mobile Developer'
  ]);
  const [isRoleDropdownOpen, setIsRoleDropdownOpen] = useState(false);
  const roleDropdownRef = useRef(null);

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

    const fetchProfileData = async () => {
      try {
        // Fetch target roles from backend
        getTargetRolesApi()
          .then((data) => {
            if (data?.roles && Array.isArray(data.roles) && data.roles.length > 0) {
              setAvailableRoles(data.roles);
            }
          })
          .catch(() => {
            // Keep default list
          });

        const data = await getProfileApi();
        if (!ignore) {
          setEducation(data.education || '');
          setExperienceLevel(data.experience_level || 'Entry-Level');

          // Parse and load preferred roles
          if (Array.isArray(data.preferred_roles)) {
            setTargetRoles(data.preferred_roles);
          } else if (typeof data.preferred_roles === 'string' && data.preferred_roles.trim()) {
            try {
              const parsed = JSON.parse(data.preferred_roles);
              if (Array.isArray(parsed)) {
                setTargetRoles(parsed);
              } else {
                setTargetRoles(data.preferred_roles.split(',').map((r) => r.trim()).filter(Boolean));
              }
            } catch {
              setTargetRoles(data.preferred_roles.split(',').map((r) => r.trim()).filter(Boolean));
            }
          } else {
            setTargetRoles([]);
          }

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

    fetchProfileData();

    return () => {
      ignore = true;
    };
  }, []);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (roleDropdownRef.current && !roleDropdownRef.current.contains(event.target)) {
        setIsRoleDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleAddTargetRole = (roleToAdd) => {
    const clean = roleToAdd?.trim();
    if (!clean) return;
    const lower = clean.toLowerCase();
    if (!targetRoles.some((r) => r.toLowerCase() === lower)) {
      setTargetRoles((prev) => [...prev, clean]);
    }
    setRoleSearchInput('');
    setIsRoleDropdownOpen(false);
  };

  const handleRemoveTargetRole = (roleToRemove) => {
    setTargetRoles((prev) => prev.filter((r) => r.toLowerCase() !== roleToRemove.toLowerCase()));
  };

  const handleClearAllTargetRoles = () => {
    setTargetRoles([]);
  };

  const handleRoleInputKeyDown = (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      if (roleSearchInput.trim()) {
        const firstMatch = filteredAvailableRoles.find(
          (r) => !targetRoles.some((t) => t.toLowerCase() === r.toLowerCase())
        );
        if (firstMatch) {
          handleAddTargetRole(firstMatch);
        } else {
          handleAddTargetRole(roleSearchInput.trim());
        }
      }
    } else if (e.key === 'Escape') {
      setIsRoleDropdownOpen(false);
    }
  };

  const filteredAvailableRoles = availableRoles.filter((role) =>
    role.toLowerCase().includes(roleSearchInput.trim().toLowerCase())
  );

  const suggestedRolesToAdd = availableRoles.filter(
    (role) => !targetRoles.some((r) => r.toLowerCase() === role.toLowerCase())
  );

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
        preferred_roles: targetRoles,
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
      if (Array.isArray(updated.preferred_roles)) {
        setTargetRoles(updated.preferred_roles);
      }
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

          {/* Target Roles Multi-Select Section */}
          <div style={styles.fieldGroup}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
              <label style={styles.label}>
                <Briefcase size={14} style={{ marginRight: '6px' }} />
                Target Job Roles ({targetRoles.length} selected)
              </label>
              {targetRoles.length > 0 && (
                <button
                  type="button"
                  onClick={handleClearAllTargetRoles}
                  style={styles.clearRolesBtn}
                  title="Clear all selected target roles"
                >
                  <Trash2 size={12} />
                  <span>Clear All</span>
                </button>
              )}
            </div>
            <p style={{ fontSize: '12px', color: '#6b7280', margin: '0 0 8px 0' }}>
              Select the job roles you want to pursue. Our explainable ranking algorithm prioritizes opportunities directly aligning with these target roles.
            </p>

            {/* Searchable input with suggestion dropdown */}
            <div ref={roleDropdownRef} style={styles.roleSearchContainer}>
              <div style={styles.roleInputWrapper}>
                <Search size={15} color="#9ca3af" style={{ marginLeft: '10px' }} />
                <input
                  type="text"
                  id="target-roles-search-input"
                  placeholder="Search roles to add (e.g. Backend Developer, Data Analyst)..."
                  value={roleSearchInput}
                  onChange={(e) => {
                    setRoleSearchInput(e.target.value);
                    setIsRoleDropdownOpen(true);
                  }}
                  onFocus={() => setIsRoleDropdownOpen(true)}
                  onKeyDown={handleRoleInputKeyDown}
                  style={styles.roleSearchInput}
                  role="combobox"
                  aria-expanded={isRoleDropdownOpen}
                  aria-autocomplete="list"
                />
                {roleSearchInput.trim() && (
                  <button
                    type="button"
                    onClick={() => handleAddTargetRole(roleSearchInput)}
                    style={styles.addRoleInlineBtn}
                  >
                    <Plus size={14} />
                    <span>Add</span>
                  </button>
                )}
              </div>

              {isRoleDropdownOpen && filteredAvailableRoles.length > 0 && (
                <div style={styles.roleDropdown}>
                  {filteredAvailableRoles.map((role) => {
                    const isSelected = targetRoles.some(
                      (r) => r.toLowerCase() === role.toLowerCase()
                    );
                    return (
                      <div
                        key={role}
                        onClick={() => {
                          if (!isSelected) {
                            handleAddTargetRole(role);
                          } else {
                            handleRemoveTargetRole(role);
                          }
                        }}
                        style={{
                          ...styles.roleDropdownItem,
                          backgroundColor: isSelected ? '#eff6ff' : '#ffffff',
                          color: isSelected ? '#1d4ed8' : '#1f2937',
                          fontWeight: isSelected ? '600' : '400',
                        }}
                      >
                        <span>{role}</span>
                        {isSelected ? (
                          <span style={{ fontSize: '11px', color: '#2563eb', display: 'flex', alignItems: 'center', gap: '3px' }}>
                            <Check size={13} /> Selected
                          </span>
                        ) : (
                          <span style={{ fontSize: '11px', color: '#6b7280' }}>
                            + Add
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Selected Target Roles Chips */}
            <div style={styles.targetRolesChipContainer}>
              {targetRoles.length === 0 ? (
                <span style={styles.noRolesText}>
                  No target roles selected yet. Search above or pick from popular recommendations below to prioritize your job feed.
                </span>
              ) : (
                targetRoles.map((role) => (
                  <div key={role} style={styles.targetRoleChip}>
                    <Briefcase size={12} color="#2563eb" />
                    <span>{role}</span>
                    <button
                      type="button"
                      onClick={() => handleRemoveTargetRole(role)}
                      style={styles.removeRoleBtn}
                      title={`Remove ${role}`}
                      aria-label={`Remove ${role}`}
                    >
                      <X size={12} />
                    </button>
                  </div>
                ))
              )}
            </div>

            {/* Quick Suggestion Pills */}
            {suggestedRolesToAdd.length > 0 && (
              <div style={{ marginTop: '10px', display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                <span style={{ fontSize: '11px', color: '#6b7280', display: 'flex', alignItems: 'center', gap: '3px' }}>
                  <Sparkles size={12} color="#f59e0b" /> Popular:
                </span>
                {suggestedRolesToAdd.slice(0, 5).map((role) => (
                  <button
                    key={role}
                    type="button"
                    onClick={() => handleAddTargetRole(role)}
                    style={styles.suggestionPill}
                  >
                    <Plus size={11} /> {role}
                  </button>
                ))}
              </div>
            )}
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
  roleSearchContainer: {
    position: 'relative',
    marginBottom: '10px',
  },
  roleInputWrapper: {
    display: 'flex',
    alignItems: 'center',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    backgroundColor: '#ffffff',
    overflow: 'hidden',
    transition: 'border-color 0.15s ease',
  },
  roleSearchInput: {
    flex: 1,
    padding: '9px 12px',
    border: 'none',
    fontSize: '13px',
    outline: 'none',
    backgroundColor: 'transparent',
  },
  addRoleInlineBtn: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
    marginRight: '6px',
    padding: '5px 12px',
    borderRadius: '6px',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    fontSize: '12px',
    fontWeight: '600',
    border: 'none',
    cursor: 'pointer',
  },
  roleDropdown: {
    position: 'absolute',
    top: '100%',
    left: 0,
    right: 0,
    maxHeight: '220px',
    overflowY: 'auto',
    backgroundColor: '#ffffff',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    boxShadow: '0 6px 16px rgba(0, 0, 0, 0.08)',
    zIndex: 30,
    marginTop: '4px',
  },
  roleDropdownItem: {
    padding: '9px 14px',
    fontSize: '13px',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottom: '1px solid #f9fafb',
  },
  targetRolesChipContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '8px',
    minHeight: '44px',
    padding: '12px',
    borderRadius: '8px',
    backgroundColor: '#f9fafb',
    border: '1px solid #e5e7eb',
  },
  noRolesText: {
    fontSize: '13px',
    color: '#9ca3af',
  },
  targetRoleChip: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '6px 12px',
    borderRadius: '20px',
    backgroundColor: '#eff6ff',
    border: '1px solid #bfdbfe',
    color: '#1d4ed8',
    fontSize: '13px',
    fontWeight: '500',
  },
  removeRoleBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '18px',
    height: '18px',
    borderRadius: '50%',
    backgroundColor: 'transparent',
    border: 'none',
    color: '#3b82f6',
    cursor: 'pointer',
  },
  clearRolesBtn: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    background: 'none',
    border: 'none',
    color: '#ef4444',
    fontSize: '12px',
    cursor: 'pointer',
    padding: '2px 6px',
    borderRadius: '4px',
  },
  suggestionPill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 10px',
    borderRadius: '16px',
    backgroundColor: '#f3f4f6',
    border: '1px solid #e5e7eb',
    color: '#4b5563',
    fontSize: '11px',
    fontWeight: '500',
    cursor: 'pointer',
    transition: 'all 0.12s ease',
  },
};

