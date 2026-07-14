/** Test OCR on a single page using mupdf.js + tesseract.js.
 *  No system dependencies (both are WASM-based).
 */
const fs = require('fs');
const path = require('path');

const pdfPath = path.join(__dirname, '..', 'HIT教材 复变函数与积分变换同步学习(2).pdf');
const tmpDir = path.join(__dirname, '..', 'data', 'tmp');
if (!fs.existsSync(tmpDir)) fs.mkdirSync(tmpDir, { recursive: true });

async function test() {
  // Step 1: Render page 5 to PNG using mupdf
  console.log('Loading mupdf...');
  const mupdf = await import('mupdf');
  console.log(`mupdf version: ${mupdf.Document.version}`);

  console.log('Opening PDF...');
  const buf = fs.readFileSync(pdfPath);
  const doc = mupdf.Document.openDocument(buf, 'application/pdf');
  console.log(`Pages: ${doc.countPages()}`);

  // Render page 5 (0-indexed)
  const pageNum = 4;  // page 5
  console.log(`Rendering page ${pageNum + 1}...`);
  const page = doc.loadPage(pageNum);
  const bounds = page.getBounds();
  console.log(`Page bounds: ${JSON.stringify(bounds)}`);

  // Render at 200 DPI (zoom = 200/72 ≈ 2.78)
  const zoom = 2.78;
  const matrix = mupdf.Matrix.scale(zoom, zoom);
  const pixmap = page.toPixmap(matrix, mupdf.ColorSpace.DeviceRGB, false);
  console.log(`Pixmap: ${pixmap.getWidth()}x${pixmap.getHeight()}`);

  // Save as PNG
  const pngData = pixmap.asPNG();
  const pngPath = path.join(tmpDir, 'test_page5.png');
  fs.writeFileSync(pngPath, Buffer.from(pngData));
  console.log(`Saved PNG: ${pngPath} (${(pngData.length / 1024).toFixed(1)} KB)`);

  // Step 2: OCR
  console.log('Running OCR...');
  const Tesseract = (await import('tesseract.js')).default;
  const { data } = await Tesseract.recognize(pngPath, 'chi_sim+eng');
  console.log(`OCR confidence: ${data.confidence}%`);
  console.log(`\n=== OCR Result (first 1500 chars) ===`);
  console.log(data.text.slice(0, 1500));
  console.log(`\n=== Total OCR chars: ${data.text.length} ===`);

  // Save
  const outFile = path.join(tmpDir, 'test_page5.txt');
  fs.writeFileSync(outFile, data.text, 'utf-8');
  console.log(`Saved to ${outFile}`);
}

test().catch(e => { console.error(e); process.exit(1); });
