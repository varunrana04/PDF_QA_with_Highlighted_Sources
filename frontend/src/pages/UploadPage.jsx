/**
 * UploadPage.jsx
 * Drag-and-drop or click-to-select PDF upload.
 * Shows progress and error states.
 */
import { useState, useRef, useCallback } from 'react';

export default function UploadPage({ onUploaded }) {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const upload = useCallback(async (file) => {
    if (!file || !file.name.toLowerCase().endsWith('.pdf')) {
      setError('Please select a valid PDF file.');
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      const res = await fetch('/upload', { method: 'POST', body: form });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `Upload failed (${res.status})`);
      onUploaded(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [onUploaded]);

  const onDrop = (e) => {
    e.preventDefault(); setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) upload(file);
  };

  return (
    <div style={styles.root}>
      {/* Background glow */}
      <div style={styles.glow} />

      <div style={styles.hero}>
        <div style={styles.eyebrow}>Sapien Robotics · Assignment 1</div>
        <h1 style={styles.title}><span className="hero-gradient">PDF Q&A</span></h1>
        <p style={styles.subtitle}>WITH HIGHLIGHTED SOURCES</p>
        <p style={styles.desc}>
          Upload a PDF, ask any question, and get a streamed answer<br />
          with the source passages highlighted directly on the document.
        </p>
      </div>

      {/* Drop zone */}
      <div
        style={{
          ...styles.dropZone,
          ...(dragging ? styles.dropZoneActive : {}),
        }}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        id="drop-zone"
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          style={{ display: 'none' }}
          onChange={e => { if (e.target.files[0]) upload(e.target.files[0]); }}
          id="file-input"
        />
        {loading ? (
          <div style={styles.loadingWrap}>
            <span className="spinner" style={{ width: 28, height: 28, borderWidth: 3 }} />
            <p style={styles.dropText}>Parsing + indexing…</p>
          </div>
        ) : (
          <>
            <div style={styles.uploadIcon}>⬆</div>
            <p style={styles.dropText}>
              {dragging ? 'Drop to upload' : 'Drag & drop a PDF or click to select'}
            </p>
            <p style={styles.dropHint}>Supports PDFs of 50+ pages · Max 50 MB</p>
          </>
        )}
      </div>

      {error && (
        <div style={styles.errorBox}>
          <strong>Upload failed:</strong> {error}
        </div>
      )}

      <div style={styles.features}>
        {[
          ['Exact highlights', 'Words highlighted directly on the PDF — not page numbers'],
          ['Multi-page citations', 'Answers spanning multiple pages are all highlighted'],
          ['Streaming answers', 'Response tokens appear in real time as Ollama generates'],
          ['Honest refusals', 'Says "not found" instead of guessing from outside the document'],
        ].map(([title, desc]) => (
          <div key={title} style={styles.feature}>
            <div style={styles.featureTitle}>{title}</div>
            <div style={styles.featureDesc}>{desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

const styles = {
  root: {
    minHeight: '100vh', display: 'flex', flexDirection: 'column',
    alignItems: 'center', justifyContent: 'center',
    padding: '60px 20px', gap: 28, position: 'relative', overflow: 'hidden',
  },
  glow: {
    position: 'absolute', top: '20%', left: '50%', transform: 'translate(-50%, -50%)',
    width: 600, height: 400,
    background: 'radial-gradient(ellipse, rgba(59,143,245,0.1) 0%, transparent 70%)',
    pointerEvents: 'none',
  },
  hero: { textAlign: 'center', maxWidth: 520, position: 'relative', zIndex: 1 },
  eyebrow: { fontSize: 10, fontWeight: 700, letterSpacing: '0.14em', textTransform: 'uppercase', color: 'var(--accent-blue)', marginBottom: 10, opacity: 0.8 },
  title: { fontSize: 72, fontWeight: 900, letterSpacing: '-0.04em', lineHeight: 1 },
  subtitle: { fontSize: 12, fontWeight: 700, color: 'var(--text-muted)', marginTop: 8, letterSpacing: '0.28em' },
  desc: { marginTop: 16, fontSize: 14, color: 'var(--text-secondary)', lineHeight: 1.8 },
  dropZone: {
    width: '100%', maxWidth: 480,
    border: '2px dashed var(--border-bright)',
    borderRadius: 'var(--radius-lg)', padding: '40px 24px',
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8,
    cursor: 'pointer', transition: 'border-color 0.2s, background 0.2s, box-shadow 0.2s',
    background: 'var(--bg-800)',
    position: 'relative', zIndex: 1,
  },
  dropZoneActive: {
    borderColor: 'var(--accent-blue)',
    background: 'rgba(59,143,245,0.06)',
    boxShadow: '0 0 30px rgba(59,143,245,0.15)',
  },
  uploadIcon: { fontSize: 32, color: 'var(--accent-blue)', marginBottom: 4 },
  dropText: { fontSize: 14, fontWeight: 600, color: 'var(--text-secondary)', margin: 0 },
  dropHint: { fontSize: 11, color: 'var(--text-muted)', margin: 0 },
  loadingWrap: { display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10 },
  errorBox: {
    background: 'rgba(240,71,71,0.08)', border: '1px solid rgba(240,71,71,0.25)',
    borderRadius: 'var(--radius-sm)', padding: '10px 16px',
    fontSize: 13, color: '#fca5a5', maxWidth: 480, width: '100%',
  },
  features: {
    display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10,
    maxWidth: 480, width: '100%', position: 'relative', zIndex: 1,
  },
  feature: {
    background: 'var(--bg-800)', border: '1px solid var(--border)',
    borderRadius: 'var(--radius-sm)', padding: '12px 14px',
  },
  featureTitle: { fontSize: 12, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 4 },
  featureDesc: { fontSize: 11, color: 'var(--text-muted)', lineHeight: 1.5 },
};
