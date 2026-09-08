/**
 * PDFViewer.jsx
 * Renders every page of a PDF using pdf.js onto individual <canvas> elements.
 * Positions a HighlightOverlay SVG on top of each page canvas.
 * Exposes ref handles for programmatic scroll-to-page.
 */
import { useEffect, useRef, useState } from 'react';
import * as pdfjsLib from 'pdfjs-dist/build/pdf.min.mjs';
import HighlightOverlay from './HighlightOverlay.jsx';

// Use the local worker stored in the public directory (renamed to avoid /pdf proxy)
pdfjsLib.GlobalWorkerOptions.workerSrc = '/worker.min.mjs';

export default function PDFViewer({ docId, highlights, flashCitation, pageRefs }) {
  const [pdfDoc, setPdfDoc] = useState(null);
  const [pageCount, setPageCount] = useState(0);
  const [scale, setScale] = useState(1.4);
  const [renderedPages, setRenderedPages] = useState(new Set());
  const [error, setError] = useState(null);
  const containerRef = useRef(null);

  // Load PDF from backend
  useEffect(() => {
    if (!docId) return;
    setPdfDoc(null);
    setRenderedPages(new Set());
    setError(null);

    try {
      pdfjsLib.getDocument({ url: `/pdf/${docId}` }).promise.then(doc => {
        setPdfDoc(doc);
        setPageCount(doc.numPages);
      }).catch(err => {
        setError("Async Error: " + (err?.message || err));
      });
    } catch (e) {
      setError("Sync Error: " + (e?.message || e));
    }
  }, [docId]);

  if (error) {
    return (
      <div style={{...styles.container, justifyContent: 'center'}}>
        <div style={{background: 'rgba(255,0,0,0.1)', color: '#ff6b6b', padding: 20, borderRadius: 8}}>
          <b>PDF Load Failed:</b><br/>{error}
        </div>
      </div>
    );
  }

  return (
    <div ref={containerRef} style={styles.container} id="pdf-container">
      {Array.from({ length: pageCount }, (_, i) => i + 1).map(pageNum => (
        <PageCanvas
          key={pageNum}
          pageNum={pageNum}
          pdfDoc={pdfDoc}
          scale={scale}
          highlights={(highlights || []).filter(h => h.page === pageNum)}
          flashCitation={flashCitation}
          pageRef={el => { if (pageRefs) pageRefs.current[pageNum] = el; }}
        />
      ))}
    </div>
  );
}

// ── Single page component ─────────────────────────────────────────────────────
function PageCanvas({ pageNum, pdfDoc, scale, highlights, flashCitation, pageRef }) {
  const canvasRef = useRef(null);
  const wrapRef = useRef(null);
  const [dims, setDims] = useState({ width: 0, height: 0 });
  const [isVisible, setIsVisible] = useState(false);
  const renderTaskRef = useRef(null);
  const renderedRef = useRef(false); // Track if we've already rendered this scale

  // Intersection Observer for Lazy Rendering
  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
        }
      },
      { rootMargin: '1000px 0px' } // Render 1000px ahead/behind
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!pdfDoc || !isVisible) return;
    
    pdfDoc.getPage(pageNum).then(page => {
      const vp = page.getViewport({ scale });
      const canvas = canvasRef.current;
      if (!canvas) return;
      
      canvas.width = vp.width;
      canvas.height = vp.height;
      setDims({ width: vp.width, height: vp.height });

      // Cancel any in-flight render
      if (renderTaskRef.current) renderTaskRef.current.cancel();

      const task = page.render({
        canvasContext: canvas.getContext('2d'),
        viewport: vp,
      });
      renderTaskRef.current = task;
      task.promise.then(() => {
        renderedRef.current = true;
      }).catch(e => {
        if (e?.name !== 'RenderingCancelledException') console.error(e);
      });
    });
  }, [pdfDoc, pageNum, scale, isVisible]);

  return (
    <div 
      ref={el => { wrapRef.current = el; if (pageRef) pageRef(el); }} 
      style={{...styles.pageWrap, minHeight: dims.height || 800}} // Reserve space to prevent scroll jumping
      data-page={pageNum}
    >
      <div style={styles.pageNum}>Page {pageNum}</div>
      <div style={{ position: 'relative', lineHeight: 0, width: dims.width || '100%', minHeight: dims.height || 800 }}>
        <canvas ref={canvasRef} style={styles.canvas} />
        {dims.width > 0 && (
          <HighlightOverlay
            width={dims.width}
            height={dims.height}
            highlights={highlights}
            flashCitation={flashCitation}
          />
        )}
      </div>
    </div>
  );
}

const styles = {
  container: {
    flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column',
    alignItems: 'center', gap: 16, padding: '16px 12px',
    background: 'var(--bg-950)',
  },
  pageWrap: {
    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
  },
  pageNum: {
    fontSize: 10, color: 'var(--text-muted)', fontWeight: 600,
    letterSpacing: '0.08em', textTransform: 'uppercase',
  },
  canvas: { display: 'block', borderRadius: 4, boxShadow: '0 4px 24px rgba(0,0,0,0.5)' },
};
