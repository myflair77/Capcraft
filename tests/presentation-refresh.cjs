const {readFileSync}=require('node:fs');
const vm=require('node:vm');
const assert=require('node:assert/strict');
const forbidden=()=>{throw Error('Presentation side effect forbidden');};
const context={window:{},document:{addEventListener:forbidden},
 canvas:{contextContainer:{getImageData:forbidden}},setInterval:forbidden};
vm.runInNewContext(readFileSync('presentation-refresh.js','utf8'),context);
context.window.installPresentationRefresh();
const first=context.window.capcraftPresentationRefresh;
context.window.installPresentationRefresh();assert.equal(first,context.window.capcraftPresentationRefresh);
for(let i=0;i<100;i++)first();
console.log('PASS no presentation timers or pixel readback');
