/** Batch extract text from scanned PDF textbook using mupdf.js + tesseract.js.
 *  Features: resume on interrupt, incremental save, skip empty pages.
 *  Usage: node scripts/extract_pdf.cjs [startPage] [endPage]
 */
const fs = require('fs');
const path = require('path');

const pdfPath = path.join(__dirname, '..', 'HIT教材 复变函数与积分变换同步学习(2).pdf');
const outDir = path.join(__dirname, '..', 'data');
const outPath = path.join(outDir, 'hit_textbook_full.txt');
const PROGRESS_FILE = path.join(outDir, 'ocr_progress.json');

// Parse optional page range from CLI
const startPage = parseInt(process.argv[2]) || 1;
const endPage = parseInt(process.argv[3]) || Infinity;

if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });

async function main() {
  // Load mupdf
  console.log('Loading mupdf.js...');
  const mupdf = await import('mupdf');

  // Open PDF
  const buf = fs.readFileSync(pdfPath);
  const doc = mupdf.Document.openDocument(buf, 'application/pdf');
  const totalPages = doc.countPages();
  const actualEnd = Math.min(endPage, totalPages);
  console.log(`Total pages: ${totalPages}, processing ${startPage}-${actualEnd}`);

  // Load resume state
  let donePages = new Set();
  if (fs.existsSync(PROGRESS_FILE)) {
    donePages = new Set(JSON.parse(fs.readFileSync(PROGRESS_FILE, 'utf-8')));
    console.log(`Resume: ${donePages.size} pages already done`);
  }

  // Load existing text for append
  let existingText = '';
  if (fs.existsSync(outPath)) {
    existingText = fs.readFileSync(outPath, 'utf-8');
    console.log(`Existing text: ${existingText.length} chars`);
  }

  // Load tesseract
  console.log('Loading tesseract.js...');
  const Tesseract = (await import('tesseract.js')).default;

  const zoom = 2.78; // ~200 DPI
  const batchSize = 5; // save every N pages
  let batchBuffer = [];

  for (let i = startPage; i <= actualEnd; i++) {
    if (donePages.has(i)) continue;

    try {
      // Render page
      const page = doc.loadPage(i - 1);
      const matrix = mupdf.Matrix.scale(zoom, zoom);
      const pixmap = page.toPixmap(matrix, mupdf.ColorSpace.DeviceRGB, false);
      const pngData = pixmap.asPNG();

      // OCR
      const { data } = await Tesseract.recognize(Buffer.from(pngData), 'chi_sim+eng');
      const text = data.text.trim();

      if (text.length > 10) {
        batchBuffer.push(`[Page ${i}]\n${text}`);
        console.log(`  Page ${i}: ${text.length} chars (conf: ${data.confidence}%)`);
      } else {
        console.log(`  Page ${i}: SKIPPED (${text.length} chars, likely blank)`);
      }

      donePages.add(i);

      // Periodic save
      if (batchBuffer.length >= batchSize) {
        fs.appendFileSync(outPath, batchBuffer.join('\n\n') + '\n\n', 'utf-8');
        fs.writeFileSync(PROGRESS_FILE, JSON.stringify([...donePages]), 'utf-8');
        console.log(`  SAVED: ${[...donePages].length}/${actualEnd} pages`);
        batchBuffer = [];
      }
    } catch (e) {
      console.error(`  Page ${i} ERROR: ${e.message}`);
      // Save progress on error too
      if (batchBuffer.length > 0) {
        fs.appendFileSync(outPath, batchBuffer.join('\n\n') + '\n\n', 'utf-8');
        batchBuffer = [];
      }
      fs.writeFileSync(PROGRESS_FILE, JSON.stringify([...donePages]), 'utf-8');
    }
  }

  // Final flush
  if (batchBuffer.length > 0) {
    fs.appendFileSync(outPath, batchBuffer.join('\n\n') + '\n\n', 'utf-8');
  }
  fs.writeFileSync(PROGRESS_FILE, JSON.stringify([...donePages]), 'utf-8');

  const finalSize = fs.existsSync(outPath) ? fs.statSync(outPath).size : 0;
  console.log(`\nDone! ${donePages.size} pages processed, output: ${(finalSize / 1024).toFixed(0)} KB`);
}

main().catch(e => { console.error(e); process.exit(1); });
