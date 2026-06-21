'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  AlertTriangle,
  FileText,
  X,
  ChevronLeft,
  ChevronRight,
  ZoomIn,
  ZoomOut,
  Maximize2,
  Loader2,
  Search,
} from 'lucide-react';
import { fetchAuthenticatedBlob } from '@/shared/api/client';
import { Citation } from '@/shared/types';

interface PdfViewerProps {
  versionId: string;
  filename: string;
  citation?: Citation;
  onClose: () => void;
}

export function PdfViewer({ versionId, filename, citation, onClose }: PdfViewerProps) {
  const [pdfjs, setPdfjs] = useState<any>(null);
  const [pdfDoc, setPdfDoc] = useState<any>(null);
  const [pageNum, setPageNum] = useState<number>(1);
  const [numPages, setNumPages] = useState<number>(0);
  const [scale, setScale] = useState<number>(1.2);
  const [loading, setLoading] = useState<boolean>(true);
  const [searching, setSearching] = useState<boolean>(false);
  const [foundOnPage, setFoundOnPage] = useState<number | null>(null);
  const [error, setError] = useState<string>();

  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const renderTaskRef = useRef<any>(null);

  // 1. Dynamically import pdfjs-dist on client mount
  useEffect(() => {
    import('pdfjs-dist')
      .then((mod) => {
        mod.GlobalWorkerOptions.workerSrc = `https://unpkg.com/pdfjs-dist@${mod.version}/build/pdf.worker.min.mjs`;
        setPdfjs(mod);
      })
      .catch((err) => {
        console.error('Failed to load pdfjs-dist:', err);
        setError('Failed to initialize PDF renderer library.');
        setLoading(false);
      });
  }, []);

  // Search for quote across all pages — returns the first page number that contains it
  const findQuoteInDocument = useCallback(
    async (doc: any, quote: string): Promise<number | null> => {
      const normalized = quote.toLowerCase().replace(/\s+/g, ' ').trim();
      // Only search first 100 chars for speed (avoids huge substring joins)
      const searchSnippet = normalized.slice(0, 120);
      for (let p = 1; p <= doc.numPages; p++) {
        try {
          const page = await doc.getPage(p);
          const textContent = await page.getTextContent();
          const pageText = textContent.items
            .filter((item: any) => 'str' in item)
            .map((item: any) => item.str)
            .join(' ')
            .toLowerCase()
            .replace(/\s+/g, ' ');
          if (pageText.includes(searchSnippet)) {
            return p;
          }
        } catch {
          // skip unreadable page
        }
      }
      return null;
    },
    []
  );

  // 2. Fetch authenticated PDF blob and load document
  useEffect(() => {
    if (!pdfjs) return;

    let active = true;
    let createdUrl: string | undefined;

    setLoading(true);
    setError(undefined);
    setFoundOnPage(null);

    fetchAuthenticatedBlob(`/document-versions/${versionId}/content`)
      .then(async (blob) => {
        if (!active) return;
        createdUrl = URL.createObjectURL(blob);

        const loadingTask = pdfjs.getDocument({ url: createdUrl });
        const doc = await loadingTask.promise;

        if (!active) return;
        setPdfDoc(doc);
        setNumPages(doc.numPages);

        // If we have page_start from the DB, use it. Otherwise search.
        if (citation?.page_start) {
          const p = Math.min(Math.max(citation.page_start, 1), doc.numPages);
          setPageNum(p);
          setFoundOnPage(p);
          setLoading(false);
        } else if (citation?.quote) {
          setLoading(false);
          setSearching(true);
          findQuoteInDocument(doc, citation.quote).then((p) => {
            if (!active) return;
            setSearching(false);
            if (p) {
              setPageNum(p);
              setFoundOnPage(p);
            }
          });
        } else {
          setPageNum(1);
          setLoading(false);
        }
      })
      .catch((reason: unknown) => {
        if (active) {
          console.error('Error fetching PDF:', reason);
          setError(reason instanceof Error ? reason.message : 'Unable to load PDF');
          setLoading(false);
        }
      });

    return () => {
      active = false;
      if (createdUrl) URL.revokeObjectURL(createdUrl);
    };
  }, [versionId, pdfjs, citation, findQuoteInDocument]);

  // Highlight matching quote spans on the rendered canvas
  const drawHighlights = useCallback(
    async (page: any, viewport: any, context: CanvasRenderingContext2D, quote: string) => {
      const textContent = await page.getTextContent();
      const normalizedQuote = quote.toLowerCase().replace(/\s+/g, ' ').trim();

      const items = textContent.items.filter((item: any) => 'str' in item && item.str.trim());
      let fullPageText = '';
      const itemSpans: { start: number; end: number; item: any }[] = [];

      for (const item of items) {
        const start = fullPageText.length;
        fullPageText += item.str + ' ';
        itemSpans.push({ start, end: fullPageText.length, item });
      }

      const normalizedPage = fullPageText.toLowerCase().replace(/\s+/g, ' ');
      const matchStart = normalizedPage.indexOf(normalizedQuote.slice(0, 80));
      if (matchStart === -1) return;

      // Highlight all items whose text is a substring of the quote
      context.save();
      for (const span of itemSpans) {
        const spanText = span.item.str.toLowerCase().replace(/\s+/g, ' ').trim();
        if (spanText.length > 3 && normalizedQuote.includes(spanText)) {
          const tx: number = span.item.transform[4];
          const ty: number = span.item.transform[5];
          const [vx, vy] = viewport.convertToViewportPoint(tx, ty);
          const itemHeight: number = span.item.height || Math.abs(span.item.transform[3]) || 12;
          const itemWidth: number = span.item.width || 40;

          context.fillStyle = 'rgba(234, 179, 8, 0.28)';
          context.fillRect(vx, vy - itemHeight * 1.1, itemWidth, itemHeight * 1.3);
          context.strokeStyle = 'rgba(234, 179, 8, 0.55)';
          context.lineWidth = 1;
          context.strokeRect(vx, vy - itemHeight * 1.1, itemWidth, itemHeight * 1.3);
        }
      }
      context.restore();
    },
    []
  );

  // 3. Render page canvas
  const renderPage = useCallback(
    async (pageNumber: number, currentScale: number) => {
      if (!canvasRef.current || !pdfDoc) return;

      try {
        if (renderTaskRef.current) {
          renderTaskRef.current.cancel();
        }

        const page = await pdfDoc.getPage(pageNumber);
        const viewport = page.getViewport({ scale: currentScale });

        const canvas = canvasRef.current;
        const context = canvas.getContext('2d');
        if (!context) return;

        const dpr = window.devicePixelRatio || 1;
        canvas.width = viewport.width * dpr;
        canvas.height = viewport.height * dpr;
        canvas.style.width = `${viewport.width}px`;
        canvas.style.height = `${viewport.height}px`;

        context.scale(dpr, dpr);

        const renderTask = page.render({ canvasContext: context, viewport });
        renderTaskRef.current = renderTask;
        await renderTask.promise;
        renderTaskRef.current = null;

        // Draw highlights if this page contains the citation
        if (citation?.quote && pageNumber === foundOnPage) {
          await drawHighlights(page, viewport, context, citation.quote);
        }
      } catch (err: any) {
        if (err.name === 'RenderingCancelledException') return;
        console.error('Error rendering page:', err);
      }
    },
    [pdfDoc, citation, foundOnPage, drawHighlights]
  );

  useEffect(() => {
    if (pdfDoc && !loading) {
      renderPage(pageNum, scale);
    }
  }, [pdfDoc, pageNum, scale, loading, renderPage]);

  const handlePrevPage = () => { if (pageNum > 1) setPageNum(pageNum - 1); };
  const handleNextPage = () => { if (pageNum < numPages) setPageNum(pageNum + 1); };
  const handleZoomIn = () => setScale((p) => Math.min(p + 0.2, 3.0));
  const handleZoomOut = () => setScale((p) => Math.max(p - 0.2, 0.6));
  const handleFitPage = () => setScale(1.2);
  const handleJumpToCitation = () => { if (foundOnPage) setPageNum(foundOnPage); };

  // Page label shown in header
  const pageLabel = foundOnPage
    ? `Page ${foundOnPage} — citation highlighted`
    : searching
    ? 'Locating passage…'
    : 'Passage location unknown';

  return (
    <div
      className="fixed inset-0 z-[70] flex flex-col bg-zinc-950/97 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-label={`PDF viewer for ${filename}`}
    >
      {/* Header */}
      <header className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-800 bg-zinc-900/80 px-6 py-3 backdrop-blur-md shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-indigo-500/10 text-indigo-400 shrink-0">
            <FileText className="h-5 w-5" />
          </div>
          <div className="min-w-0">
            <h2 className="truncate text-sm font-bold text-zinc-100 max-w-[280px]">{filename}</h2>
            {citation && (
              <p className={`text-[11px] font-semibold ${foundOnPage ? 'text-amber-400' : searching ? 'text-indigo-400 animate-pulse' : 'text-zinc-500'}`}>
                {pageLabel}
              </p>
            )}
          </div>
        </div>

        {/* Toolbar Controls */}
        <div className="flex items-center flex-wrap gap-2 md:gap-3">
          {/* Jump to citation */}
          {foundOnPage && pageNum !== foundOnPage && (
            <button
              onClick={handleJumpToCitation}
              className="flex items-center gap-1.5 rounded-xl bg-amber-500/10 border border-amber-500/30 px-3 py-1.5 text-[11px] font-bold text-amber-300 hover:bg-amber-500/20 transition-all cursor-pointer"
            >
              <Search className="h-3 w-3" />
              Jump to citation
            </button>
          )}

          {!error && !loading && pdfDoc && (
            <>
              {/* Page Navigation */}
              <div className="flex items-center gap-1 rounded-xl bg-zinc-950 p-1 border border-zinc-800">
                <button
                  onClick={handlePrevPage}
                  disabled={pageNum <= 1}
                  className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 disabled:opacity-30 disabled:pointer-events-none transition-all"
                  title="Previous page"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <span className="text-[11px] font-bold text-zinc-400 px-2 min-w-[72px] text-center select-none">
                  {pageNum} / {numPages}
                </span>
                <button
                  onClick={handleNextPage}
                  disabled={pageNum >= numPages}
                  className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 disabled:opacity-30 disabled:pointer-events-none transition-all"
                  title="Next page"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>

              {/* Zoom Controls */}
              <div className="flex items-center gap-1 rounded-xl bg-zinc-950 p-1 border border-zinc-800">
                <button onClick={handleZoomOut} disabled={scale <= 0.6} className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 disabled:opacity-30 disabled:pointer-events-none transition-all" title="Zoom out">
                  <ZoomOut className="h-4 w-4" />
                </button>
                <span className="text-[11px] font-bold text-zinc-400 px-1.5 min-w-[45px] text-center select-none">
                  {Math.round(scale * 100)}%
                </span>
                <button onClick={handleZoomIn} disabled={scale >= 3.0} className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 disabled:opacity-30 disabled:pointer-events-none transition-all" title="Zoom in">
                  <ZoomIn className="h-4 w-4" />
                </button>
                <button onClick={handleFitPage} className="rounded-lg p-1.5 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-all border-l border-zinc-800 pl-2" title="Reset zoom">
                  <Maximize2 className="h-4 w-4" />
                </button>
              </div>
            </>
          )}

          <button
            onClick={onClose}
            aria-label="Close PDF viewer"
            className="rounded-xl p-2 text-zinc-400 hover:bg-zinc-800 hover:text-white transition-all cursor-pointer border border-zinc-800 hover:border-zinc-700 bg-zinc-900"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
      </header>

      {/* Citation Passage Panel */}
      {citation?.quote && (
        <aside className="border-b border-amber-900/30 bg-amber-950/10 px-6 py-2.5 shrink-0 flex items-start gap-2">
          <div className="mt-0.5 h-3 w-3 rounded-sm bg-amber-500/40 border border-amber-500/60 shrink-0" />
          <div className="min-w-0">
            <span className="text-[10px] font-bold text-amber-400/80 uppercase tracking-widest mr-2">
              Cited passage
              {citation.source_filename ? ` · ${citation.source_filename}` : ''}
            </span>
            <span className="text-[11px] text-zinc-300 italic leading-relaxed line-clamp-2">
              "{citation.quote}"
            </span>
          </div>
        </aside>
      )}

      {/* Searching overlay message */}
      {searching && (
        <div className="border-b border-indigo-900/30 bg-indigo-950/10 px-6 py-2 shrink-0 flex items-center gap-2">
          <Loader2 className="h-3.5 w-3.5 animate-spin text-indigo-400" />
          <span className="text-[11px] font-semibold text-indigo-300">
            Scanning document to locate the cited passage…
          </span>
        </div>
      )}

      {/* Main PDF Canvas Area */}
      <div className="min-h-0 flex-1 overflow-auto flex items-start justify-center p-6 bg-zinc-900/20">
        {error ? (
          <div className="flex flex-col items-center gap-3 text-center max-w-sm p-6 rounded-2xl bg-red-950/20 border border-red-900/50 my-auto">
            <AlertTriangle className="h-8 w-8 text-red-400" />
            <h3 className="text-sm font-bold text-red-200">Unable to load document</h3>
            <p className="text-xs text-red-400 leading-relaxed">{error}</p>
          </div>
        ) : loading ? (
          <div className="flex flex-col items-center gap-3 my-auto">
            <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
            <span className="text-xs font-semibold text-zinc-500 uppercase tracking-widest">Retrieving PDF…</span>
          </div>
        ) : (
          <div className="relative bg-zinc-950 rounded-2xl p-4 shadow-2xl border border-zinc-800/80">
            {/* Amber glow ring on citation page */}
            {pageNum === foundOnPage && (
              <div className="absolute -inset-px rounded-2xl border border-amber-500/30 pointer-events-none" />
            )}
            <canvas ref={canvasRef} className="mx-auto rounded-lg max-w-full" />
          </div>
        )}
      </div>
    </div>
  );
}
