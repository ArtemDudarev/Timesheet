/* ============ SHARED UI: icons, charts, shell ============ */
const { useState, useEffect, useRef, useMemo } = React;

/* ---------- icons (stroke) ---------- */
function Icon({ d, size=18, fill=false, stroke=1.8, style }){
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill={fill?'currentColor':'none'}
         stroke={fill?'none':'currentColor'} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" style={style}>
      {Array.isArray(d) ? d.map((p,i)=><path key={i} d={p}/>) : <path d={d}/>}
    </svg>
  );
}
const IC = {
  grid:'M4 4h7v7H4zM13 4h7v7h-7zM13 13h7v7h-7zM4 13h7v7H4z',
  calendar:['M3 5h18v16H3z','M3 9h18','M8 3v4M16 3v4'],
  user:['M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z','M4 20a8 8 0 0 1 16 0'],
  folder:'M3 6a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z',
  chart:['M4 20V4','M4 20h16','M8 16v-5M13 16V8M18 16v-9'],
  users:['M9 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Z','M2 20a7 7 0 0 1 14 0','M16 4a3.5 3.5 0 0 1 0 7M22 20a7 7 0 0 0-5-6.7'],
  bell:['M18 9a6 6 0 1 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9','M10.5 21a2 2 0 0 0 3 0'],
  search:['M11 11a7 7 0 1 0 0-14 7 7 0 0 0 0 14Z','M21 21l-4.3-4.3'],
  plus:'M12 5v14M5 12h14',
  check:'M5 12l5 5L20 6',
  x:'M6 6l12 12M18 6L6 18',
  chevL:'M15 6l-6 6 6 6',
  chevR:'M9 6l6 6-6 6',
  chevD:'M6 9l6 6 6-6',
  download:['M12 4v11','M8 11l4 4 4-4','M5 20h14'],
  filter:'M3 5h18l-7 8v6l-4-2v-4z',
  clock:['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z','M12 7v5l3 2'],
  logout:['M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4','M10 17l5-5-5-5','M15 12H3'],
  settings:['M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z','M19.4 13a1.6 1.6 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.6 1.6 0 0 0-2.7 1.1V21a2 2 0 1 1-4 0v-.2A1.6 1.6 0 0 0 7 19.3a1.6 1.6 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.6 1.6 0 0 0-1.1-2.7H1a2 2 0 1 1 0-4h.2A1.6 1.6 0 0 0 2.7 7a1.6 1.6 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.6 1.6 0 0 0 1.8.3H7a1.6 1.6 0 0 0 1-1.5V1a2 2 0 1 1 4 0v.2a1.6 1.6 0 0 0 1 1.5 1.6 1.6 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.6 1.6 0 0 0-.3 1.8V7a1.6 1.6 0 0 0 1.5 1H21a2 2 0 1 1 0 4h-.2a1.6 1.6 0 0 0-1.4 1Z'],
  mail:['M3 5h18v14H3z','M3 6l9 7 9-7'],
  phone:'M6.6 10.8a15.6 15.6 0 0 0 6.6 6.6l2.2-2.2a1 1 0 0 1 1-.24 11.4 11.4 0 0 0 3.6.6 1 1 0 0 1 1 1V20a1 1 0 0 1-1 1A17 17 0 0 1 3 4a1 1 0 0 1 1-1h3.5a1 1 0 0 1 1 1c0 1.25.2 2.45.6 3.6a1 1 0 0 1-.25 1z',
  briefcase:['M4 8h16v12H4z','M9 8V5h6v3'],
  trend:['M3 17l6-6 4 4 8-8','M15 7h6v6'],
  edit:['M4 20h4l10-10-4-4L4 16z','M14 6l4 4'],
  send:'M22 2L11 13M22 2l-7 20-4-9-9-4z',
  dots:'M12 5.5h.01M12 12h.01M12 18.5h.01',
  menu:'M4 6h16M4 12h16M4 18h16',
  flag:['M5 21V4','M5 4h11l-1.5 3.5L16 11H5'],
  target:['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z','M12 16a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z','M12 12h.01'],
  file:['M6 2h8l4 4v16H6z','M14 2v4h4'],
  fileText:['M6 2h8l4 4v16H6z','M14 2v4h4','M9 13h6M9 17h6M9 9h2'],
  chat:['M21 12a8 8 0 0 1-11.5 7.2L4 21l1.8-5.5A8 8 0 1 1 21 12Z'],
  hash:['M5 9h14M5 15h14M10 4l-2 16M16 4l-2 16'],
  paperclip:'M21 12l-8.5 8.5a4 4 0 0 1-6-6L15 6a2.5 2.5 0 0 1 4 4l-9 9a1 1 0 0 1-1.5-1.5L16 10',
  pen:['M4 20h4l10-10-4-4L4 16z','M13.5 6.5l4 4'],
  signature:['M3 17c3 0 3-9 6-9s2 9 5 9 3-4 6-4','M3 21h18'],
  shield:['M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z','M9 12l2 2 4-4'],
  inbox:['M3 12h5l2 3h4l2-3h5','M5 5h14l2 7v7H3v-7z'],
  smile:['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z','M8.5 14a4 4 0 0 0 7 0','M9 9h.01M15 9h.01'],
  attach:['M12 5v14M5 12h14'],
  key:['M21 2l-2 2m-7.61 7.61a5.5 5.5 0 1 1-7.778 7.778 5.5 5.5 0 0 1 7.777-7.777zm0 0L15.5 7.5m0 0 3 3L22 7l-3-3m-3.5 3.5L19 4'],
  copy:['M8 4H6a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h8a2 2 0 0 0 2-2v-2','M16 4h2a2 2 0 0 1 2 2v8','M8 4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v4H8z'],
  trash:['M3 6h18','M8 6V4h8v2','M19 6l-1 14H6L5 6'],
};

/* ---------- avatar ---------- */
function initials(name){ return name.split(' ').map(w=>w[0]).slice(0,2).join('').toUpperCase(); }
function hueFor(id){ const codes=[250,295,155,75,22,210,330]; let s=0; for(const c of id) s+=c.charCodeAt(0); return codes[s%codes.length]; }
function Avatar({ id, name, size=36, ring, imageUrl }){
  const bg = `oklch(0.58 0.13 ${hueFor(id||name)})`;
  if(imageUrl){
    return (
      <span className="avatar" style={{ width:size, height:size, background:bg,
        boxShadow: ring ? '0 0 0 2px var(--surface), 0 0 0 4px var(--border)' : 'none' }}>
        <img src={imageUrl} alt={name} style={{width:'100%',height:'100%',objectFit:'cover',borderRadius:'50%'}}/>
      </span>
    );
  }
  return (
    <span className="avatar" style={{ width:size, height:size, background:bg, fontSize:size*0.38,
      boxShadow: ring ? '0 0 0 2px var(--surface), 0 0 0 4px var(--border)' : 'none' }}>
      {initials(name)}
    </span>
  );
}

/* ---------- mini charts (SVG) ---------- */
function Sparkline({ data, w=120, h=34, color='var(--accent)' }){
  const max=Math.max(...data), min=Math.min(...data);
  const rng=max-min||1;
  const pts=data.map((v,i)=>[ (i/(data.length-1))*w, h-4-((v-min)/rng)*(h-8) ]);
  const path=pts.map((p,i)=>(i?'L':'M')+p[0].toFixed(1)+' '+p[1].toFixed(1)).join(' ');
  const area=path+` L${w} ${h} L0 ${h} Z`;
  const gid='sp'+Math.random().toString(36).slice(2,7);
  return (
    <svg width={w} height={h} style={{display:'block'}}>
      <defs><linearGradient id={gid} x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor={color} stopOpacity="0.18"/><stop offset="1" stopColor={color} stopOpacity="0"/>
      </linearGradient></defs>
      <path d={area} fill={`url(#${gid})`}/>
      <path d={path} fill="none" stroke={color} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx={pts[pts.length-1][0]} cy={pts[pts.length-1][1]} r="2.6" fill={color}/>
    </svg>
  );
}

function Donut({ value, size=120, stroke=13, color='var(--accent)', track='var(--surface-3)', label, sub }){
  const r=(size-stroke)/2, c=2*Math.PI*r;
  const off=c*(1-Math.min(value,1));
  return (
    <div style={{position:'relative', width:size, height:size}}>
      <svg width={size} height={size} style={{transform:'rotate(-90deg)'}}>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={track} strokeWidth={stroke}/>
        <circle cx={size/2} cy={size/2} r={r} fill="none" stroke={color} strokeWidth={stroke}
          strokeDasharray={c} strokeDashoffset={off} strokeLinecap="round"
          style={{transition:'stroke-dashoffset .6s ease'}}/>
      </svg>
      <div style={{position:'absolute', inset:0, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center'}}>
        <div style={{fontWeight:800, fontSize:size*0.21, letterSpacing:'-.02em'}} className="tnum">{label}</div>
        {sub && <div className="muted" style={{fontSize:11}}>{sub}</div>}
      </div>
    </div>
  );
}

/* horizontal bar chart */
function BarsH({ items, max, fmt=(v)=>v, height=null }){
  const m = max || Math.max(...items.map(i=>i.value), 1);
  return (
    <div style={{display:'flex', flexDirection:'column', gap:12}}>
      {items.map((it,i)=>(
        <div key={i} style={{display:'grid', gridTemplateColumns:'140px 1fr 56px', alignItems:'center', gap:12}}>
          <div style={{display:'flex', alignItems:'center', gap:8, minWidth:0}}>
            {it.dot && <span style={{width:8,height:8,borderRadius:3,background:it.dot,flex:'none'}}/>}
            <span style={{fontSize:13, fontWeight:500, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{it.label}</span>
          </div>
          <div style={{height:9, borderRadius:999, background:'var(--surface-3)', overflow:'hidden'}}>
            <div style={{height:'100%', width:(it.value/m*100)+'%', background:it.color||'var(--accent)', borderRadius:999, transition:'width .5s ease'}}/>
          </div>
          <div className="mono" style={{fontSize:12.5, fontWeight:600, textAlign:'right', color:it.over?'var(--red)':'var(--text-2)'}}>{fmt(it.value)}</div>
        </div>
      ))}
    </div>
  );
}

/* vertical grouped bars (plan/fact) */
function ColumnsPF({ data, h=180 }){
  const max=Math.max(...data.flatMap(d=>[d.plan,d.fact]),1);
  return (
    <div style={{display:'flex', alignItems:'flex-end', gap:18, height:h, padding:'0 4px'}}>
      {data.map((d,i)=>(
        <div key={i} style={{flex:1, display:'flex', flexDirection:'column', alignItems:'center', gap:8, height:'100%', justifyContent:'flex-end'}}>
          <div style={{display:'flex', alignItems:'flex-end', gap:5, height:'100%', width:'100%', justifyContent:'center'}}>
            <div title={'План '+d.plan} style={{width:'34%', height:(d.plan/max*100)+'%', background:'var(--surface-3)', borderRadius:'5px 5px 0 0', transition:'height .5s'}}/>
            <div title={'Факт '+d.fact} style={{width:'34%', height:(d.fact/max*100)+'%', background:'var(--accent)', borderRadius:'5px 5px 0 0', transition:'height .5s'}}/>
          </div>
          <div className="muted" style={{fontSize:11.5, fontWeight:500}}>{d.label}</div>
        </div>
      ))}
    </div>
  );
}

/* ---------- status helpers ---------- */
const PROJ_STATUS = {
  active:{ label:'В работе',     cls:'green'  },
  risk:  { label:'Под риском',   cls:'amber'  },
  paused:{ label:'Приостановлен',cls:''       },
  done:  { label:'Завершён',     cls:'accent' },
};
const APPR_STATUS = {
  pending: { label:'На согласовании', cls:'amber'  },
  approved:{ label:'Утверждён',       cls:'green'  },
  rejected:{ label:'Отклонён',        cls:'red'    },
  draft:   { label:'Черновик',        cls:''       },
};

function StatCard({ label, value, sub, icon, trend, accent }){
  return (
    <div className="card" style={{padding:'16px 18px', display:'flex', flexDirection:'column', gap:10}}>
      <div style={{display:'flex', alignItems:'center', justifyContent:'space-between'}}>
        <span className="muted" style={{fontSize:12.5, fontWeight:600}}>{label}</span>
        {icon && <span style={{color:accent?'var(--accent)':'var(--text-3)', display:'flex'}}><Icon d={IC[icon]} size={17}/></span>}
      </div>
      <div style={{display:'flex', alignItems:'baseline', gap:8}}>
        <span style={{fontSize:27, fontWeight:800, letterSpacing:'-.02em'}} className="tnum">{value}</span>
        {trend!=null && (
          <span style={{fontSize:12.5, fontWeight:700, color:trend>=0?'var(--green)':'var(--red)', display:'inline-flex', alignItems:'center', gap:2}}>
            {trend>=0?'↑':'↓'}{Math.abs(trend)}%
          </span>
        )}
      </div>
      {sub && <span className="muted" style={{fontSize:12}}>{sub}</span>}
    </div>
  );
}

/* ---------- toast ---------- */
function useToast(){
  const [toast,setToast]=useState(null);
  const show=(msg,kind='ok')=>{ setToast({msg,kind,k:Date.now()}); };
  useEffect(()=>{ if(!toast)return; const t=setTimeout(()=>setToast(null),2600); return ()=>clearTimeout(t); },[toast]);
  const node = toast && (
    <div style={{position:'fixed', bottom:24, left:'50%', transform:'translateX(-50%)', zIndex:200}} className="fade-in">
      <div className="card" style={{display:'flex', alignItems:'center', gap:10, padding:'11px 16px', boxShadow:'var(--shadow-lg)', borderColor:'var(--border-strong)'}}>
        <span style={{display:'flex', color:toast.kind==='ok'?'var(--green)':'var(--accent)'}}>
          <Icon d={IC.check} size={17} stroke={2.4}/>
        </span>
        <span style={{fontSize:13.5, fontWeight:600}}>{toast.msg}</span>
      </div>
    </div>
  );
  return [node, show];
}

Object.assign(window, {
  useState, useEffect, useRef, useMemo,
  Icon, IC, Avatar, initials, Sparkline, Donut, BarsH, ColumnsPF,
  PROJ_STATUS, APPR_STATUS, StatCard, useToast,
});
