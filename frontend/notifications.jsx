/* ============ Notifications panel (bell dropdown) ============ */
const NOTIF_META = {
  approval:{ icon:'check',    color:'var(--green)',  bg:'var(--green-soft)'  },
  doc:     { icon:'fileText', color:'var(--accent)', bg:'var(--accent-soft)' },
  chat:    { icon:'chat',     color:'var(--violet)', bg:'var(--violet-soft)' },
  deadline:{ icon:'flag',     color:'var(--amber)',  bg:'var(--amber-soft)'  },
  mention: { icon:'hash',     color:'var(--accent)', bg:'var(--accent-soft)' },
  password:{ icon:'key',      color:'var(--amber)',  bg:'var(--amber-soft)'  },
};

function NotificationsPanel({ items, onNavigate, onReadAll, onRead, onClose }){
  const today=items.filter(n=>n.today);
  const earlier=items.filter(n=>!n.today);

  const Row=({n})=>{
    const m=NOTIF_META[n.type]||NOTIF_META.doc;
    return (
      <button onClick={()=>{ onRead(n.id); onNavigate(n.target); }} style={{display:'flex', gap:12, width:'100%', textAlign:'left',
        padding:'11px 14px', border:'none', background:n.read?'transparent':'var(--accent-softer)', cursor:'pointer', borderRadius:10, transition:'.12s', position:'relative'}}
        onMouseEnter={e=>e.currentTarget.style.background='var(--surface-2)'}
        onMouseLeave={e=>e.currentTarget.style.background=n.read?'transparent':'var(--accent-softer)'}>
        <span style={{width:34,height:34,borderRadius:9,flex:'none',background:m.bg,color:m.color,display:'flex',alignItems:'center',justifyContent:'center'}}>
          <Icon d={IC[m.icon]} size={17}/>
        </span>
        <div style={{flex:1, minWidth:0}}>
          <div style={{fontWeight:600, fontSize:13, lineHeight:1.3}}>{n.title}</div>
          <div className="muted" style={{fontSize:12, lineHeight:1.35, marginTop:2}}>{n.text}</div>
          <div className="muted" style={{fontSize:11, marginTop:4}}>{n.time}</div>
        </div>
        {!n.read && <span style={{width:8,height:8,borderRadius:50,background:'var(--accent)',flex:'none',marginTop:4}}/>}
      </button>
    );
  };

  return (
    <div className="card fade-in" style={{position:'absolute', top:'100%', right:0, marginTop:8, width:380, maxWidth:'90vw', zIndex:60,
      boxShadow:'var(--shadow-lg)', padding:0, overflow:'hidden'}}>
      <div style={{display:'flex', alignItems:'center', justifyContent:'space-between', padding:'14px 16px', borderBottom:'1px solid var(--border)'}}>
        <h3 style={{fontSize:15}}>Уведомления</h3>
        <button className="btn ghost sm" onClick={onReadAll} style={{color:'var(--accent-strong)'}}><Icon d={IC.check} size={14}/>Прочитать все</button>
      </div>
      <div style={{maxHeight:440, overflowY:'auto', padding:8}}>
        {today.length>0 && <div className="muted" style={{fontSize:10.5, fontWeight:700, letterSpacing:'.05em', textTransform:'uppercase', padding:'6px 10px 4px'}}>Сегодня</div>}
        {today.map(n=><Row key={n.id} n={n}/>)}
        {earlier.length>0 && <div className="muted" style={{fontSize:10.5, fontWeight:700, letterSpacing:'.05em', textTransform:'uppercase', padding:'12px 10px 4px'}}>Ранее</div>}
        {earlier.map(n=><Row key={n.id} n={n}/>)}
        {items.length===0 && <div className="muted" style={{padding:'30px 16px', textAlign:'center', fontSize:13}}>Новых уведомлений нет</div>}
      </div>
    </div>
  );
}

Object.assign(window, { NotificationsPanel });
