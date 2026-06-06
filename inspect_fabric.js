const fs = require('fs');
const code = fs.readFileSync('fabric.min.js', 'utf8');
const vm = require('vm');
const sandbox = { window: {}, document: { createElement: () => ({ getContext: () => ({}) }) }, navigator: { userAgent: '' } };
vm.createContext(sandbox);
vm.runInContext(code, sandbox);
const fabric = sandbox.fabric || sandbox.window.fabric;
console.log(Object.keys(fabric.controlsUtils));
