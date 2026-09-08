/**
 * ViewerPage.jsx
 * Split-screen: PDF viewer on the left, Q&A panel on the right.
 * Manages highlight state shared between the two sides.
 */
import { useState, useRef, useCallback } from 'react';
import PDFViewer from '../components/PDFViewer.jsx';
import QuestionPanel from '../components/QuestionPanel.jsx';

export default function ViewerPage({ uploadInfo, onBack }) {
  const [highlights, setHighlights] = useState([]);
  const [flashCitation, setFlashCitation] = useState(null);
  const pageRefs = useRef({});

  const handleFlash = useCallback((chunk_id) => {
    setFlashCitation(chunk_id);
    setTimeout(() => setFlashCitation(null), 1400);
  }, []);

  return (
    <div style={styles.root}>
      {/* Top bar */}
      <div style={styles.topBar}>
        <div style={styles.topLeft}>
          <button className="btn btn-sm" onClick={onBack} id="btn-back">
            ← Back
          </button>
          <div style={styles.docInfo}>
            <span style={styles.docName}>{uploadInfo.filename}</span>
            <span className="badge badge-blue">{uploadInfo.page_count} pages</span>
            {uploadInfo.metadata?.image_only_pages > 0 && (
              <span className="badge" style={{backgroundColor: 'var(--accent-orange)'}}>
                {uploadInfo.metadata.image_only_pages} scanned pages skipped
              </span>
            )}
            <span className="badge badge-green">{uploadInfo.chunk_count} chunks indexed</span>
          </div>
        </div>
        {uploadInfo.warning && (
          <span style={styles.warning}>⚠ {uploadInfo.warning}</span>
        )}
      </div>

      {/* Main split */}
      <div style={styles.split}>
        {/* Left: PDF */}
        <div style={styles.pdfCol}>
          <PDFViewer
            docId={uploadInfo.doc_id}
            highlights={highlights}
            flashCitation={flashCitation}
            pageRefs={pageRefs}
          />
        </div>

        {/* Divider */}
        <div style={styles.divider} />

        {/* Right: Q&A */}
        <div style={styles.qaCol}>
          <QuestionPanel
            docId={uploadInfo.doc_id}
            onCitations={setHighlights}
            onFlashCitation={handleFlash}
            pageRefs={pageRefs}
          />
        </div>
      </div>
    </div>
  );
}

const styles = {
  root: { height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  topBar: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '8px 16px', flexShrink: 0,
    background: 'var(--bg-800)', borderBottom: '1px solid var(--border)',
  },
  topLeft: { display: 'flex', alignItems: 'center', gap: 12 },
  docInfo: { display: 'flex', alignItems: 'center', gap: 8 },
  docName: { fontSize: 13, fontWeight: 600, color: 'var(--text-secondary)', maxWidth: 280, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  warning: { fontSize: 11, color: 'var(--accent-orange)' },
  split: { flex: 1, display: 'flex', overflow: 'hidden' },
  pdfCol: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', minWidth: 0 },
  divider: { width: 1, background: 'var(--border)', flexShrink: 0 },
  qaCol: { width: 400, flexShrink: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
};
