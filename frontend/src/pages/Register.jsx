import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import { UserPlus, User, Mail, Lock, AlertCircle, Loader2 } from 'lucide-react';

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [validationErrors, setValidationErrors] = useState({});

  const validate = () => {
    const errors = {};
    if (!fullName.trim()) {
      errors.fullName = 'Full name is required.';
    }
    if (!email.trim()) {
      errors.email = 'Email address is required.';
    } else if (!/\S+@\S+\.\S+/.test(email)) {
      errors.email = 'Please enter a valid email address.';
    }
    if (!password) {
      errors.password = 'Password is required.';
    } else if (password.length < 6) {
      errors.password = 'Password must be at least 6 characters.';
    }
    if (password !== confirmPassword) {
      errors.confirmPassword = 'Passwords do not match.';
    }
    setValidationErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!validate()) return;

    setLoading(true);
    try {
      await register(fullName, email, password);
      navigate('/profile');
    } catch (err) {
      setError(err.customMessage || 'Registration failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <div style={styles.card}>
        <div style={styles.header}>
          <div style={styles.iconCircle}>
            <UserPlus size={24} color="#2563eb" />
          </div>
          <h2 style={styles.title}>Create Account</h2>
          <p style={styles.subtitle}>Join Unified Job Search as a candidate</p>
        </div>

        {error && (
          <div style={styles.errorBanner}>
            <AlertCircle size={18} color="#b91c1c" />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={styles.form}>
          <div style={styles.formGroup}>
            <label style={styles.label}>Full Name</label>
            <div style={styles.inputWrapper}>
              <User size={18} style={styles.inputIcon} />
              <input
                type="text"
                placeholder="Pankaj Sharma"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                style={{
                  ...styles.input,
                  borderColor: validationErrors.fullName ? '#ef4444' : '#d1d5db',
                }}
                disabled={loading}
              />
            </div>
            {validationErrors.fullName && (
              <span style={styles.fieldError}>{validationErrors.fullName}</span>
            )}
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Email Address</label>
            <div style={styles.inputWrapper}>
              <Mail size={18} style={styles.inputIcon} />
              <input
                type="email"
                placeholder="candidate@university.edu"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{
                  ...styles.input,
                  borderColor: validationErrors.email ? '#ef4444' : '#d1d5db',
                }}
                disabled={loading}
              />
            </div>
            {validationErrors.email && (
              <span style={styles.fieldError}>{validationErrors.email}</span>
            )}
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Password</label>
            <div style={styles.inputWrapper}>
              <Lock size={18} style={styles.inputIcon} />
              <input
                type="password"
                placeholder="Min 6 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{
                  ...styles.input,
                  borderColor: validationErrors.password ? '#ef4444' : '#d1d5db',
                }}
                disabled={loading}
              />
            </div>
            {validationErrors.password && (
              <span style={styles.fieldError}>{validationErrors.password}</span>
            )}
          </div>

          <div style={styles.formGroup}>
            <label style={styles.label}>Confirm Password</label>
            <div style={styles.inputWrapper}>
              <Lock size={18} style={styles.inputIcon} />
              <input
                type="password"
                placeholder="Re-enter your password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                style={{
                  ...styles.input,
                  borderColor: validationErrors.confirmPassword ? '#ef4444' : '#d1d5db',
                }}
                disabled={loading}
              />
            </div>
            {validationErrors.confirmPassword && (
              <span style={styles.fieldError}>{validationErrors.confirmPassword}</span>
            )}
          </div>

          <button type="submit" style={styles.submitBtn} disabled={loading}>
            {loading ? (
              <>
                <Loader2 size={16} className="spin" />
                <span>Creating account...</span>
              </>
            ) : (
              <span>Create Account</span>
            )}
          </button>
        </form>

        <div style={styles.footer}>
          <span>Already have an account? </span>
          <Link to="/login" style={styles.link}>
            Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}

const styles = {
  container: {
    minHeight: '80vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: '24px',
    fontFamily: 'system-ui, -apple-system, sans-serif',
  },
  card: {
    width: '100%',
    maxWidth: '440px',
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    border: '1px solid #e5e7eb',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)',
    padding: '32px',
  },
  header: {
    textAlign: 'center',
    marginBottom: '24px',
  },
  iconCircle: {
    width: '48px',
    height: '48px',
    borderRadius: '50%',
    backgroundColor: '#eff6ff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    margin: '0 auto 12px auto',
  },
  title: {
    fontSize: '20px',
    fontWeight: '700',
    color: '#111827',
    margin: '0 0 6px 0',
  },
  subtitle: {
    fontSize: '13px',
    color: '#6b7280',
    margin: 0,
  },
  errorBanner: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '10px 14px',
    backgroundColor: '#fef2f2',
    border: '1px solid #fee2e2',
    borderRadius: '8px',
    color: '#b91c1c',
    fontSize: '13px',
    marginBottom: '20px',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  formGroup: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  label: {
    fontSize: '13px',
    fontWeight: '500',
    color: '#374151',
  },
  inputWrapper: {
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
  },
  inputIcon: {
    position: 'absolute',
    left: '12px',
    color: '#9ca3af',
  },
  input: {
    width: '100%',
    padding: '10px 12px 10px 38px',
    borderRadius: '8px',
    border: '1px solid #d1d5db',
    fontSize: '14px',
    outline: 'none',
    boxSizing: 'border-box',
    transition: 'border-color 0.15s ease',
  },
  fieldError: {
    fontSize: '11px',
    color: '#ef4444',
  },
  submitBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    padding: '10px 16px',
    borderRadius: '8px',
    backgroundColor: '#2563eb',
    color: '#ffffff',
    fontSize: '14px',
    fontWeight: '600',
    border: 'none',
    cursor: 'pointer',
    marginTop: '8px',
    transition: 'background-color 0.15s ease',
  },
  footer: {
    textAlign: 'center',
    marginTop: '24px',
    fontSize: '13px',
    color: '#6b7280',
  },
  link: {
    color: '#2563eb',
    fontWeight: '600',
    textDecoration: 'none',
  },
};
