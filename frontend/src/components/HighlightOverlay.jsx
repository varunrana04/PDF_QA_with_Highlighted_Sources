/**
 * HighlightOverlay.jsx
 * Renders amber SVG rectangles over the PDF canvas for cited passages.
 * Coordinates are normalised [0,1] from the backend — multiplied by canvas dims.
 * Flashing on citation click is driven by the `flashCitation` prop (chunk_id).
 */
import { useEffect, useRef } from 'react';

export default function HighlightOverlay({ width, height, highlights, flashCitation }) {
  const svgRef = useRef(null);

  // Group highlight words into contiguous horizontal runs per "line"
  // so we draw one rect per text line rather than per word
  const rects = buildRects(highlights, width, height);

  return (
    <svg
      ref={svgRef}
      style={{
        position: 'absolute', top: 0, left: 0,
        width, height,
        pointerEvents: 'none',
        overflow: 'visible',
        zIndex: 10,
      }}
      width={width}
      height={height}
    >
      {rects.map((r, i) => (
        <rect
          key={i}
          x={r.x}
          y={r.y}
          width={r.w}
          height={r.h}
          rx={2}
          fill="rgba(251,191,36,0.35)"
          stroke="rgba(251,191,36,0.6)"
          strokeWidth={0.8}
          className={flashCitation === r.chunk_id ? 'highlight-flash' : ''}
        />
      ))}
    </svg>
  );
}

function buildRects(highlights, width, height) {
  if (!highlights || highlights.length === 0) return [];

  const rects = [];
  // Group by approximate top position (same "line" = within 4px)
  const sorted = [...highlights].sort((a, b) => a.top - b.top || a.x0 - b.x0);
  let lineGroup = [];

  for (const word of sorted) {
    const px = {
      x0: word.x0 * width,
      top: word.top * height,
      x1: word.x1 * width,
      bottom: word.bottom * height,
      chunk_id: word.chunk_id,
    };

    if (lineGroup.length === 0) {
      lineGroup.push(px);
    } else {
      const last = lineGroup[lineGroup.length - 1];
      const sameLine = Math.abs(px.top - last.top) < 6;
      if (sameLine) {
        lineGroup.push(px);
      } else {
        rects.push(mergeGroup(lineGroup));
        lineGroup = [px];
      }
    }
  }
  if (lineGroup.length > 0) rects.push(mergeGroup(lineGroup));

  return rects;
}

function mergeGroup(group) {
  const x0 = Math.min(...group.map(g => g.x0));
  const x1 = Math.max(...group.map(g => g.x1));
  const top = Math.min(...group.map(g => g.top));
  const bottom = Math.max(...group.map(g => g.bottom));
  return {
    x: x0 - 2,
    y: top - 1,
    w: x1 - x0 + 4,
    h: bottom - top + 2,
    chunk_id: group[0].chunk_id,
  };
}
