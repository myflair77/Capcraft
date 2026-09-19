const {readFileSync} = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const timers = [], animations = [], listeners = {};
const context = {window:{}, document:{hidden:false,
    addEventListener(name, callback) { listeners[name] = callback; },
    documentElement:{animate(frames, options) {
        const animation = {cancel() {this.cancelled=true;}, options};
        animations.push(animation); return animation;
    }}}, canvas:{contextContainer:{}, on(name, callback) {this.callback=callback;}},
    setTimeout(callback) {timers.push(callback); return timers.length;}};
vm.runInNewContext(readFileSync('presentation-refresh.js','utf8'), context);
context.window.installPresentationRefresh();
const refresh = context.window.capcraftPresentationRefresh;
context.window.installPresentationRefresh();
assert.equal(context.window.capcraftPresentationRefresh, refresh);
listeners.pointerup(); listeners.input(); refresh();
assert.equal(timers.length,1, 'coalesce burst');
timers.shift()();
assert.equal(animations[0].options.iterations,1);
assert.equal(animations[0].options.duration,180);
animations[0].onfinish();
assert.equal(timers.length,0,'no idle loop');
context.canvas.callback({ctx:{}});
assert.equal(timers.length,0,'ignore thumbnail renders');
context.canvas.callback({ctx:context.canvas.contextContainer});
assert.equal(timers.length,1,'refresh visible canvas');
timers.shift()();
context.document.hidden=true; refresh();
assert.equal(timers.length,0,'ignore hidden document');
console.log('PASS bounded presentation refresh: coalescing, idle, visible canvas, hidden document');
