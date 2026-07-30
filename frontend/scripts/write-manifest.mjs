// TICKET-0055 BRIEF-0055-a/c: canonical source-hash algorithm, implemented
// identically here and in tooling/verify/checks/frontend_build_fresh.py.
// SOURCE SET: every file under frontend/src/ at any depth, plus exactly
// frontend/package.json, frontend/package-lock.json, frontend/vite.config.js,
// frontend/index.html. PER-FILE: sha256 of raw bytes, lowercase hex.
// CANONICAL STRING: sort by relpath (byte-wise ascending, POSIX-separated),
// append "<relpath>\n<filehash>\n" per file, concatenate with no separator.
// SOURCE HASH: sha256 of the canonical string (UTF-8), lowercase hex.
import { createHash } from 'node:crypto';
import { readFileSync, writeFileSync, mkdirSync, readdirSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, '..');
const repoRoot = path.resolve(frontendRoot, '..');

function walk(dir, out) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(full, out);
    } else if (entry.isFile()) {
      out.push(full);
    }
  }
}

const absoluteFiles = [];
walk(path.join(frontendRoot, 'src'), absoluteFiles);
for (const rel of ['package.json', 'package-lock.json', 'vite.config.js', 'index.html']) {
  absoluteFiles.push(path.join(frontendRoot, rel));
}

const relFiles = absoluteFiles
  .map((abs) => path.relative(repoRoot, abs).split(path.sep).join('/'))
  .sort();

let canonical = '';
for (const rel of relFiles) {
  const bytes = readFileSync(path.join(repoRoot, rel));
  const fileHash = createHash('sha256').update(bytes).digest('hex');
  canonical += `${rel}\n${fileHash}\n`;
}

const sourceHash = createHash('sha256').update(Buffer.from(canonical, 'utf8')).digest('hex');
const builtAt = new Date().toISOString();

const outDir = path.join(repoRoot, 'src', 'world_engine', 'cockpit', 'static');
mkdirSync(outDir, { recursive: true });
writeFileSync(
  path.join(outDir, '.build-manifest.json'),
  `{ "source_hash": "${sourceHash}", "built_at": "${builtAt}" }\n`,
);
