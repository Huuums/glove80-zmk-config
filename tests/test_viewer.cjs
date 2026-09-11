const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../preview/index.html'), 'utf8');
class Element {
  constructor() { this.children=[]; this.attrs={}; this.style={setProperty:()=>{}}; this.checked=false; this.events={}; }
  setAttribute(k,v) { this.attrs[k]=v; }
  append(...items) { this.children.push(...items); }
  replaceChildren() { this.children=[]; }
  addEventListener(k, fn) { this.events[k]=fn; }
}
async function test() {
  const ids={};
  for(const id of ['data','title','effective','keyboard','layers','detail','follow','connection','view-kind','view-name','modifier-state','last-input','input-meta','input-pad','clear-input','focus-status']) ids[id]=new Element();
  ids.effective.checked=true;
  ids.data.textContent=html.match(/<script id="data" type="application\/json">(.*?)<\/script>/s)[1];
  let response={connected:true,layer_count:32,layers:[0,31],transport:'bluetooth'};
  let nextPoll;
  const context=vm.createContext({
    document:{hasFocus:()=>true,addEventListener:()=>{},getElementById:id=>ids[id],createElement:()=>new Element(),createElementNS:()=>new Element()},
    window:{addEventListener:()=>{}},location:{protocol:'http:'}, AbortSignal,
    fetch:async()=>({ok:true,json:async()=>response}),
    setTimeout:fn=>{nextPoll=fn;}
  });
  vm.runInContext(html.match(/<script>(.*?)<\/script>/s)[1],context);
  await new Promise(setImmediate);
  assert.equal(ids.keyboard.children.length,80);
  assert.equal(ids.layers.children.length,32);
  assert.equal(ids.layers.children[31].attrs['aria-pressed'],true);
  assert.match(ids.connection.textContent,/Connected over bluetooth/);
  response={connected:true,layer_count:32,layers:[0,16],transport:'usb'};
  await nextPoll();
  assert.equal(ids.layers.children[31].attrs['aria-pressed'],false);
  assert.equal(ids.layers.children[16].attrs['aria-pressed'],true);
  response={connected:false,errors:{usb:'Unplugged'}};
  await nextPoll();
  assert.equal(ids.keyboard.style.opacity,'0.35');
  assert.match(ids.connection.textContent,/Unplugged/);
  response={connected:true,layer_count:2,layers:[0],transport:'usb'};
  await nextPoll();
  assert.match(ids.connection.textContent,/Layout mismatch/);
  response={connected:true,layer_count:32,layers:[0],transport:'bluetooth'};
  await nextPoll();
  assert.equal(ids.keyboard.style.opacity,'1');
  assert.equal(ids.layers.children[16].attrs['aria-pressed'],false);
  vm.runInContext(`liveLayers.clear();liveLayers.add(0);liveLayers.add(31);
    data.layers[31][0]={value:'&trans'};data.layers[0][0]={value:'&kp',params:[{value:'A'}]};
    if(resolve(0).layer!==0)throw Error('Transparent resolution');
    data.layers[31][0]={value:'&none'};
    if(resolve(0).layer!==31)throw Error('Blocked resolution');`,context);
  console.log('Viewer passed: live updates, layer 31, USB, stale status, mismatch, reconnect, transparency.');
}
test().catch(error=>{console.error(error);process.exitCode=1;});
