/** Batch extract text from chapter handouts + exercise PDFs.
 *  Usage: node scripts/extract_handouts.cjs
 */
const fs = require('fs');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const DATA = path.join(ROOT, 'data', 'extracted');
if (!fs.existsSync(DATA)) fs.mkdirSync(DATA, { recursive: true });

const SOURCES = [
  { file: '复变/1.复数与复变函数_handout.pdf',      out: 'handout_ch1.txt', label: 'Ch1 复数与复变函数' },
  { file: '复变/2.解析函数_handout.pdf',            out: 'handout_ch2.txt', label: 'Ch2 解析函数' },
  { file: '复变/3.复变函数的积分_handout.pdf',      out: 'handout_ch3.txt', label: 'Ch3 复变函数的积分' },
  { file: '复变/4.级数_handout.pdf',                out: 'handout_ch4.txt', label: 'Ch4 级数' },
  { file: '复变/5.留数_handout.pdf',                out: 'handout_ch5.txt', label: 'Ch5 留数' },
  { file: '薪火（源：HIT外置学习资料库）-复变综合训练选择填空解析(1).pdf',
    out: 'exercises_xinhuo.txt', label: '薪火习题集' },
];

async function extractOne(mupdf, Tesseract, src) {
  const pdfPath = path.join(ROOT, src.file);
  if (!fs.existsSync(pdfPath)) { console.log(`  SKIP: not found`); return; }

  const buf = fs.readFileSync(pdfPath);
  const doc = mupdf.Document.openDocument(buf, 'application/pdf');
  const total = doc.countPages();
  console.log(`  ${total} pages`);

  const outPath = path.join(DATA, src.out);
  const progressFile = outPath + '.progress.json';
  let donePages = new Set();
  if (fs.existsSync(progressFile)) donePages = new Set(JSON.parse(fs.readFileSync(progressFile, 'utf-8')));

  const zoom = 2.0;
  let batch = [];
  for (let i = 0; i < total; i++) {
    const pageNum = i + 1;
    if (donePages.has(pageNum)) continue;
    try {
      const page = doc.loadPage(i);
      const pixmap = page.toPixmap(mupdf.Matrix.scale(zoom, zoom), mupdf.ColorSpace.DeviceRGB, false);
      const { data } = await Tesseract.recognize(Buffer.from(pixmap.asPNG()), 'chi_sim+eng');
      if (data.text.trim().length > 20) batch.push(`[Page ${pageNum}]\n${data.text.trim()}`);
      donePages.add(pageNum);
      if (batch.length >= 3) {
        fs.appendFileSync(outPath, batch.join('\n\n') + '\n\n', 'utf-8');
        fs.writeFileSync(progressFile, JSON.stringify([...donePages]), 'utf-8');
        batch = [];
      }
      if (pageNum % 10 === 0) console.log(`    ${pageNum}/${total}`);
    } catch (e) { console.error(`    Page ${pageNum} ERROR: ${e.message}`); }
  }
  if (batch.length > 0) fs.appendFileSync(outPath, batch.join('\n\n') + '\n\n', 'utf-8');
  fs.writeFileSync(progressFile, JSON.stringify([...donePages]), 'utf-8');
  const sz = fs.existsSync(outPath) ? fs.statSync(outPath).size : 0;
  console.log(`  DONE: ${donePages.size}/${total} pages, ${(sz/1024).toFixed(0)} KB`);
}

async function main() {
  console.log('Loading engines...');
  const mupdf = await import('mupdf');
  const Tesseract = (await import('tesseract.js')).default;
  for (const src of SOURCES) {
    console.log(`\n=== ${src.label} ===`);
    await extractOne(mupdf, Tesseract, src);
  }
  console.log('\n=== All done! ===');
}

main().catch(e => { console.error(e); process.exit(1); });
