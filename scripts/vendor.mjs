import { mkdir, copyFile, writeFile, readFile } from 'node:fs/promises';
import { build } from 'esbuild';
import { fileURLToPath } from 'node:url';
process.chdir(fileURLToPath(new URL('..', import.meta.url)));
await mkdir('vendor/licenses', { recursive: true });
const files = {
    'fabric/dist/fabric.min.js': 'fabric.min.js',
    'jspdf/dist/jspdf.umd.min.js': 'jspdf.umd.min.js',
    'lucide/dist/umd/lucide.min.js': 'lucide.min.js',
    'dompurify/dist/purify.min.js': 'purify.min.js'
};
for (const [source, target] of Object.entries(files)) {
    await copyFile('node_modules/' + source, 'vendor/' + target);
}
const packages = ['fabric', 'jspdf', 'lucide', 'emoji-picker-element', 'emoji-picker-element-data', 'dompurify'];
const versions = {};
for (const name of packages) {
    versions[name] = JSON.parse(await readFile(`node_modules/${name}/package.json`, 'utf8')).version;
    await copyFile(`node_modules/${name}/LICENSE`, `vendor/licenses/${name}.txt`);
}
await build({ entryPoints: ['scripts/emoji-entry.js'], bundle: true,
    format: 'iife', minify: true, target: 'chrome100', outfile: 'vendor/emoji-picker.js', legalComments: 'eof' });
await writeFile('vendor/versions.json', JSON.stringify(versions, null, 2) + '\n');
console.log('Offline assets ready:', versions);
