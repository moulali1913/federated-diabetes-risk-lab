import os, re, subprocess, sys
from playwright.sync_api import sync_playwright

HERE=os.getcwd()
FONT='Times New Roman,Liberation Serif,serif'
BLUE='#1f6fcf'; GREY='#8d8d80'

def line_chart(title, xs, series, ymin, ymax, ystep, xlabel, ylabel, xfmt=str, W=640, H=270, xpos=None):
    L,R,T,B=58,92,34,48
    pw,ph=W-L-R,H-T-B
    X=(lambda i: L+pw*(xpos[i]-xpos[0])/(xpos[-1]-xpos[0])) if xpos else (lambda i: L+pw*i/(len(xs)-1))
    Y=lambda v: T+ph*(1-(v-ymin)/(ymax-ymin))
    o=[f'<svg viewBox="0 0 {W} {H}" width="100%" font-family="{FONT}" role="img" aria-label="{title}">']
    o.append(f'<text x="{L}" y="18" font-size="13" font-weight="bold">{title}</text>')
    v=ymin
    while v<=ymax+1e-9:
        o.append(f'<line x1="{L}" x2="{W-R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="#ddd"/><text x="{L-6}" y="{Y(v)+4:.1f}" font-size="10.5" text-anchor="end" fill="#333">{v:.3f}</text>')
        v+=ystep
    for i,x in enumerate(xs):
        o.append(f'<text x="{X(i):.1f}" y="{T+ph+15}" font-size="10.5" text-anchor="middle" fill="#333">{xfmt(x)}</text>')
    o.append(f'<line x1="{L}" x2="{W-R}" y1="{T+ph}" y2="{T+ph}" stroke="#222"/>')
    o.append(f'<text x="{L+pw/2}" y="{H-8}" font-size="11" text-anchor="middle">{xlabel}</text>')
    o.append(f'<text transform="translate(14 {T+ph/2}) rotate(-90)" font-size="11" text-anchor="middle">{ylabel}</text>')
    for s in series:
        pts=[(X(i),Y(v)) for i,v in enumerate(s['y'])]
        d=' '.join(f'{"M" if i==0 else "L"}{x:.1f} {y:.1f}' for i,(x,y) in enumerate(pts))
        dash=f' stroke-dasharray="{s["dash"]}"' if s.get('dash') else ''
        o.append(f'<path d="{d}" fill="none" stroke="{s["color"]}" stroke-width="{s.get("w",2.2)}"{dash}/>')
        if s.get('dots'):
            for x,y in pts: o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{s["color"]}"/>')
        o.append(f'<text x="{W-R+6}" y="{pts[-1][1]+s.get("ly",4):.1f}" font-size="10.5" fill="{s["color"] if s["color"]!="#222" else "#111"}">{s["label"]}</text>')
    o.append('</svg>')
    return ''.join(o)

def sigma_chart():
    W,H=640,270; L,T,B=50,34,60
    base=T+150+0
    # scale: 3.3 pts -> 150px
    k=150/3.3; floor=T+190
    items=[('No noise','0.0',0,False),('σ 0.25','0.0',0.0,False),('σ 0.5','0.4',0.4,False),('σ 1','1.6',1.6,True),('σ 1.5','3.3',3.3,True)]
    o=[f'<svg viewBox="0 0 {W} {H}" width="100%" font-family="{FONT}" role="img" aria-label="AUC lost to privacy noise">']
    o.append(f'<text x="{L}" y="18" font-size="13" font-weight="bold">AUC lost to privacy noise (points), mean of 5 cohorts</text>')
    o.append(f'<line x1="{L}" x2="{W-20}" y1="{floor}" y2="{floor}" stroke="#222"/>')
    gain=0.7
    for i,(lab,txt,v,over) in enumerate(items):
        cx=L+60+i*118; h=max(v*k,0)
        col=GREY if over else BLUE
        if h>0: o.append(f'<rect x="{cx-30}" y="{floor-h:.1f}" width="60" height="{h:.1f}" fill="{col}"/>')
        o.append(f'<text x="{cx}" y="{floor+16}" font-size="11" text-anchor="middle">{lab}</text>')
        o.append(f'<text x="{cx}" y="{floor+32}" font-size="11.5" font-weight="bold" text-anchor="middle">{txt} pts</text>')
    gy=floor-gain*k
    o.append(f'<line x1="{L}" x2="{W-20}" y1="{gy:.1f}" y2="{gy:.1f}" stroke="#444" stroke-dasharray="5 4"/>')
    o.append(f'<text x="{L+4}" y="{gy-6:.1f}" font-size="10.5" fill="#333">Mean gain from federating, 10 cohorts: 0.7 pts</text>')
    o.append('</svg>'); return ''.join(o)

def arch_svg():
    W,H=700,330
    o=[f'<svg viewBox="0 0 {W} {H}" width="100%" font-family="{FONT}" role="img" aria-label="System architecture">',
    '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#333"/></marker></defs>']
    o.append('<rect x="225" y="14" width="250" height="68" fill="#e6f0fb" stroke="#1f6fcf" stroke-width="1.5"/>')
    o.append('<text x="350" y="40" font-size="14" font-weight="bold" text-anchor="middle">Coordinator</text><text x="350" y="58" font-size="11.5" text-anchor="middle">clips and averages updates (FedAvg),</text><text x="350" y="72" font-size="11.5" text-anchor="middle">adds noise, keeps the shared model</text>')
    names=['Hospital A','Hospital B','Hospital C','Hospital D','Hospital E']
    for i,n in enumerate(names):
        x=20+i*135; cx=x+60; sx=285+i*32
        o.append(f'<rect x="{x}" y="215" width="120" height="82" fill="#f3f3ee" stroke="#555"/>')
        o.append(f'<text x="{cx}" y="236" font-size="12.5" font-weight="bold" text-anchor="middle">{n}</text>')
        o.append(f'<text x="{cx}" y="254" font-size="10.5" text-anchor="middle">Patient records</text><text x="{cx}" y="268" font-size="10.5" text-anchor="middle">(never leave)</text><text x="{cx}" y="286" font-size="10.5" text-anchor="middle">Local training</text>')
        o.append(f'<line x1="{sx-5}" y1="82" x2="{cx-8}" y2="215" stroke="#333" marker-end="url(#ah)"/>')
        o.append(f'<line x1="{cx+8}" y1="215" x2="{sx+5}" y2="82" stroke="#1f6fcf" stroke-dasharray="4 3" marker-end="url(#ah)"/>')
    o.append('<line x1="20" x2="40" y1="318" y2="318" stroke="#333" marker-end="url(#ah)"/><text x="46" y="322" font-size="11">Shared model weights (9 values)</text>')
    o.append('<line x1="270" x2="290" y1="318" y2="318" stroke="#1f6fcf" stroke-dasharray="4 3" marker-end="url(#ah)"/><text x="296" y="322" font-size="11">Clipped weight update (9 values)</text>')
    o.append('</svg>'); return ''.join(o)

def round_svg():
    W,H=700,190
    o=[f'<svg viewBox="0 0 {W} {H}" width="100%" font-family="{FONT}" role="img" aria-label="One federated round">',
    '<defs><marker id="ah2" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="#333"/></marker></defs>']
    boxes=[('1. Broadcast','Send current weights','to every hospital'),('2. Train locally','Mini-batch gradient','descent on own patients'),('3. Clip and upload','Send change in weights,','norm limited to 1'),('4. Aggregate','Size-weighted average,','add noise, update model')]
    for i,(a,b,c) in enumerate(boxes):
        x=10+i*173
        o.append(f'<rect x="{x}" y="20" width="150" height="76" fill="#f3f3ee" stroke="#555"/>')
        o.append(f'<text x="{x+75}" y="44" font-size="13" font-weight="bold" text-anchor="middle">{a}</text><text x="{x+75}" y="64" font-size="11" text-anchor="middle">{b}</text><text x="{x+75}" y="79" font-size="11" text-anchor="middle">{c}</text>')
        if i<3: o.append(f'<line x1="{x+150}" y1="58" x2="{x+173}" y2="58" stroke="#333" marker-end="url(#ah2)"/>')
    o.append('<path d="M595 96 V150 H85 V98" fill="none" stroke="#333" marker-end="url(#ah2)"/>')
    o.append('<text x="340" y="170" font-size="12" text-anchor="middle">repeat for R rounds (default 30)</text>')
    o.append('</svg>'); return ''.join(o)

conv=line_chart('Federated AUC by round, mean of 10 cohorts',[1,2,3,5,8,10,15,20,25,30],[
 {'y':[0.849,0.854,0.855,0.856,0.856,0.856,0.856,0.857,0.856,0.857],'color':BLUE,'label':'Federated','dots':True,'ly':14},
 {'y':[0.858]*10,'color':'#222','dash':'6 4','label':'Pooled records','w':1.8,'ly':-6},
 {'y':[0.850]*10,'color':'#7a7a70','dash':'3 3','label':'Average single site','w':1.8,'ly':14}],
 0.845,0.862,0.005,'Communication round','Test AUC',xpos=[1,2,3,5,8,10,15,20,25,30],xfmt=lambda v: str(v) if v in (1,5,10,15,20,25,30) else '')
# fix: conv x labels for sparse ticks handled by xfmt
het=line_chart('Test AUC as hospitals differ more, mean of 10 cohorts',[0,0.4,0.8,1.2,1.5],[
 {'y':[0.848,0.850,0.857,0.861,0.867],'color':BLUE,'label':'Federated','dots':True,'ly':-4},
 {'y':[0.849,0.850,0.858,0.862,0.869],'color':'#222','dash':'6 4','label':'Pooled records','w':1.6,'ly':-16},
 {'y':[0.842,0.844,0.850,0.853,0.857],'color':'#7a7a70','dash':'3 3','label':'Average single site','w':1.8,'ly':14}],
 0.840,0.870,0.005,'Case-mix difference setting','Test AUC',xfmt=lambda v: str(v))

STYLE='''
@page{size:A4;margin:0}
*{box-sizing:border-box}
body{font-family:"Times New Roman","Liberation Serif",serif;color:#000;font-size:11pt;line-height:1.38;margin:0}
.page{page-break-after:always}
.page:last-child{page-break-after:auto}
h1{font-size:17pt;margin:16px 0 6px}
h1.front{text-align:center;font-size:18pt;margin:6px 0 16px;text-transform:uppercase;letter-spacing:.5px}
h2{font-size:13.5pt;margin:12px 0 4px;page-break-after:avoid}
h3{font-size:12pt;margin:8px 0 3px;page-break-after:avoid}
p{margin:5px 0;text-align:justify}
ul,ol{margin:5px 0;padding-left:24px}li{margin:2px 0;text-align:justify}
table{border-collapse:collapse;width:100%;margin:8px 0 4px;font-size:10.5pt;page-break-inside:avoid}
th,td{border:1px solid #444;padding:3px 7px;text-align:left}th{background:#e6e6e6}
.n{text-align:right}
.cap{font-size:10pt;text-align:center;margin:2px 0 10px;color:#222}
figure{margin:8px 0 2px;page-break-inside:avoid}
pre{font-family:"Liberation Mono","Courier New",monospace;font-size:8.8pt;line-height:1.3;background:#f4f4f1;border:1px solid #ccc;padding:7px 9px;margin:6px 0;white-space:pre-wrap;page-break-inside:avoid}
.sig{display:flex;justify-content:space-between;margin-top:70px}
.sig div{text-align:center;width:44%}
.sig .line{border-top:1px solid #000;padding-top:4px}
.toc{width:100%;border:0;font-size:11.5pt;margin:0}
.toc td{border:0;padding:1px 0;font-size:10.5pt}
.toc td.pg{text-align:right;width:40px}.toc td:first-child{border-bottom:1px dotted #aaa}
.toc tr.sub td{padding-left:22px;font-size:9.5pt}
.eq{text-align:center;margin:6px 0;font-style:italic}
.note{font-size:10pt;color:#333}
'''

def cover():
    return '''<div class="page cover" style="height:297mm;padding:14mm">
<div style="border:2px solid #000;height:100%;padding:8mm 10mm;text-align:center;display:flex;flex-direction:column;justify-content:space-between">
 <div><img src="logo.png" style="width:62%;display:block;margin:0 auto">
  <p style="text-align:center;font-size:25pt;margin:10mm 0 0;line-height:1.2">School of Computer Science and Engineering</p>
  <p style="text-align:center;font-size:14pt;margin-top:6px">(Cloud Technology and Mobile Applications)</p>
  <p style="text-align:center;font-size:14pt">Faculty of Engineering &amp; Technology</p>
  <p style="text-align:center;font-size:11pt;margin-top:4px">Jain Global Campus, Kanakapura Taluk - 562112<br>Ramanagara District, Karnataka, India</p></div>
 <div><p style="text-align:center;font-size:14pt;font-weight:bold;margin:0">2026-2027</p><p style="text-align:center;font-size:11pt;font-weight:bold;margin:6px 0 0">(III Semester)</p></div>
 <div style="display:flex;flex-direction:column;gap:3.5mm">
  <p style="text-align:center;font-size:14pt;font-weight:bold;margin:0">An Application Project Report for the course</p>
  <p style="text-align:center;font-size:17pt;font-weight:bold;margin:0">25PCCS202 - Python Programming</p>
  <p style="text-align:center;font-size:13pt;font-style:italic;margin:2mm 0 0">Project: Federated Learning Simulation for Privacy-Preserving Diabetic Risk Prediction Across Hospitals</p>
  <p style="text-align:center;font-size:11pt;font-weight:bold;margin:0">Submitted in partial fulfilment for the completion of the course</p>
  <p style="text-align:center;font-size:14pt;font-weight:bold;margin:0">BACHELOR OF TECHNOLOGY IN</p>
  <p style="text-align:center;font-size:14pt;font-weight:bold;margin:0">COMPUTER SCIENCE &amp; ENGINEERING</p>
  <p style="text-align:center;font-size:14pt;font-weight:bold;margin:0">(CTMA)</p></div>
 <div><p style="text-align:center;font-size:11pt;font-weight:bold;margin:0">Submitted by</p><p style="text-align:center;font-size:17pt;font-weight:bold;margin:6px 0 0">SHAIK MAHAMMAD MOULALI (25BTRCM048)</p></div>
 <div><p style="text-align:center;font-size:11pt;font-weight:bold;margin:0">Under the guidance of</p><p style="text-align:center;font-size:14pt;font-weight:bold;margin:4px 0">Dr. B. Narmada</p>
  <p style="text-align:center;font-size:11pt;margin:0">Assistant Professor<br>Department of Computer Science &amp; Engineering - CTMA<br>School of Computer Science &amp; Engineering<br>Faculty of Engineering &amp; Technology<br>JAIN (Deemed-to-be University)</p></div>
</div></div>'''

TITLE='Federated Learning Simulation for Privacy-Preserving Diabetic Risk Prediction Across Hospitals'

def front():
    return f'''
<div class="page"><h1 class="front">Certificate</h1>
<p>This is to certify that the Application Project Report entitled <b>&ldquo;{TITLE}&rdquo;</b> is a bonafide record of work carried out by <b>SHAIK MAHAMMAD MOULALI (25BTRCM048)</b> in partial fulfilment of the requirements for the course <b>25PCCS202 - Python Programming</b> of the Bachelor of Technology in Computer Science &amp; Engineering (CTMA), III Semester, academic year 2026-2027, at the School of Computer Science and Engineering, Faculty of Engineering &amp; Technology, JAIN (Deemed-to-be University).</p>
<p>The work was carried out under my guidance. The report has not been submitted to any other course, university or institution for the award of any grade or degree.</p>
<div class="sig"><div><div class="line"><b>Dr. B. Narmada</b><br>Assistant Professor<br>Department of Computer Science &amp; Engineering - CTMA<br>(Project Guide)</div></div><div><div class="line"><b>Head of the Department</b><br>Department of Computer Science &amp; Engineering - CTMA</div></div></div>
<p style="margin-top:50px">Date: ____________________ &nbsp;&nbsp;&nbsp;&nbsp; Place: Ramanagara, Karnataka</p>
</div>

<div class="page"><h1 class="front">Declaration</h1>
<p>I, <b>SHAIK MAHAMMAD MOULALI (25BTRCM048)</b>, a student of the III Semester B.Tech in Computer Science &amp; Engineering (CTMA), JAIN (Deemed-to-be University), hereby declare that this Application Project Report entitled <b>&ldquo;{TITLE}&rdquo;</b> is an original piece of work done by me under the guidance of Dr. B. Narmada, Assistant Professor, Department of Computer Science &amp; Engineering - CTMA.</p>
<p>The simulation, the experiments and the results described in this report were produced by me. Published work that I have used or referred to is acknowledged in the text and listed in the References. All patient data used in the project is synthetic; no real patient record was collected, used or shared.</p>
<p style="margin-top:36px;text-align:right"><b>SHAIK MAHAMMAD MOULALI</b><br>25BTRCM048</p>
<p>Date: ____________________</p>
<h1 class="front" style="margin-top:44px">Acknowledgement</h1>
<p>I thank my project guide, Dr. B. Narmada, Assistant Professor, Department of Computer Science &amp; Engineering - CTMA, for her guidance, suggestions and encouragement throughout this project.</p>
<p>I am grateful to the Head of the Department and the faculty of the School of Computer Science and Engineering, Faculty of Engineering &amp; Technology, JAIN (Deemed-to-be University), for providing the learning environment and facilities needed to complete this work. I also thank my classmates and family for their support.</p>
</div>

<div class="page"><h1 class="front">Abstract</h1>
<p>Hospitals hold the patient data needed to build accurate diabetes risk models, but privacy rules and institutional policy prevent them from copying that data into one place. Federated learning offers a way around this: each hospital trains a shared model on its own patients, and only the model weights are exchanged and averaged.</p>
<p>This project builds an interactive simulation of federated learning for diabetic risk prediction. Between 3 and 10 virtual hospitals, each with its own synthetic patients based on the eight features of the Pima Indians Diabetes dataset, train a logistic regression model using Federated Averaging (FedAvg). The simulation lets the user change the number of hospitals, communication rounds, local epochs, learning rate, how different the hospitals' patient populations are, and the strength of privacy noise (update clipping plus Gaussian noise). It reports the area under the ROC curve (AUC) of the federated model against a model trained on pooled records and against models trained by each hospital alone, and it lets the user score a made-up patient.</p>
<p>Across ten simulated cohorts at the default settings, the federated model reached a mean test AUC of 0.857 (standard deviation 0.014), against 0.858 for the pooled-records model and 0.850 for the average single-hospital model. The federated model beat the average single-hospital model in all ten cohorts, by 0.7 AUC points on average. It stayed within 0.002 AUC of the pooled model when the hospitals' patients were made more different from each other. Privacy noise up to a standard deviation factor of 0.5 cost about 0.4 AUC points, less than the 0.7-point gain from federating, while a factor of 1 cost 1.6 points and removed the benefit.</p>
<p>The results come from synthetic data and an illustrative noise mechanism without formal privacy accounting, so they show that the approach works, not how it would perform on real hospital records. The simulation is a self-contained web page that runs in a browser with no server.</p>
<p><b>Keywords:</b> federated learning, federated averaging, diabetes risk prediction, privacy preservation, logistic regression, simulation, healthcare.</p>
</div>

<div class="page"><h1 class="front">Table of Contents</h1>
@@TOC@@
</div>
'''

def body():
    return f'''
<div class="page">
<h1>1. Introduction</h1>
<h2>1.1 Background</h2>
<p>Diabetes is a long-term condition that is easier and cheaper to manage when it is found early. Machine learning models that estimate a patient's risk from routine measurements such as glucose, body mass index (BMI), blood pressure and age can help clinicians decide who needs screening first. Such models improve when they learn from more patients and from more varied patients, which in practice means learning from the records of several hospitals.</p>
<p>Hospital records are sensitive. Privacy law, ethics approvals and institutional policy usually forbid copying identifiable patient data to a central server, even for research. As a result each hospital tends to build its own model from its own, smaller and often unrepresentative, patient group.</p>
<h2>1.2 Federated learning in brief</h2>
<p>Federated learning reverses the usual direction of movement. Instead of sending data to the model, the model goes to the data. A coordinator sends the current model to every participating site, each site improves it using only its own records, and the sites send back only the change they made to the model. The coordinator combines the changes into a better shared model and starts the next round. Raw records are never transmitted.</p>
<h2>1.3 Problem statement</h2>
<p>Design and build a simulation that shows whether hospitals can jointly train a diabetic risk model without sharing patient records, and that measures what the arrangement costs and gains in accuracy and privacy.</p>
<h2>1.4 Objectives</h2>
<ol>
<li>Implement Federated Averaging for a logistic regression diabetes risk model, running entirely in the browser.</li>
<li>Generate synthetic patients for several hospitals whose patient mix can be made more or less different.</li>
<li>Compare the federated model with a model trained on pooled records and with models trained at each hospital alone.</li>
<li>Add update clipping and Gaussian noise, and measure how much accuracy that privacy protection costs.</li>
<li>Present the results through interactive controls, charts, a per-hospital table and a patient risk calculator.</li>
</ol>
<h2>1.5 Scope</h2>
<p>The project covers a simulation with synthetic data. It does not use real patient records, does not give medical advice, and does not provide a formal privacy guarantee. The model is a logistic regression, chosen because it is simple, fast and easy to inspect.</p>
<h2>1.6 Organisation of the report</h2>
<p>Chapter 2 reviews related work. Chapter 3 describes the system design. Chapter 4 explains the methodology, and Chapter 5 the implementation. Chapter 6 presents and discusses the results. Chapter 7 lists limitations, and Chapter 8 concludes with future work.</p>

<h1>2. Literature Review</h1>
<h2>2.1 Federated averaging</h2>
<p>McMahan et al. (2017) introduced Federated Averaging (FedAvg), in which clients run several steps of local gradient descent and the server averages the resulting models weighted by the number of local examples. They showed that this needs far fewer communication rounds than sending a gradient after every step. FedAvg is the aggregation rule used in this project.</p>
<h2>2.2 Challenges and open problems</h2>
<p>Li et al. (2020) and Kairouz et al. (2021) survey the field. The main challenges they identify are communication cost, differences between the data held by different clients (statistical heterogeneity), uneven client resources, and privacy and security of the exchanged updates. Healthcare is a standard motivating example because data is both valuable and tightly controlled.</p>
<h2>2.3 Heterogeneous data</h2>
<p>When clients hold differently distributed data, local training pulls each client's model in a different direction, which can slow or bias convergence. Li et al. (2020, MLSys) proposed FedProx, which adds a term that keeps local models close to the shared model. This project does not implement FedProx but tests plain FedAvg under growing heterogeneity, using a case-mix setting that shifts age, BMI, glucose and baseline risk at each hospital.</p>
<h2>2.4 Privacy of model updates</h2>
<p>Keeping records local does not make updates automatically safe, because updates can leak information about the data that produced them. Differential privacy (Dwork and Roth, 2014) limits what any single record can change in the output. Abadi et al. (2016) showed how to train deep networks with differential privacy by clipping gradients and adding Gaussian noise. Secure aggregation (Bonawitz et al., 2017) lets a server learn only the sum of client updates and not any individual update. This project borrows the clip-and-add-noise idea to show the accuracy cost of protection, but does not perform formal privacy accounting or secure aggregation.</p>
<h2>2.5 Data and evaluation</h2>
<p>The Pima Indians Diabetes dataset (Smith et al., 1988) records eight measurements for women of Pima heritage and whether they developed diabetes, and is widely used to demonstrate risk prediction. Its eight features are used here as the basis for synthetic patients. Models are compared by the area under the ROC curve (AUC), which equals the probability that a randomly chosen diabetic patient receives a higher risk score than a randomly chosen non-diabetic one (Hanley and McNeil, 1982).</p>
<h2>2.6 Gap addressed</h2>
<p>Most published examples show federated learning as code or as a final accuracy number. This project makes the trade-offs visible and adjustable: the user can see in one place how the benefit of joining depends on hospital size, how different the hospitals are, and how much privacy noise is applied.</p>
</div>

<div class="page">
<h1>3. System Analysis and Design</h1>
<h2>3.1 Requirements</h2>
<table><tr><th style="width:26%">Type</th><th>Requirement</th></tr>
<tr><td>Functional</td><td>Simulate 3 to 10 hospitals with different patient mixes; train a shared model with FedAvg; train pooled and single-hospital baselines; add clipping and noise; report AUC and accuracy; show per-hospital results; score a user-defined patient.</td></tr>
<tr><td>Usability</td><td>All parameters adjustable with sliders; results update automatically; works on phone and desktop screens, in light and dark themes.</td></tr>
<tr><td>Performance</td><td>A full simulation (30 rounds, 5 hospitals) should finish in well under a second so that sliders feel immediate.</td></tr>
<tr><td>Privacy</td><td>No patient data is stored or transmitted; all data is generated in the browser from a seed.</td></tr>
<tr><td>Portability</td><td>A single HTML file with no server, database or machine learning library.</td></tr>
</table>
<h2>3.2 Architecture</h2>
<p>Figure 3.1 shows the logical architecture. Each hospital keeps its patient records locally. A coordinator holds only the shared model, which for logistic regression with eight features is nine numbers (eight weights and a bias).</p>
<figure>{arch_svg()}</figure>
<p class="cap">Figure 3.1: Architecture of the federated simulation</p>
<h2>3.3 One round of training</h2>
<figure>{round_svg()}</figure>
<p class="cap">Figure 3.2: The four steps of one communication round</p>
<h2>3.4 Technology choices</h2>
<table><tr><th style="width:26%">Item</th><th>Choice and reason</th></tr>
<tr><td>Language</td><td>JavaScript, so the simulation runs in any browser without installation.</td></tr>
<tr><td>Model</td><td>Logistic regression: few parameters, fast training, interpretable coefficients.</td></tr>
<tr><td>Random numbers</td><td>Seeded generator (mulberry32), so a cohort can be reproduced exactly from its seed.</td></tr>
<tr><td>Charts</td><td>Hand-built SVG, so every plotted value is computed from the simulation results.</td></tr>
<tr><td>Delivery</td><td>Published as a web page; no back end is needed.</td></tr>
</table>

<h1>4. Methodology</h1>
<h2>4.1 Synthetic patients</h2>
<p>Each patient has the eight Pima features: pregnancies, glucose, blood pressure, skin thickness, insulin, BMI, diabetes pedigree function and age. Features are generated as standardised values with realistic correlations (for example age with pregnancies and BMI with skin thickness) and are clipped to between -3 and 3.5 standard deviations. A fixed logistic risk model, in which glucose, BMI, age and pedigree function carry the largest weights, converts the features into a probability, and the diabetes label is drawn from it.</p>
<p>Each hospital draws its own patients with shifts in age, BMI and glucose and a shift in baseline risk. All shifts are multiplied by the <i>case-mix difference</i> setting: at 0 every hospital has the same kind of patient, and at 1.5 the hospitals differ strongly. In the default cohort (seed 2024) the five hospitals have 248 to 550 patients (1,937 in total) and between 25% and 68% of patients are diabetic.</p>
<h2>4.2 Model and local training</h2>
<p>The model estimates the probability of diabetes from the standardised features x:</p>
<p class="eq">p(diabetes | x) = S(w &middot; x + b), &nbsp; S(z) = 1 / (1 + e<sup>-z</sup>)</p>
<p>Each hospital updates the weights with mini-batch gradient descent on the logistic loss (batch size 32, small L2 penalty of 0.001) for E local epochs at learning rate &eta;.</p>
<h2>4.3 Federated averaging with clipping and noise</h2>
<p>In round t, hospital k starts from the shared weights w<sub>t</sub>, trains locally, and computes its update &Delta;<sub>k</sub> = w<sub>k</sub> &minus; w<sub>t</sub>. When privacy noise is on (&sigma; &gt; 0), the update is clipped to a maximum Euclidean length C = 1. The coordinator then forms the size-weighted average and adds Gaussian noise:</p>
<p class="eq">w<sub>t+1</sub> = w<sub>t</sub> + &Sigma;<sub>k</sub> (n<sub>k</sub> / N) &middot; &Delta;<sub>k</sub> &middot; min(1, C / ||&Delta;<sub>k</sub>||) + Normal(0, (&sigma;C / K)<sup>2</sup>)</p>
<p>where n<sub>k</sub> is the number of patients at hospital k, N the total, and K the number of hospitals. Dividing the noise by K means a larger network dilutes it. With &sigma; = 0 no clipping or noise is applied and the rule is plain FedAvg.</p>
<h2>4.4 Baselines</h2>
<ul>
<li><b>Pooled records:</b> one logistic regression trained on all hospitals' patients together (80 epochs). This is what the network could achieve if data sharing were allowed, so it is an upper bound.</li>
<li><b>Single hospital:</b> one logistic regression per hospital, trained only on its own patients (80 epochs).</li>
</ul>
<h2>4.5 Evaluation</h2>
<p>A test set of about 1,500 patients is drawn from all hospitals in proportion to their size. The main metric is AUC; accuracy at a 0.5 threshold is also reported. To avoid drawing conclusions from one cohort, the key experiments are repeated over ten cohorts (seeds 2024 and 1 to 9), and results are reported as means with standard deviations where useful. The default settings are 5 hospitals, 30 rounds, 3 local epochs, learning rate 0.1, case-mix difference 0.8 and noise &sigma; = 0.2.</p>
</div>

<div class="page">
<h1>5. Implementation</h1>
<h2>5.1 Structure of the program</h2>
<table><tr><th style="width:30%">Component</th><th>Purpose</th></tr>
<tr><td>Cohort generator</td><td>Creates the hospitals, their patients and the shared test set from a seed.</td></tr>
<tr><td>Local trainer</td><td>Mini-batch gradient descent on one hospital's data.</td></tr>
<tr><td>Federated loop</td><td>Runs the rounds: broadcast, local training, clipping, weighted averaging, noise.</td></tr>
<tr><td>Baselines</td><td>Pooled and single-hospital models.</td></tr>
<tr><td>Metrics</td><td>AUC from ranks, and accuracy.</td></tr>
<tr><td>Interface</td><td>Sliders, summary figures, convergence chart, per-hospital table, privacy-noise chart, coefficient comparison and patient risk calculator.</td></tr>
</table>
<h2>5.2 The federated round</h2>
<p>The core of the program is the loop below (shortened from the source). Each hospital's update is clipped when noise is enabled, weighted by its share of patients, and summed, after which noise is added once to the aggregate.</p>
<pre>for (r = 1; r &lt;= R; r++) {{
  agg = zeros(9);
  for (k = 0; k &lt; hospitals.length; k++) {{
    wk = sgd(w, data[k], E, lr, rand);          // local training
    d  = wk - w;                                // update, 9 values
    f  = sigma &gt; 0 ? min(1, CLIP / norm(d)) : 1; // clip to norm 1
    agg += (hospitals[k].n / N) * f * d;        // size-weighted
  }}
  if (sigma &gt; 0) agg += gauss() * sigma * CLIP / K;  // noise
  w += agg;                                     // new shared model
}}</pre>
<h2>5.3 Evaluation by ranks</h2>
<p>AUC is computed without plotting the ROC curve: test patients are sorted by predicted score, and the sum of the ranks of the diabetic patients gives the Mann-Whitney statistic, which equals the AUC.</p>
<pre>auc = (rankSumOfPositives - P * (P + 1) / 2) / (P * Nneg)</pre>
<h2>5.4 User interface</h2>
<p>The page opens with four headline figures (federated AUC, pooled AUC, average single-hospital AUC and the number of patient records shared, which is always zero). Below are the settings, a convergence chart with a round selector, a per-hospital table, the privacy-noise chart, a bar comparison of the federated and pooled coefficients, and a patient calculator with sliders for the eight features. Changing any setting reruns the simulation. A button creates a new random patient cohort. Colours follow the device's light or dark theme.</p>
<h2>5.5 Running the application</h2>
<ol>
<li>Open the published page in a web browser; no installation is needed.</li>
<li>Choose the number of hospitals, rounds, local epochs, learning rate, case-mix difference and privacy noise.</li>
<li>Read the headline figures and charts; drag the round selector to see the model at earlier rounds.</li>
<li>Set the patient sliders to see the predicted diabetes risk from the federated model and the pooled model.</li>
</ol>
</div>

<div class="page">
<h1>6. Results and Discussion</h1>
<h2>6.1 Default cohort</h2>
<p>For the default cohort (seed 2024) the federated model reached a test AUC of 0.859 and 78% accuracy after 30 rounds, against 0.858 for pooled records and 0.850 for the average single hospital. Every hospital gained from joining, and the hospital with the lowest single-site AUC gained most.</p>
<table><tr><th>Hospital</th><th class="n">Patients</th><th class="n">Diabetic</th><th class="n">Single-site AUC</th><th class="n">Gain from joining (AUC pts)</th></tr>
<tr><td>A (urban teaching)</td><td class="n">482</td><td class="n">30%</td><td class="n">0.851</td><td class="n">+0.8</td></tr>
<tr><td>B (regional district)</td><td class="n">550</td><td class="n">25%</td><td class="n">0.853</td><td class="n">+0.6</td></tr>
<tr><td>C (diabetes referral)</td><td class="n">248</td><td class="n">47%</td><td class="n">0.856</td><td class="n">+0.3</td></tr>
<tr><td>D (rural primary care)</td><td class="n">302</td><td class="n">68%</td><td class="n">0.855</td><td class="n">+0.4</td></tr>
<tr><td>E (private multispecialty)</td><td class="n">355</td><td class="n">30%</td><td class="n">0.833</td><td class="n">+2.6</td></tr></table>
<p class="cap">Table 6.1: Per-hospital results for the default cohort (federated AUC 0.859)</p>
<h2>6.2 Convergence</h2>
<p>Training converges within a few rounds. Averaged over ten cohorts, the federated AUC is 0.849 after one round and 0.855 after three, and stays between 0.856 and 0.857 from round 5 to round 30 (Figure 6.1). Further rounds add almost nothing for this model, which suggests that fewer rounds could be used to save communication.</p>
<figure>{conv}</figure>
<p class="cap">Figure 6.1: Federated test AUC by communication round, compared with the pooled and single-site averages</p>
<h2>6.3 Repeated cohorts</h2>
<table><tr><th>Model (10 cohorts, default settings)</th><th class="n">Mean AUC</th><th class="n">Std. dev.</th></tr>
<tr><td>Federated (&sigma; = 0.2)</td><td class="n">0.857</td><td class="n">0.014</td></tr>
<tr><td>Pooled records</td><td class="n">0.858</td><td class="n">0.014</td></tr>
<tr><td>Average single hospital</td><td class="n">0.850</td><td class="n">0.015</td></tr>
<tr><td>Federated minus pooled</td><td class="n">-0.001</td><td class="n">0.002</td></tr>
<tr><td>Federated minus average single hospital</td><td class="n">+0.007</td><td class="n">0.003</td></tr></table>
<p class="cap">Table 6.2: Summary over ten cohorts (seeds 2024 and 1 to 9); mean federated accuracy 78.9%</p>
<p>The standard deviation of 0.014 across cohorts is much larger than the 0.002 spread of the federated-minus-pooled difference, because some cohorts are simply easier to predict than others. Comparing models within each cohort is therefore the fair test. Federated learning beat the average single hospital in all ten cohorts and was within 0.003 AUC of pooled training in each of them, so the 0.7-point gain and the near-match to pooled data are consistent.</p>
<h2>6.4 Number of hospitals and local epochs</h2>
<table><tr><th>Hospitals</th><th class="n">Federated</th><th class="n">Pooled</th><th class="n">Avg. single</th><th class="n">Gain (pts)</th></tr>
<tr><td>3</td><td class="n">0.854</td><td class="n">0.856</td><td class="n">0.849</td><td class="n">+0.4</td></tr>
<tr><td>5</td><td class="n">0.857</td><td class="n">0.858</td><td class="n">0.850</td><td class="n">+0.7</td></tr>
<tr><td>7</td><td class="n">0.853</td><td class="n">0.854</td><td class="n">0.846</td><td class="n">+0.7</td></tr>
<tr><td>10</td><td class="n">0.855</td><td class="n">0.856</td><td class="n">0.848</td><td class="n">+0.7</td></tr></table>
<p class="cap">Table 6.3: Mean test AUC over ten cohorts for different network sizes</p>
<table><tr><th>Local epochs per round</th><th class="n">Final federated AUC</th><th class="n">Rounds to come within 0.005 of pooled AUC (mean)</th></tr>
<tr><td>1</td><td class="n">0.857</td><td class="n">6.6</td></tr>
<tr><td>3</td><td class="n">0.857</td><td class="n">2.2</td></tr>
<tr><td>8</td><td class="n">0.857</td><td class="n">1.3</td></tr></table>
<p class="cap">Table 6.4: Effect of local epochs on speed of convergence (ten cohorts)</p>
<p>The gain from federating was 0.4 points with three hospitals and 0.7 points with five or more; the AUC differences between network sizes mostly reflect which patients each cohort contains, so only the gain column is meaningful here. More local epochs reached the target in fewer rounds (6.6, 2.2 and 1.3) without changing the final accuracy, which is the saving in communication that FedAvg is designed for. For a model with only nine weights the extra local computation is cheap; for larger models and more heterogeneous data it may not be so harmless.</p>
<h2>6.5 Differences between hospitals</h2>
<p>The case-mix setting was varied from 0 (identical hospitals) to 1.5 (very different hospitals). The federated model stayed within 0.002 AUC of pooled training at every setting (Figure 6.2). AUC rises with the setting for all models because wider spreads in age, BMI and glucose make diabetic and non-diabetic patients easier to separate; the comparison to read is the gap between the lines, not the height. The gap between federated and average single-hospital AUC stayed close to 0.007 to 0.010. The lowest single-hospital AUC in each cohort averaged 0.834 at setting 0 and 0.845 at setting 1.5, so the weakest hospital was always the one with most to gain.</p>
<figure>{het}</figure>
<p class="cap">Figure 6.2: Test AUC as the hospitals' patient populations differ more</p>
<p>Plain FedAvg coped well here. This is expected for logistic regression, whose loss is convex and in which every simulated hospital follows the same underlying risk relationship; harder cases, such as hospitals that measure or label differently, are not tested.</p>
<h2>6.6 Cost of privacy noise</h2>
<p>Noise was varied with the other settings at their defaults. Averaged over five cohorts, final federated AUC was 0.855 with no noise and with &sigma; 0.25, 0.851 with &sigma; 0.5, 0.839 with &sigma; 1 and 0.822 with &sigma; 1.5. Figure 6.3 shows the loss against the no-noise model.</p>
<figure>{sigma_chart()}</figure>
<p class="cap">Figure 6.3: AUC lost to privacy noise, mean of 5 cohorts (mean gain from federating over 10 cohorts shown as dashed line)</p>
<p>Noise up to &sigma; 0.5 costs 0.4 points or less, which is smaller than the 0.7-point gain from federating, so the hospitals still come out ahead. At &sigma; 1 the cost (1.6 points) exceeds the gain, and a hospital would do better training alone. Because the noise is divided by the number of hospitals, a larger network could use a larger &sigma; for the same loss. The seed 2024 cohort, used in the interactive page's privacy chart, shows the same pattern with slightly different numbers (0.6 points at &sigma; 0.5 and 2.4 points at &sigma; 1).</p>
<h2>6.7 Learned risk factors</h2>
<p>The coefficients of the federated and pooled models agree closely. For the default cohort the federated weights for glucose, BMI, age and pedigree function are 1.30, 0.66, 0.51 and 0.42 (pooled: 1.30, 0.70, 0.48 and 0.36), the largest in both models and in the same order for glucose and BMI. The federated model therefore finds the same risk factors without seeing the combined data.</p>
</div>

<div class="page">
<h1>7. Limitations</h1>
<ul>
<li><b>Synthetic data.</b> Labels come from one logistic model, so the logistic regression is correctly specified. Real records contain missing values, inconsistent coding and non-linear effects.</li>
<li><b>Shared underlying risk.</b> All simulated hospitals follow the same risk relationship; they differ only in patient mix. Real hospitals also differ in measurement methods, equipment and labelling practice.</li>
<li><b>Small gains.</b> Each hospital has at least 248 patients, so single-site models already do well and the gain from federating is under one AUC point on average. Smaller sites or rarer outcomes would probably gain more, but this was not tested.</li>
<li><b>Illustrative privacy.</b> The clipping-and-noise step has no formal (&epsilon;, &delta;) accounting, assumes a trusted coordinator, and is applied to the aggregate rather than to each update. It shows the accuracy cost of noise, not a privacy guarantee. Secure aggregation is not implemented.</li>
<li><b>Limited model and metrics.</b> Only logistic regression is used, and only AUC and accuracy are reported; calibration and fairness across hospitals are not assessed.</li>
<li><b>Ideal network.</b> Every hospital takes part in every round and none fails or drops out.</li>
<li><b>Language.</b> The simulation is written in JavaScript so that it runs in a browser; the course in which this report is submitted is a Python course, and a Python version would be a natural extension.</li>
</ul>

<h1>8. Conclusion and Future Work</h1>
<h2>8.1 Conclusion</h2>
<p>The project built an interactive federated learning simulation for diabetic risk prediction and used it to study how far hospitals can cooperate without sharing records. In ten simulated cohorts, a model trained by federated averaging matched a model trained on pooled records (mean AUC 0.857 against 0.858) and beat the average hospital working alone (0.850) in every cohort. It did so while sending only nine numbers per hospital per round. The result held as the hospitals' patient populations were made more different, and the hospital with the weakest local model gained most. Training converged in a handful of rounds, and more local epochs cut the rounds needed from about seven to about one.</p>
<p>Privacy protection has a price: modest noise cost less than the gain from federating, but stronger noise removed the benefit. The simulation lets this trade-off be examined directly by adjusting one slider. The findings come from synthetic data and an illustrative noise mechanism, and should be confirmed on real data before drawing clinical or policy conclusions.</p>
<h2>8.2 Future work</h2>
<ol>
<li>Repeat the experiments on the real Pima dataset split across virtual sites, and on a de-identified multi-site clinical dataset if one can be obtained.</li>
<li>Add secure aggregation and formal differential privacy accounting, so that a privacy budget (&epsilon;, &delta;) can be reported.</li>
<li>Implement FedProx and personalised federated learning, and test hospitals with different measurement practices.</li>
<li>Compare other models, such as gradient-boosted trees and small neural networks.</li>
<li>Add calibration and per-hospital fairness measures, and simulate hospitals dropping out during training.</li>
<li>Write a Python reference implementation with NumPy so that it can be extended and used in the course.</li>
</ol>

<h1>References</h1>
<ol style="font-size:10.5pt">
<li>McMahan, H. B., Moore, E., Ramage, D., Hampson, S. and Aguera y Arcas, B. (2017). Communication-Efficient Learning of Deep Networks from Decentralized Data. <i>Proceedings of the 20th International Conference on Artificial Intelligence and Statistics (AISTATS)</i>, PMLR 54.</li>
<li>Li, T., Sahu, A. K., Talwalkar, A. and Smith, V. (2020). Federated Learning: Challenges, Methods, and Future Directions. <i>IEEE Signal Processing Magazine</i>, 37(3), 50-60.</li>
<li>Li, T., Sahu, A. K., Zaheer, M., Sanjabi, M., Talwalkar, A. and Smith, V. (2020). Federated Optimization in Heterogeneous Networks. <i>Proceedings of Machine Learning and Systems (MLSys)</i>, 2.</li>
<li>Kairouz, P. et al. (2021). Advances and Open Problems in Federated Learning. <i>Foundations and Trends in Machine Learning</i>, 14(1-2), 1-210.</li>
<li>Dwork, C. and Roth, A. (2014). The Algorithmic Foundations of Differential Privacy. <i>Foundations and Trends in Theoretical Computer Science</i>, 9(3-4), 211-407.</li>
<li>Abadi, M. et al. (2016). Deep Learning with Differential Privacy. <i>Proceedings of the ACM SIGSAC Conference on Computer and Communications Security (CCS)</i>, 308-318.</li>
<li>Bonawitz, K. et al. (2017). Practical Secure Aggregation for Privacy-Preserving Machine Learning. <i>Proceedings of the ACM SIGSAC Conference on Computer and Communications Security (CCS)</i>, 1175-1191.</li>
<li>Smith, J. W., Everhart, J. E., Dickson, W. C., Knowler, W. C. and Johannes, R. S. (1988). Using the ADAP Learning Algorithm to Forecast the Onset of Diabetes Mellitus. <i>Proceedings of the Annual Symposium on Computer Application in Medical Care</i>, 261-265.</li>
<li>Hanley, J. A. and McNeil, B. J. (1982). The Meaning and Use of the Area under a Receiver Operating Characteristic (ROC) Curve. <i>Radiology</i>, 143(1), 29-36.</li>
</ol>
</div>
'''

HEADS=[('1. Introduction',0),('2. Literature Review',0),('3. System Analysis and Design',0),('4. Methodology',0),('5. Implementation',0),('6. Results and Discussion',0),('7. Limitations',0),('8. Conclusion and Future Work',0),('References',0)]
SUBS=[('1.1 Background',1),('1.2 Federated learning in brief',1),('1.3 Problem statement',1),('1.4 Objectives',1),('1.5 Scope',1),('1.6 Organisation of the report',1),
('2.1 Federated averaging',1),('2.2 Challenges and open problems',1),('2.3 Heterogeneous data',1),('2.4 Privacy of model updates',1),('2.5 Data and evaluation',1),('2.6 Gap addressed',1),
('3.1 Requirements',1),('3.2 Architecture',1),('3.3 One round of training',1),('3.4 Technology choices',1),
('4.1 Synthetic patients',1),('4.2 Model and local training',1),('4.3 Federated averaging with clipping and noise',1),('4.4 Baselines',1),('4.5 Evaluation',1),
('5.1 Structure of the program',1),('5.2 The federated round',1),('5.3 Evaluation by ranks',1),('5.4 User interface',1),('5.5 Running the application',1),
('6.1 Default cohort',1),('6.2 Convergence',1),('6.3 Repeated cohorts',1),('6.4 Number of hospitals and local epochs',1),('6.5 Differences between hospitals',1),('6.6 Cost of privacy noise',1),('6.7 Learned risk factors',1),
('8.1 Conclusion',1),('8.2 Future work',1)]
ORDER=['1. Introduction','1.1','1.2','1.3','1.4','1.5','1.6','2. Literature Review','2.1','2.2','2.3','2.4','2.5','2.6','3. System','3.1','3.2','3.3','3.4','4. Methodology','4.1','4.2','4.3','4.4','4.5','5. Implementation','5.1','5.2','5.3','5.4','5.5','6. Results','6.1','6.2','6.3','6.4','6.5','6.6','6.7','7. Limitations','8. Conclusion','8.1','8.2','References']
ALL={h:l for h,l in HEADS+SUBS}
def entries():
    out=[]
    for k in ORDER:
        for h in ALL:
            if h.startswith(k): out.append((h,ALL[h])); break
    # front items
    return out

def toc_html(pages):
    rows=[]
    for h,l in entries():
        p=pages.get(h,'')
        rows.append(f'<tr class="{"sub" if l else ""}"><td>{h}</td><td class="pg">{p}</td></tr>')
    return '<table class="toc">'+''.join(rows)+'</table>'

def render(pages, out_body, out_cover):
    html_cover=f'<!doctype html><html><head><meta charset="utf-8"><style>{STYLE}</style></head><body>{cover()}</body></html>'
    html_body=f'<!doctype html><html><head><meta charset="utf-8"><style>{STYLE}</style></head><body><div style="padding:0">{ (front()+body()).replace("@@TOC@@",toc_html(pages)) }</div></body></html>'
    open('cover.html','w').write(html_cover); open('body.html','w').write(html_body)
    with sync_playwright() as p:
        b=p.chromium.launch(); pg=b.new_page()
        pg.goto('file://'+HERE+'/cover.html'); pg.pdf(path=out_cover,format='A4',print_background=True,margin={'top':'0','bottom':'0','left':'0','right':'0'})
        pg.goto('file://'+HERE+'/body.html')
        foot='<div style="width:100%;text-align:center;font-size:10px;font-family:Times New Roman,serif"><span class="pageNumber"></span></div>'
        pg.pdf(path=out_body,format='A4',print_background=True,display_header_footer=True,header_template='<span></span>',footer_template=foot,margin={'top':'18mm','bottom':'18mm','left':'20mm','right':'18mm'})
        b.close()

def find_pages(pdf):
    n=int(re.search(r'Pages:\s+(\d+)',subprocess.run(['pdfinfo',pdf],capture_output=True,text=True).stdout).group(1))
    texts=[subprocess.run(['pdftotext','-f',str(i),'-l',str(i),'-layout',pdf,'-'],capture_output=True,text=True).stdout for i in range(1,n+1)]
    toc_i=next(i for i,t in enumerate(texts) if 'table of contents' in t.lower())
    pages={}
    for h,l in entries():
        for i in range(toc_i+1,n):
            if re.search(r'^\s*'+re.escape(h)+r'\s*$',texts[i],re.M) or (l==0 and h in texts[i] and re.search(r'^\s*'+re.escape(h),texts[i],re.M)):
                pages[h]=i+1; break
        else: pages[h]='?'
    return n,pages

if __name__=='__main__':
    render({}, 'body.pdf','cover.pdf')
    n,pages=find_pages('body.pdf')
    render(pages,'body.pdf','cover.pdf')
    n2,pages2=find_pages('body.pdf')
    if pages2!=pages:
        render(pages2,'body.pdf','cover.pdf'); n2,pages2=find_pages('body.pdf')
    subprocess.run(['pdfunite','cover.pdf','body.pdf','Application_Project_Report.pdf'],check=True)
    print('body pages',n2,'total',n2+1); print(pages2)
