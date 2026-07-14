/** Extract text from HIT Complex Analysis PDF textbook. */
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const pdfPath = path.join(__dirname, '..', 'HIT教材 复变函数与积分变换同步学习(2).pdf');

async function main() {
  const pdfParse = (await import('pdf-parse')).default;
  const dataBuffer = fs.readFileSync(pdfPath);

  console.log(`Reading: ${pdfPath}`);
  console.log(`File size: ${(dataBuffer.length / 1024 / 1024).toFixed(1)} MB`);

  const data = await pdfParse(dataBuffer);
  console.log(`Total pages: ${data.numpages}`);
  console.log(`Total chars: ${data.text.length}`);
  console.log(`\n=== Info ===`);
  console.log(JSON.stringify(data.info, null, 2));
  console.log(`\n=== First 5000 chars ===`);
  console.log(data.text.slice(0, 5000));

  // Save full text to file
  const outPath = path.join(__dirname, '..', 'data', 'hit_textbook_full.txt');
  const outDir = path.dirname(outPath);
  if (!fs.existsSync(outDir)) fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(outPath, data.text, 'utf-8');
  console.log(`\nFull text saved to: ${outPath} (${(data.text.length / 1024).toFixed(0)} KB)`);
}

main().catch(err => { console.error(err); process.exit(1); });
