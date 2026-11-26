const fs=require('fs');
let src=fs.readFileSync(__dirname+'/check.js','utf8')
 .replace('var state=','var state=globalThis.__state=')
 .replace('setTimeout(function(){computeSweep(p)},30);','')
 .replace(/init\(\);\s*\}\)\(\);\s*$/,"globalThis.__sim=simulate;globalThis.__sweep=computeSweep;\n})();");
if(!src.includes('__sim'))throw new Error('patch failed');
const vals={K:5,R:30,E:3,lr:0.1,het:0.8,sigma:0.2};
const cache={};
global.document={querySelector(sel){
  if(!cache[sel]){const m=sel.match(/^#c-(\w+)$/);
    cache[sel]={get value(){return m?String(vals[m[1]]):'0'},set value(v){},textContent:'',innerHTML:'',addEventListener(){},max:0,clientWidth:600};}
  return cache[sel];}};
global.window={addEventListener(){}};
(0,eval)(src);
const S=globalThis.__state;
// dummy controls so renderers don't crash: build cache entries lazily (done by querySelector)
function run(cfg,seed){
  Object.assign(vals,{K:5,R:30,E:3,lr:0.1,het:0.8,sigma:0.2},cfg);
  S.seed=seed;S.round=30;S.roundFollowsEnd=true;
  globalThis.__sim();
  const f=S.fed,last=f[f.length-1],la=S.locals.map(l=>l.auc);
  return {fed:last.auc,acc:last.acc,pooled:S.centralAuc,local:la.reduce((a,b)=>a+b,0)/la.length,
    localMin:Math.min(...la),curve:f.map(x=>x.auc),gains:la.map(a=>last.auc-a)};
}
const mean=a=>a.reduce((x,y)=>x+y,0)/a.length, sd=a=>{const m=mean(a);return Math.sqrt(mean(a.map(x=>(x-m)**2)))};
const r3=v=>Math.round(v*1000)/1000;
const seeds=[2024,1,2,3,4,5,6,7,8,9];
const out={};
// A) default config over seeds
let A=seeds.map(s=>run({},s));
out.A={fed:[r3(mean(A.map(x=>x.fed))),r3(sd(A.map(x=>x.fed)))],pooled:[r3(mean(A.map(x=>x.pooled))),r3(sd(A.map(x=>x.pooled)))],
 local:[r3(mean(A.map(x=>x.local))),r3(sd(A.map(x=>x.local)))],
 diff:[r3(mean(A.map(x=>x.fed-x.pooled))),r3(sd(A.map(x=>x.fed-x.pooled)))],
 gain:[r3(mean(A.map(x=>x.fed-x.local))),r3(sd(A.map(x=>x.fed-x.local)))],
 acc:r3(mean(A.map(x=>x.acc))),
 fedBeatsLocal:A.filter(x=>x.fed>x.local).length,
 perSeed:A.map(x=>[r3(x.fed),r3(x.pooled),r3(x.local)])};
// curve mean over seeds
out.curve=[0,1,2,3,5,8,10,15,20,25,30].map(r=>[r,r3(mean(A.map(x=>x.curve[r])))]);
// B) hospitals
out.K=[3,5,7,10].map(K=>{const R=seeds.map(s=>run({K},s));return {K,fed:r3(mean(R.map(x=>x.fed))),pooled:r3(mean(R.map(x=>x.pooled))),local:r3(mean(R.map(x=>x.local))),gain:r3(mean(R.map(x=>x.fed-x.local)))}});
// C) local epochs
out.E=[1,3,8].map(E=>{const R=seeds.map(s=>run({E},s));
 const reach=R.map(x=>{const t=x.pooled-0.005;const i=x.curve.findIndex(v=>v>=t);return i<0?31:i});
 return {E,fed:r3(mean(R.map(x=>x.fed))),pooled:r3(mean(R.map(x=>x.pooled))),roundsToReach:Math.round(mean(reach)*10)/10}});
// D) heterogeneity
out.het=[0,0.4,0.8,1.2,1.5].map(h=>{const R=seeds.map(s=>run({het:h},s));return {het:h,fed:r3(mean(R.map(x=>x.fed))),pooled:r3(mean(R.map(x=>x.pooled))),local:r3(mean(R.map(x=>x.local))),minLocal:r3(mean(R.map(x=>x.localMin))),diff:r3(mean(R.map(x=>x.fed-x.pooled)))}});
// E) sigma sweep over 5 seeds via computeSweep
out.sig=[];
const sw={0:[],0.25:[],0.5:[],1:[],1.5:[]};
for(const s of seeds.slice(0,5)){
  run({sigma:0.2},s);
  const p=S.params;
  // replicate computeSweep without the stale-check
  [0,0.25,0.5,1,1.5].forEach(sg=>{ /* use computeSweep's logic via direct call */ });
  globalThis.__sweep(p);
  S.sweep.forEach(o=>sw[o.sigma].push(o.auc));
  var base=null;
}
out.sig=Object.keys(sw).map(k=>({sigma:+k,auc:r3(mean(sw[k])),sd:r3(sd(sw[k]))}));
console.log(JSON.stringify(out));
