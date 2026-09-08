/**
 * QuestionPanel.jsx
 * Right-side panel: API key, question input, streaming answer, citation chips.
 * Connects to /query SSE stream, parses token and citation events in real time.
 */
import { useState, useRef, useCallback } from 'react';

export default function QuestionPanel({ docId, onCitations, onFlashCitation, pageRefs }) {
  const [question, setQuestion] = useState('');
  const [answerSegments, setAnswerSegments] = useState([]);
  const [citations, setCitations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const abortRef = useRef(null);
  const hasAutoScrolledRef = useRef(false);

  const clearChat = useCallback(() => {
    if (abortRef.current) abortRef.current.abort();
    setError(null);
    setAnswerSegments([]);
    setCitations([]);
    setQuestion('');
    onCitations([]);
  }, [onCitations]);

  const askQuestion = useCallback(async () => {
    if (!question.trim() || !docId || loading) return;
    setError(null);
    setAnswerSegments([]);
    setCitations([]);
    onCitations([]);
    setLoading(true);
    hasAutoScrolledRef.current = false;

    // Cancel previous stream if any
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const url = `/query?doc_id=${encodeURIComponent(docId)}&question=${encodeURIComponent(question)}`;
      const res = await fetch(url, { signal: controller.signal });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Backend error ${res.status}: ${text}`);
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = '';

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });

        const lines = buf.split('\n\n');
        buf = lines.pop(); // keep incomplete chunk

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const event = JSON.parse(line.slice(6));
            handleEvent(event);
          } catch { /* malformed */ }
        }
      }
    } catch (e) {
      if (e.name !== 'AbortError') setError(e.message);
    } finally {
      setLoading(false);
    }

    function handleEvent(event) {
      if (event.type === 'token') {
        setAnswerSegments(prev => {
          const next = [...prev];
          if (next.length > 0 && next[next.length - 1].type === 'text') {
            next[next.length - 1] = {
              ...next[next.length - 1],
              content: next[next.length - 1].content + event.content
            };
          } else {
            next.push({ type: 'text', content: event.content });
          }
          return next;
        });
      } else if (event.type === 'citation') {
        const chunk_id = event.citation_id || event.chunk_id;
        const words = (event.words || []).map(w => ({ ...w, chunk_id }));
        const pages = [...new Set(words.map(w => w.page))].sort((a,b) => a-b);
        const isValid = pages.length > 0;
        
        setCitations(prev => {
          const next = [...prev, { chunk_id, pages, words, isValid }];
          onCitations(next.flatMap(c => c.words));
          
          // Auto-scroll to the very first valid citation automatically
          if (isValid && !hasAutoScrolledRef.current) {
            hasAutoScrolledRef.current = true;
            // Delay slightly to ensure PDF has rendered the new page layout
            setTimeout(() => {
              const el = pageRefs?.current?.[pages[0]];
              if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
              onFlashCitation(chunk_id);
            }, 300);
          }
          
          return next;
        });

        // Insert inline citation marker
        if (isValid) {
          setAnswerSegments(prev => [...prev, { type: 'cite', chunk_id }]);
        }
      } else if (event.type === 'error') {
        setError(event.content);
      }
    }
  }, [question, docId, loading, onCitations]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) askQuestion();
  };

  const scrollToCitation = (citation) => {
    onFlashCitation(citation.chunk_id);
    // Scroll to the first page of the citation
    const firstPage = citation.pages[0];
    const el = pageRefs?.current?.[firstPage];
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
  };

  return (
    <div style={styles.root}>
      <div style={styles.header}>
        <span style={styles.title}>Ask a Question</span>
        {docId && <span className="badge badge-green">Doc loaded</span>}
      </div>

      {/* Question */}
      <div style={styles.questionRow}>
        <textarea
          className="input"
          placeholder={docId ? 'Ask anything about the document… (Ctrl+Enter to send)' : 'Upload a PDF first'}
          value={question}
          onChange={e => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={!docId || loading}
          rows={3}
          style={{ resize: 'vertical', fontSize: 14 }}
          id="question-input"
        />
        <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
          <button
            className="btn btn-primary"
            onClick={askQuestion}
            disabled={!docId || !question.trim() || loading}
            id="btn-ask"
            style={{ flex: 1 }}
          >
            {loading ? <><span className="spinner" /> Thinking…</> : 'Ask'}
          </button>
          <button
            className="btn"
            onClick={clearChat}
            disabled={loading || (!question && answerSegments.length === 0)}
            title="Clear Chat"
            style={{ padding: '0 12px' }}
          >
            Clear
          </button>
        </div>
      </div>

      {error && (
        <div style={styles.errorBox}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {/* Citations */}
      {citations.length > 0 && (
        <div style={styles.citationsWrap}>
          <div style={styles.citLabel}>Sources</div>
          <div style={styles.chips}>
            {citations.map((c, i) => (
              <button
                key={i}
                className="btn btn-sm"
                style={c.isValid ? styles.chip : styles.chipInvalid}
                onClick={c.isValid ? () => scrollToCitation(c) : undefined}
                id={`cite-chip-${c.chunk_id}`}
                title={c.isValid ? `Pages ${c.pages.join(', ')}` : "Source mapping failed"}
                disabled={!c.isValid}
              >
                {c.isValid ? (c.pages.length > 1 ? `p.${c.pages[0]}-${c.pages[c.pages.length-1]}` : `p.${c.pages[0]}`) : "Unverified"}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Answer */}
      {(answerSegments.length > 0 || loading) && (
        <div style={styles.answerWrap} className="fade-in">
          <div style={styles.answerLabel}>Answer</div>
          <div style={styles.answerText}>
            {answerSegments.map((seg, i) => {
              if (seg.type === 'text') {
                const parts = seg.content.split(/(<think>|<\/think>)/g);
                let isThinking = false;
                return (
                  <span key={i}>
                    {parts.map((part, idx) => {
                      if (part === '<think>') { isThinking = true; return null; }
                      if (part === '</think>') { isThinking = false; return null; }
                      if (isThinking) {
                        return <span key={idx} style={{ color: 'var(--text-muted)', fontStyle: 'italic', fontSize: '0.9em', display: 'block', borderLeft: '2px solid var(--border)', paddingLeft: '8px', marginBottom: '8px', whiteSpace: 'pre-wrap' }}>{part}</span>;
                      }
                      return <span key={idx}>{part}</span>;
                    })}
                  </span>
                );
              } else if (seg.type === 'cite') {
                // Find citation index (1-based)
                const citIdx = citations.findIndex(c => c.chunk_id === seg.chunk_id);
                const num = citIdx !== -1 ? citIdx + 1 : '?';
                return (
                  <sup 
                    key={i} 
                    style={styles.inlineCite}
                    onClick={() => scrollToCitation(citations[citIdx])}
                    title="Click to view source"
                  >
                    [{num}]
                  </sup>
                );
              }
              return null;
            })}
            {answerSegments.length === 0 && !loading && <span style={{ color: 'var(--text-muted)' }}>…</span>}
            {loading && <span style={styles.cursor}>▌</span>}
          </div>
        </div>
      )}
    </div>
  );
}

const styles = {
  root: {
    display: 'flex', flexDirection: 'column', gap: 12,
    height: '100%', overflowY: 'auto', padding: 16,
    background: 'var(--bg-900)',
  },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  title: { fontSize: 15, fontWeight: 700 },
  questionRow: { display: 'flex', flexDirection: 'column' },
  errorBox: {
    background: 'rgba(240,71,71,0.08)', border: '1px solid rgba(240,71,71,0.25)',
    borderRadius: 'var(--radius-sm)', padding: '8px 12px',
    fontSize: 12, color: '#fca5a5',
  },
  citationsWrap: { display: 'flex', flexDirection: 'column', gap: 6 },
  citLabel: { fontSize: 9, fontWeight: 800, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)' },
  chips: { display: 'flex', flexWrap: 'wrap', gap: 5 },
  chip: {
    fontSize: 10, padding: '3px 9px',
    background: 'rgba(251,191,36,0.1)', borderColor: 'rgba(251,191,36,0.35)',
    color: '#fbbf24',
    cursor: 'pointer',
  },
  chipInvalid: {
    fontSize: 10, padding: '3px 9px',
    background: 'rgba(156,163,175,0.1)', borderColor: 'rgba(156,163,175,0.3)',
    color: '#9ca3af', textDecoration: 'line-through',
    cursor: 'not-allowed',
  },
  answerWrap: {
    flex: 1, display: 'flex', flexDirection: 'column', gap: 6,
    background: 'var(--bg-800)', borderRadius: 'var(--radius-md)',
    border: '1px solid var(--border)', padding: 14,
  },
  answerLabel: { fontSize: 9, fontWeight: 800, letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)' },
  answerText: { fontSize: 14, lineHeight: 1.75, color: 'var(--text-primary)', whiteSpace: 'pre-wrap' },
  inlineCite: { 
    color: 'var(--accent-blue)', cursor: 'pointer', fontWeight: 700, 
    padding: '0 2px', userSelect: 'none', transition: 'color 0.15s'
  },
  cursor: { animation: 'spin 0.8s steps(2) infinite', display: 'inline-block', marginLeft: 2, color: 'var(--accent-blue)' },
};
