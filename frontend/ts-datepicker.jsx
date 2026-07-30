/* ============ WinUI-style CalendarDatePicker (+ range) ============ */
const _WD = DB.WD;            // Пн..Вс
const _MONTHS = DB.MONTHS;
const _MONTHS_SHORT = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'];

function _startOfDay(d){ const x=new Date(d); x.setHours(0,0,0,0); return x; }
function _sameDay(a,b){ return a&&b&&a.getFullYear()===b.getFullYear()&&a.getMonth()===b.getMonth()&&a.getDate()===b.getDate(); }
function _mondayOf(d){ const x=_startOfDay(d); let wd=x.getDay(); wd=wd===0?6:wd-1; x.setDate(x.getDate()-wd); return x; }
function _addDays(d,n){ const x=new Date(d); x.setDate(x.getDate()+n); return x; }
function _between(d,a,b){ const t=_startOfDay(d).getTime(); const lo=Math.min(a.getTime(),b.getTime()); const hi=Math.max(a.getTime(),b.getTime()); return t>lo&&t<hi; }

/* trigger + flyout. props:
   value:{date,range}, today:Date, onPick(date), onRange({start,end}), label, placeholder */
function WinDatePicker({ value, today, onPick, onRange, label, placeholder }){
  const [open,setOpen]=useState(false);
  const [level,setLevel]=useState('days');      // days | months | years
  const [viewDate,setViewDate]=useState(()=> (value&&value.date) || (value&&value.range&&value.range.start) || today || new Date());
  const [rangeMode,setRangeMode]=useState(!!(value&&value.range));
  const [pendingStart,setPendingStart]=useState(null);
  const [hoverDate,setHoverDate]=useState(null);
  const rootRef=useRef(null);

  useEffect(()=>{
    if(!open) return;
    const h=(e)=>{ if(rootRef.current && !rootRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown',h);
    return ()=>document.removeEventListener('mousedown',h);
  },[open]);

  const openFlyout=()=>{
    setViewDate((value&&value.date)||(value&&value.range&&value.range.start)||today||new Date());
    setLevel('days'); setPendingStart(null); setHoverDate(null);
    setRangeMode(!!(value&&value.range));
    setOpen(true);
  };

  const selDate = value&&value.date;
  const selRange = value&&value.range;

  const pickDay=(d)=>{
    if(rangeMode){
      if(!pendingStart){ setPendingStart(d); setHoverDate(d); return; }
      const a=pendingStart, b=d;
      const start=a<=b?a:b, end=a<=b?b:a;
      onRange&&onRange({start:_startOfDay(start), end:_startOfDay(end)});
      setPendingStart(null); setHoverDate(null); setOpen(false);
    } else {
      onPick&&onPick(_startOfDay(d)); setOpen(false);
    }
  };

  const navStep=(dir)=>{
    const x=new Date(viewDate);
    if(level==='days') x.setMonth(x.getMonth()+dir);
    else if(level==='months') x.setFullYear(x.getFullYear()+dir);
    else x.setFullYear(x.getFullYear()+dir*10);
    setViewDate(x);
  };
  const cycleUp=()=> setLevel(l=> l==='days'?'months': l==='months'?'years':'years');

  // ---- header title ----
  let title;
  if(level==='days') title=`${_MONTHS[viewDate.getMonth()]} ${viewDate.getFullYear()}`;
  else if(level==='months') title=`${viewDate.getFullYear()}`;
  else { const dec=Math.floor(viewDate.getFullYear()/10)*10; title=`${dec} – ${dec+9}`; }

  // ---- day grid (6 weeks) ----
  const gridStart=_mondayOf(new Date(viewDate.getFullYear(),viewDate.getMonth(),1));
  const cells=[]; for(let i=0;i<42;i++) cells.push(_addDays(gridStart,i));
  const curMonth=viewDate.getMonth();

  const isRangeEnd=(d)=> (selRange && (_sameDay(d,selRange.start)||_sameDay(d,selRange.end)));
  const inSelRange=(d)=> (selRange && _between(d,selRange.start,selRange.end));
  const inPreview=(d)=> (rangeMode && pendingStart && hoverDate && (_between(d,pendingStart,hoverDate)||_sameDay(d,hoverDate)) && !_sameDay(d,pendingStart));

  return (
    <div ref={rootRef} style={{position:'relative', display:'inline-block'}}>
      {/* trigger — WinUI CalendarDatePicker */}
      <button className="wdp-trigger" onClick={()=> open?setOpen(false):openFlyout()} aria-expanded={open}>
        <span className={'wdp-val'+((label)?'':' ph')}>{label||placeholder||'Выберите дату'}</span>
        <span className="wdp-ic"><Icon d={IC.calendar} size={16}/></span>
      </button>

      {open && (
        <div className="wdp-flyout fade-in" role="dialog">
          <div className="wdp-head">
            <button className="wdp-title" onClick={cycleUp}>{title}</button>
            <div style={{display:'flex', gap:2}}>
              <button className="wdp-navbtn" onClick={()=>navStep(-1)} title="Назад"><Icon d={IC.chevU} size={15}/></button>
              <button className="wdp-navbtn" onClick={()=>navStep(1)} title="Вперёд"><Icon d={IC.chevD} size={15}/></button>
            </div>
          </div>

          {level==='days' && (
            <>
              <div className="wdp-wd">{_WD.map(w=><span key={w}>{w}</span>)}</div>
              <div className="wdp-grid" onMouseLeave={()=>setHoverDate(null)}>
                {cells.map((d,i)=>{
                  const out=d.getMonth()!==curMonth;
                  const isToday=_sameDay(d,today);
                  const isSel=!rangeMode && _sameDay(d,selDate);
                  const rEnd=isRangeEnd(d) || (rangeMode&&_sameDay(d,pendingStart));
                  const band=inSelRange(d)||inPreview(d);
                  return (
                    <button key={i} className={'wdp-day'+(band?' band':'')+(rEnd?' end':'')+(isSel?' sel':'')+(out?' out':'')+(isToday&&!isSel&&!rEnd?' today':'')}
                      onMouseEnter={()=> rangeMode&&pendingStart&&setHoverDate(d)}
                      onClick={()=>pickDay(d)}>
                      <span>{d.getDate()}</span>
                    </button>
                  );
                })}
              </div>
            </>
          )}

          {level==='months' && (
            <div className="wdp-mgrid">
              {_MONTHS_SHORT.map((mn,m)=>{
                const on=m===viewDate.getMonth();
                return <button key={m} className={'wdp-cell'+(on?' sel':'')}
                  onClick={()=>{ const x=new Date(viewDate); x.setMonth(m); setViewDate(x); setLevel('days'); }}>{mn}</button>;
              })}
            </div>
          )}

          {level==='years' && (
            <div className="wdp-mgrid">
              {(()=>{ const dec=Math.floor(viewDate.getFullYear()/10)*10; const arr=[];
                for(let y=dec-1;y<=dec+10;y++) arr.push(y); return arr.map(y=>{
                  const on=y===viewDate.getFullYear(); const out=y<dec||y>dec+9;
                  return <button key={y} className={'wdp-cell'+(on?' sel':'')+(out?' out':'')}
                    onClick={()=>{ const x=new Date(viewDate); x.setFullYear(y); setViewDate(x); setLevel('months'); }}>{y}</button>;
                }); })()}
            </div>
          )}

          <div className="wdp-foot">
            <div className="seg" style={{padding:2}}>
              <button className={rangeMode?'':'on'} onClick={()=>{ setRangeMode(false); setPendingStart(null); }}>Дата</button>
              <button className={rangeMode?'on':''} onClick={()=>{ setRangeMode(true); setPendingStart(null); }}>Диапазон</button>
            </div>
            <button className="wdp-link" onClick={()=>{ setViewDate(new Date(today)); setLevel('days'); if(!rangeMode){ onPick&&onPick(_startOfDay(today)); setOpen(false);} }}>Сегодня</button>
          </div>

          {rangeMode && (
            <div className="wdp-hint">{pendingStart? 'Выберите конечную дату диапазона' : 'Выберите начальную дату диапазона'}</div>
          )}
        </div>
      )}

      <style>{`
        .wdp-trigger{ display:inline-flex; align-items:center; gap:10px; height:34px; padding:0 10px 0 13px;
          border:1px solid var(--border-strong); background:var(--surface); border-radius:6px; cursor:pointer;
          font-family:var(--font); font-size:13.5px; font-weight:600; color:var(--text); min-width:190px;
          transition:border-color .14s, box-shadow .14s; }
        .wdp-trigger:hover{ border-color:var(--text-3); }
        .wdp-trigger[aria-expanded="true"]{ border-color:var(--accent); box-shadow:0 0 0 3px var(--accent-ring); }
        .wdp-val{ flex:1; text-align:left; white-space:nowrap; }
        .wdp-val.ph{ color:var(--text-3); font-weight:500; }
        .wdp-ic{ display:flex; color:var(--text-3); border-left:1px solid var(--border); padding-left:9px; height:20px; align-items:center; }

        .wdp-flyout{ position:absolute; top:calc(100% + 6px); left:0; z-index:60; width:288px;
          background:var(--surface); border:1px solid var(--border); border-radius:10px;
          box-shadow:var(--shadow-lg); padding:10px; }
        .wdp-head{ display:flex; align-items:center; justify-content:space-between; margin-bottom:6px; }
        .wdp-title{ border:0; background:transparent; font-family:var(--font); font-size:14px; font-weight:700;
          color:var(--text); cursor:pointer; padding:6px 8px; border-radius:6px; }
        .wdp-title:hover{ background:var(--surface-2); }
        .wdp-navbtn{ width:30px; height:30px; border:0; background:transparent; border-radius:6px; cursor:pointer;
          color:var(--text-2); display:flex; align-items:center; justify-content:center; }
        .wdp-navbtn:hover{ background:var(--surface-2); color:var(--text); }

        .wdp-wd{ display:grid; grid-template-columns:repeat(7,1fr); margin-bottom:2px; }
        .wdp-wd span{ text-align:center; font-size:11px; font-weight:700; color:var(--text-3); padding:4px 0; }
        .wdp-grid{ display:grid; grid-template-columns:repeat(7,1fr); gap:0; }
        .wdp-day{ position:relative; height:34px; border:0; background:transparent; cursor:pointer; padding:0;
          display:flex; align-items:center; justify-content:center; }
        .wdp-day > span{ width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center;
          font-size:13px; font-weight:600; color:var(--text); font-variant-numeric:tabular-nums; transition:background .1s; }
        .wdp-day:hover > span{ background:var(--surface-3); }
        .wdp-day.out > span{ color:var(--text-3); opacity:.55; }
        .wdp-day.today > span{ box-shadow:inset 0 0 0 1.5px var(--accent); color:var(--accent-strong); }
        .wdp-day.sel > span, .wdp-day.end > span{ background:var(--accent)!important; color:#fff; }
        .wdp-day.band::before{ content:''; position:absolute; inset:2px -1px; background:var(--accent-soft); }
        .wdp-day.band.end::before{ display:none; }
        .wdp-day.band > span{ position:relative; z-index:1; }
        .wdp-day.end{ z-index:1; }
        .wdp-day.end::after{ content:''; position:absolute; inset:2px -1px; background:var(--accent-soft); z-index:0; }
        .wdp-day.end > span{ position:relative; z-index:2; }

        .wdp-mgrid{ display:grid; grid-template-columns:repeat(4,1fr); gap:4px; padding:4px 0; }
        .wdp-cell{ height:46px; border:0; background:transparent; border-radius:7px; cursor:pointer;
          font-family:var(--font); font-size:13px; font-weight:600; color:var(--text); font-variant-numeric:tabular-nums; }
        .wdp-cell:hover{ background:var(--surface-2); }
        .wdp-cell.sel{ background:var(--accent); color:#fff; }
        .wdp-cell.out{ color:var(--text-3); opacity:.5; }

        .wdp-foot{ display:flex; align-items:center; justify-content:space-between; gap:8px;
          margin-top:8px; padding-top:8px; border-top:1px solid var(--border); }
        .wdp-foot .seg button{ padding:5px 11px; font-size:12.5px; }
        .wdp-link{ border:0; background:transparent; color:var(--accent-strong); font-family:var(--font);
          font-size:13px; font-weight:600; cursor:pointer; padding:5px 8px; border-radius:6px; }
        .wdp-link:hover{ background:var(--accent-soft); }
        .wdp-hint{ font-size:11.5px; color:var(--text-3); text-align:center; margin-top:6px; }
      `}</style>
    </div>
  );
}

Object.assign(window, { WinDatePicker });
