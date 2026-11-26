
(function(){
'use strict';
var D=8, CLIP=1.0, BATCH=32;
var FEATS=[
 {k:'preg',name:'Pregnancies',mu:3.8,sd:3.3,min:0,max:15,step:1,def:3,unit:''},
 {k:'glu',name:'Glucose',mu:121,sd:31,min:60,max:220,step:1,def:120,unit:'mg/dL'},
 {k:'bp',name:'Blood pressure',mu:69,sd:19,min:40,max:120,step:1,def:70,unit:'mm Hg'},
 {k:'skin',name:'Skin thickness',mu:21,sd:16,min:0,max:60,step:1,def:20,unit:'mm'},
 {k:'ins',name:'Insulin',mu:80,sd:115,min:0,max:400,step:5,def:80,unit:'µU/mL'},
 {k:'bmi',name:'BMI',mu:32,sd:7.9,min:16,max:60,step:0.5,def:32,unit:'kg/m²'},
 {k:'ped',name:'Pedigree function',mu:0.47,sd:0.33,min:0.08,max:2.4,step:0.01,def:0.47,unit:''},
 {k:'age',name:'Age',mu:33,sd:11.8,min:21,max:80,step:1,def:33,unit:'yr'}
];
var TRUE_W=[0.35,1.25,0.08,0.05,0.2,0.7,0.4,0.45], TRUE_B=-0.85;
var SITES=[['Site A','Urban teaching hospital'],['Site B','Regional district hospital'],['Site C','Diabetes referral centre'],['Site D','Rural primary care network'],['Site E','Private multispecialty hospital'],['Site F','Community health centre'],['Site G','Women and children hospital'],['Site H','Geriatric care hospital'],['Site I','Occupational health clinic'],['Site J','Mission hospital']];
var CTL=[
 {id:'K',label:'Hospitals',min:3,max:10,step:1,val:5,fmt:function(v){return String(v)},hint:'Number of sites in the network.'},
 {id:'R',label:'Communication rounds',min:5,max:60,step:1,val:30,fmt:function(v){return String(v)},hint:'How many times weights are exchanged.'},
 {id:'E',label:'Local epochs per round',min:1,max:8,step:1,val:3,fmt:function(v){return String(v)},hint:'Passes over local data before each upload.'},
 {id:'lr',label:'Learning rate',min:0.01,max:0.3,step:0.01,val:0.1,fmt:function(v){return v.toFixed(2)},hint:'Step size for local training.'},
 {id:'het',label:'Case-mix difference',min:0,max:1.5,step:0.05,val:0.8,fmt:function(v){return v.toFixed(2)},hint:'0 means identical patients everywhere. Higher means sites differ in age, BMI, glucose and baseline risk.'},
 {id:'sigma',label:'Privacy noise (σ)',min:0,max:1.5,step:0.05,val:0.2,fmt:function(v){return v.toFixed(2)},hint:'Clip each update to norm 1 and add Gaussian noise. Zero turns both off.'}
];
var $=function(s){return document.querySelector(s)};
var f2=function(v){return v.toFixed(2)}, f3=function(v){return v.toFixed(3)};
var state={seed:2024,round:30,fed:[],hs:[],locals:[],central:null,sweep:null,N:0,params:null};

function rng(seed){var a=seed>>>0;return function(){a|=0;a=a+0x6D2B79F5|0;var t=Math.imul(a^a>>>15,1|a);t=t+Math.imul(t^t>>>7,61|t)^t;return((t^t>>>14)>>>0)/4294967296;}}
function gauss(r){var u=0,v;while(!u)u=r();v=r();return Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*v);}
function sig(x){return 1/(1+Math.exp(-x));}
function clampz(z){return Math.max(-3,Math.min(3.5,z));}

function makeHospitals(K,het,seed){
  var r=rng(seed*7919+13),hs=[];
  for(var k=0;k<K;k++){
    var shift=[0,0,0,0,0,0,0,0];
    shift[7]=het*gauss(r)*0.8;
    shift[5]=het*gauss(r)*0.6;
    shift[1]=het*gauss(r)*0.4;
    hs.push({id:k,n:Math.round(140+r()*420),shift:shift,b:het*gauss(r)*0.7});
  }
  return hs;
}
function sample(h,n,r){
  var X=[],y=[];
  for(var i=0;i<n;i++){
    var age=gauss(r)+h.shift[7], bmi=gauss(r)+h.shift[5], z=new Array(D);
    z[7]=age; z[5]=bmi;
    z[0]=0.55*age+0.83*gauss(r);
    z[3]=0.5*bmi+0.87*gauss(r);
    z[1]=0.25*bmi+0.97*gauss(r)+h.shift[1];
    z[2]=0.2*age+0.2*bmi+0.95*gauss(r);
    z[4]=0.3*z[1]+0.95*gauss(r);
    z[6]=gauss(r);
    var s=TRUE_B+h.b;
    for(var j=0;j<D;j++){z[j]=clampz(z[j]);s+=TRUE_W[j]*z[j];}
    y.push(r()<sig(s)?1:0); X.push(z);
  }
  return {X:X,y:y};
}
function raw(w,x){var s=w[D];for(var j=0;j<D;j++)s+=w[j]*x[j];return s;}
function sgd(w0,data,epochs,lr,rand){
  var w=w0.slice(),n=data.y.length,idx=[],i,j;
  for(i=0;i<n;i++)idx.push(i);
  for(var e=0;e<epochs;e++){
    for(i=n-1;i>0;i--){j=Math.floor(rand()*(i+1));var t=idx[i];idx[i]=idx[j];idx[j]=t;}
    for(var s=0;s<n;s+=BATCH){
      var g=new Array(D+1).fill(0),m=Math.min(BATCH,n-s);
      for(var q=0;q<m;q++){
        var ii=idx[s+q],x=data.X[ii],err=sig(raw(w,x))-data.y[ii];
        for(j=0;j<D;j++)g[j]+=err*x[j];
        g[D]+=err;
      }
      for(j=0;j<=D;j++)w[j]-=lr*(g[j]/m+(j<D?1e-3*w[j]:0));
    }
  }
  return w;
}
function auc(w,T){
  var n=T.y.length,sc=new Array(n),i;
  for(i=0;i<n;i++)sc[i]=raw(w,T.X[i]);
  var idx=[];for(i=0;i<n;i++)idx.push(i);
  idx.sort(function(a,b){return sc[a]-sc[b]});
  if(sc[idx[0]]===sc[idx[n-1]])return 0.5;
  var rs=0,pos=0;
  for(i=0;i<n;i++){if(T.y[idx[i]]===1){rs+=i+1;pos++;}}
  var neg=n-pos;
  return (rs-pos*(pos+1)/2)/(pos*neg);
}
function acc(w,T){var c=0;for(var i=0;i<T.y.length;i++){if((raw(w,T.X[i])>0?1:0)===T.y[i])c++;}return c/T.y.length;}
function norm(v){var s=0;for(var i=0;i<v.length;i++)s+=v[i]*v[i];return Math.sqrt(s);}

function runFed(hs,datas,T,p,sigma,salt,keepNorms){
  var rand=rng(p.seed*31+salt),N=state.N,w=new Array(D+1).fill(0),hist=[],r,k,j;
  hist.push({w:w.slice(),auc:0.5,acc:acc(w,T),norms:hs.map(function(){return 0})});
  for(r=1;r<=p.R;r++){
    var agg=new Array(D+1).fill(0),norms=[];
    for(k=0;k<hs.length;k++){
      var wk=sgd(w,datas[k],p.E,p.lr,rand),d=new Array(D+1);
      for(j=0;j<=D;j++)d[j]=wk[j]-w[j];
      var nr=norm(d);norms.push(nr);
      var f=sigma>0?Math.min(1,CLIP/(nr||1)):1,wt=hs[k].n/N;
      for(j=0;j<=D;j++)agg[j]+=wt*f*d[j];
    }
    if(sigma>0){for(j=0;j<=D;j++)agg[j]+=gauss(rand)*sigma*CLIP/hs.length;}
    for(j=0;j<=D;j++)w[j]+=agg[j];
    hist.push({w:w.slice(),auc:auc(w,T),acc:acc(w,T),norms:norms});
  }
  return hist;
}

function readParams(){
  var p={seed:state.seed};
  CTL.forEach(function(c){p[c.id]=parseFloat($('#c-'+c.id).value);});
  return p;
}
function simulate(){
  var p=readParams();state.params=p;
  var hs=makeHospitals(p.K,p.het,p.seed),datas=[],N=0,k;
  for(k=0;k<hs.length;k++){datas.push(sample(hs[k],hs[k].n,rng(p.seed*101+k*17+5)));N+=hs[k].n;}
  state.N=N;state.hs=hs;state.datas=datas;
  var T={X:[],y:[]},tr=rng(p.seed*977+3);
  for(k=0;k<hs.length;k++){
    var m=Math.round(1500*hs[k].n/N),t=sample(hs[k],m,tr);
    T.X=T.X.concat(t.X);T.y=T.y.concat(t.y);
  }
  state.T=T;
  var pooled={X:[],y:[]};
  for(k=0;k<hs.length;k++){pooled.X=pooled.X.concat(datas[k].X);pooled.y=pooled.y.concat(datas[k].y);}
  var z=new Array(D+1).fill(0),br=rng(p.seed*53+9);
  state.central=sgd(z,pooled,80,p.lr,br);
  state.centralAuc=auc(state.central,T);
  state.locals=hs.map(function(h,i){
    var w=sgd(z,datas[i],80,p.lr,rng(p.seed*67+i));
    return {w:w,auc:auc(w,T)};
  });
  state.fed=runFed(hs,datas,T,p,p.sigma,1,true);
  state.round=Math.min(state.round,p.R);
  if(state.round===0||state.roundFollowsEnd)state.round=p.R;
  var rs=$('#round');rs.max=p.R;rs.value=state.round;
  state.sweep=null;
  $('#seedlabel').textContent='Cohort '+p.seed;
  renderAll();
  setTimeout(function(){computeSweep(p)},30);
}
function computeSweep(p){
  var sigmas=[0,0.25,0.5,1,1.5],out=[];
  sigmas.forEach(function(s){
    var tot=0;
    for(var rep=0;rep<3;rep++){
      var h=runFed(state.hs,state.datas,state.T,p,s,100+rep*7,false);
      tot+=h[h.length-1].auc;
    }
    out.push({sigma:s,auc:tot/3});
  });
  if(state.params===p){state.sweep=out;renderSweep();}
}

/* ---------- rendering ---------- */
function renderResults(){
  var fed=state.fed[state.fed.length-1],K=state.hs.length,R=state.params.R;
  var la=state.locals.map(function(l){return l.auc}),mean=la.reduce(function(a,b){return a+b},0)/la.length;
  var vals=K*R*(D+1);
  $('#results').innerHTML=
   '<div class="stat fed"><span class="lbl">Federated model AUC</span><span class="num">'+f3(fed.auc)+'</span><span class="sub">after '+R+' rounds, accuracy '+Math.round(fed.acc*100)+'%</span></div>'+
   '<div class="stat"><span class="lbl">Pooled records AUC</span><span class="num">'+f3(state.centralAuc)+'</span><span class="sub">upper bound, needs data sharing</span></div>'+
   '<div class="stat"><span class="lbl">Single hospital AUC</span><span class="num">'+f3(mean)+'</span><span class="sub">average of '+K+' sites alone</span></div>'+
   '<div class="stat"><span class="lbl">Patient records shared</span><span class="num">0</span><span class="sub">'+vals.toLocaleString()+' weight values uploaded in total</span></div>';
}
function renderControls(){
  var h='';
  CTL.forEach(function(c){
    h+='<div class="ctl"><div class="row"><label for="c-'+c.id+'">'+c.label+'</label><output id="o-'+c.id+'" for="c-'+c.id+'">'+c.fmt(c.val)+'</output></div>'+
       '<input type="range" id="c-'+c.id+'" min="'+c.min+'" max="'+c.max+'" step="'+c.step+'" value="'+c.val+'"><span class="hint">'+c.hint+'</span></div>';
  });
  $('#controls').innerHTML=h;
}
function yRange(vals){
  var mn=Math.min.apply(null,vals),mx=Math.max.apply(null,vals);
  var lo=Math.max(0.5,Math.floor((mn-0.02)*20)/20),hi=Math.min(1,Math.ceil((mx+0.01)*20)/20);
  if(hi-lo<0.1)hi=Math.min(1,lo+0.1);
  return [lo,hi];
}
function renderConv(){
  var el=$('#conv'),W=Math.max(300,el.clientWidth||600),H=W<520?240:300,m={l:46,r:14,t:12,b:36};
  var fed=state.fed,R=fed.length-1,la=state.locals.map(function(l){return l.auc});
  var lmin=Math.min.apply(null,la),lmax=Math.max.apply(null,la),lmean=la.reduce(function(a,b){return a+b},0)/la.length;
  var all=fed.map(function(p){return p.auc}).slice(1).concat(la,[state.centralAuc]);
  var yr=yRange(all),y0=yr[0],y1=yr[1];
  var X=function(r){return m.l+(W-m.l-m.r)*r/R},Y=function(v){return H-m.b-(H-m.t-m.b)*(v-y0)/(y1-y0)};
  var step=(y1-y0)>0.3?0.1:0.05,s='<svg viewBox="0 0 '+W+' '+H+'" width="'+W+'" height="'+H+'" role="img" aria-label="AUC by communication round for the federated model, pooled data and single hospitals">';
  for(var v=y0;v<=y1+1e-9;v+=step){
    s+='<line class="gl" x1="'+m.l+'" x2="'+(W-m.r)+'" y1="'+Y(v).toFixed(1)+'" y2="'+Y(v).toFixed(1)+'"/><text class="axt" x="'+(m.l-8)+'" y="'+(Y(v)+4).toFixed(1)+'" text-anchor="end">'+v.toFixed(2)+'</text>';
  }
  var xs=R<=10?1:R<=30?5:10;
  for(var r=0;r<=R;r+=xs){
    s+='<text class="axt" x="'+X(r).toFixed(1)+'" y="'+(H-m.b+16)+'" text-anchor="middle">'+r+'</text>';
  }
  s+='<text class="axl" x="'+((m.l+W-m.r)/2)+'" y="'+(H-4)+'" text-anchor="middle">Communication round</text>';
  s+='<rect x="'+m.l+'" y="'+Y(lmax).toFixed(1)+'" width="'+(W-m.l-m.r)+'" height="'+Math.max(1,Y(lmin)-Y(lmax)).toFixed(1)+'" fill="var(--muted)" opacity="0.18"/>';
  s+='<line x1="'+m.l+'" x2="'+(W-m.r)+'" y1="'+Y(lmean).toFixed(1)+'" y2="'+Y(lmean).toFixed(1)+'" stroke="var(--muted)" stroke-width="2" stroke-dasharray="5 4"/>';
  s+='<line x1="'+m.l+'" x2="'+(W-m.r)+'" y1="'+Y(state.centralAuc).toFixed(1)+'" y2="'+Y(state.centralAuc).toFixed(1)+'" stroke="var(--fg)" stroke-width="2" stroke-dasharray="6 4"/>';
  var d='';fed.forEach(function(p,i){d+=(i?'L':'M')+X(i).toFixed(1)+' '+Y(Math.max(y0,p.auc)).toFixed(1)});
  s+='<path d="'+d+'" fill="none" stroke="var(--accent)" stroke-width="3" stroke-linejoin="round" stroke-linecap="round"/>';
  var sr=state.round;
  s+='<line x1="'+X(sr).toFixed(1)+'" x2="'+X(sr).toFixed(1)+'" y1="'+m.t+'" y2="'+(H-m.b)+'" stroke="var(--accent)" stroke-width="1" stroke-dasharray="2 3"/>';
  s+='<circle cx="'+X(sr).toFixed(1)+'" cy="'+Y(Math.max(y0,fed[sr].auc)).toFixed(1)+'" r="5" fill="var(--accent)" stroke="var(--surface)" stroke-width="2"/>';
  s+='</svg>';
  el.innerHTML=s;
  el._geo={l:m.l,r:W-m.r,R:R};
}
function renderSites(){
  var sr=state.round,fed=state.fed[state.fed.length-1],h='<thead><tr><th>Hospital</th><th>Patients</th><th>Diabetic</th><th>Weight</th><th>Single-site AUC</th><th>Gain from joining</th><th>Update size</th></tr></thead><tbody>';
  state.hs.forEach(function(s,i){
    var pos=state.datas[i].y.reduce(function(a,b){return a+b},0)/s.n,la=state.locals[i].auc,g=(fed.auc-la)*100;
    h+='<tr><td><div class="site"><i class="dot" style="background:var(--h'+i+')"></i><span>'+SITES[i][0]+'<small>'+SITES[i][1]+'</small></span></div></td>'+
       '<td>'+s.n+'</td><td>'+Math.round(pos*100)+'%</td><td>'+Math.round(s.n/state.N*100)+'%</td><td>'+f3(la)+'</td>'+
       '<td class="'+(g>=0?'pos':'neg')+'">'+(g>=0?'+':'')+g.toFixed(1)+' pts</td><td class="mono">'+(sr===0?'-':f2(state.fed[sr].norms[i]))+'</td></tr>';
  });
  $('#sites').innerHTML=h+'</tbody>';
}
function renderSweep(){
  var el=$('#sweep');
  if(!state.sweep){el.innerHTML='<p class="note">Running privacy sweep…</p>';return;}
  var W=Math.max(300,el.clientWidth||600),H=W<520?220:260,m={l:46,r:14,t:14,b:44},sw=state.sweep;
  var yr=yRange(sw.map(function(o){return o.auc}).concat([state.centralAuc])),y0=yr[0],y1=yr[1];
  var Y=function(v){return H-m.b-(H-m.t-m.b)*(v-y0)/(y1-y0)};
  var step=(y1-y0)>0.3?0.1:0.05,s='<svg viewBox="0 0 '+W+' '+H+'" width="'+W+'" height="'+H+'" role="img" aria-label="Final AUC for different privacy noise levels">';
  for(var v=y0;v<=y1+1e-9;v+=step){
    s+='<line class="gl" x1="'+m.l+'" x2="'+(W-m.r)+'" y1="'+Y(v).toFixed(1)+'" y2="'+Y(v).toFixed(1)+'"/><text class="axt" x="'+(m.l-8)+'" y="'+(Y(v)+4).toFixed(1)+'" text-anchor="end">'+v.toFixed(2)+'</text>';
  }
  var slot=(W-m.l-m.r)/sw.length,bw=Math.min(56,slot*0.6);
  sw.forEach(function(o,i){
    var cx=m.l+slot*(i+0.5),top=Y(Math.max(y0,o.auc)),base=Y(y0);
    s+='<rect x="'+(cx-bw/2).toFixed(1)+'" y="'+top.toFixed(1)+'" width="'+bw.toFixed(1)+'" height="'+Math.max(1,base-top).toFixed(1)+'" fill="var(--accent)" opacity="'+(o.sigma===0?1:0.78)+'"/>'+
       '<text class="axt" x="'+cx.toFixed(1)+'" y="'+(top-6).toFixed(1)+'" text-anchor="middle" style="fill:var(--fg)">'+f3(o.auc)+'</text>'+
       '<text class="axt" x="'+cx.toFixed(1)+'" y="'+(H-m.b+16)+'" text-anchor="middle">'+(o.sigma===0?'off':'σ '+o.sigma)+'</text>';
  });
  s+='<line x1="'+m.l+'" x2="'+(W-m.r)+'" y1="'+Y(state.centralAuc).toFixed(1)+'" y2="'+Y(state.centralAuc).toFixed(1)+'" stroke="var(--fg)" stroke-width="2" stroke-dasharray="6 4"/>';
  s+='<text class="axl" x="'+((m.l+W-m.r)/2)+'" y="'+(H-4)+'" text-anchor="middle">Privacy noise level (dashed line: pooled records)</text></svg>';
  el.innerHTML=s;
}
function renderCoefs(){
  var w=state.fed[state.round].w,c=state.central,mx=0.5,j;
  for(j=0;j<D;j++)mx=Math.max(mx,Math.abs(w[j]),Math.abs(c[j]));
  var h='';
  function bar(cls,v){var wd=Math.abs(v)/mx*50;return '<i class="cb '+cls+'" style="width:'+wd.toFixed(1)+'%;left:'+(v>=0?50:50-wd).toFixed(1)+'%"></i>';}
  for(j=0;j<D;j++){
    h+='<div class="crow"><span>'+FEATS[j].name+'</span><div class="ctrack">'+bar('f',w[j])+bar('p',c[j])+'</div><span class="cv">'+f2(w[j])+' / '+f2(c[j])+'</span></div>';
  }
  $('#coefs').innerHTML=h;
}
function buildSliders(){
  var h='';
  FEATS.forEach(function(f,i){
    h+='<div class="ctl"><div class="row"><label for="p-'+i+'">'+f.name+'</label><output id="po-'+i+'">'+f.def+(f.unit?' '+f.unit:'')+'</output></div>'+
       '<input type="range" id="p-'+i+'" min="'+f.min+'" max="'+f.max+'" step="'+f.step+'" value="'+f.def+'"></div>';
  });
  $('#sliders').innerHTML=h;
  FEATS.forEach(function(f,i){
    $('#p-'+i).addEventListener('input',function(){
      $('#po-'+i).textContent=$('#p-'+i).value+(f.unit?' '+f.unit:'');renderRisk();
    });
  });
}
function riskOf(w){
  var z=FEATS.map(function(f,i){return clampz((parseFloat($('#p-'+i).value)-f.mu)/f.sd)});
  return sig(raw(w,z));
}
function renderRisk(){
  var p=riskOf(state.fed[state.round].w),pc=riskOf(state.central);
  var cat=p<0.2?'Lower risk':p<0.5?'Elevated risk':'High risk',col=p<0.2?'var(--good)':p<0.5?'var(--warn)':'var(--bad)';
  $('#risk').innerHTML='<span class="note" style="margin:0">Predicted probability of diabetes</span>'+
    '<span class="big">'+Math.round(p*100)+'%</span><span class="cat" style="color:'+col+'">'+cat+'</span>'+
    '<div class="meter"><i style="left:'+(p*100).toFixed(1)+'%"></i></div>'+
    '<div class="ticks"><span>0%</span><span>50%</span><span>100%</span></div>'+
    '<span class="note" style="margin:0">Pooled-records model says '+Math.round(pc*100)+'%. Category cut-offs at 20% and 50% are for illustration.</span>';
}
function renderRound(){
  $('#roundout').textContent=state.round+' / '+state.params.R;
  renderConv();renderSites();renderCoefs();renderRisk();
}
function renderAll(){renderResults();renderConv();renderSites();renderSweep();renderCoefs();renderRisk();$('#roundout').textContent=state.round+' / '+state.params.R;}

/* ---------- wiring ---------- */
var timer=null;
function schedule(){clearTimeout(timer);timer=setTimeout(simulate,140);}
function init(){
  renderControls();buildSliders();
  CTL.forEach(function(c){
    $('#c-'+c.id).addEventListener('input',function(){
      $('#o-'+c.id).textContent=c.fmt(parseFloat($('#c-'+c.id).value));
      if(c.id==='R')state.roundFollowsEnd=(state.round>=state.params.R);
      schedule();
    });
  });
  state.roundFollowsEnd=true;
  $('#round').addEventListener('input',function(){
    state.round=parseInt($('#round').value,10);state.roundFollowsEnd=false;renderRound();
  });
  $('#conv').addEventListener('click',function(e){
    var g=this._geo;if(!g)return;
    var rect=this.getBoundingClientRect(),x=e.clientX-rect.left;
    var r=Math.round((x-g.l)/(g.r-g.l)*g.R);r=Math.max(0,Math.min(g.R,r));
    state.round=r;state.roundFollowsEnd=false;$('#round').value=r;renderRound();
  });
  $('#btn-seed').addEventListener('click',function(){state.seed=Math.floor(Math.random()*9000)+1000;simulate();});
  $('#btn-reset').addEventListener('click',function(){
    CTL.forEach(function(c){$('#c-'+c.id).value=c.val;$('#o-'+c.id).textContent=c.fmt(c.val);});
    state.seed=2024;state.roundFollowsEnd=true;simulate();
  });
  var rz=null;
  window.addEventListener('resize',function(){clearTimeout(rz);rz=setTimeout(function(){if(state.fed.length){renderConv();renderSweep();}},120);});
  simulate();
}
init();
})();
