/* ============ SCREEN: Таймшит (неделя / месяц / год) — живые данные ============ */
const TS_MONTHS = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
const TS_WD = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];
const mShort = (m)=>['янв','фев','мар','апр','май','июн','июл','авг','сен','окт','ноя','дек'][m];
const monShort = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'];
const tsIso = (y,m,d)=>`${y}-${String(m+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
const tsMonday = (d)=>{ const x=new Date(d); x.setHours(0,0,0,0); let wd=x.getDay(); wd=wd===0?6:wd-1; x.setDate(x.getDate()-wd); return x; };
const tsAdd = (d,n)=>{ const x=new Date(d); x.setDate(x.getDate()+n); return x; };
const perKey = (y,m1)=>`${y}-${m1}`; // m1: 1-12

// Статусы согласования периода (русские значения бэка)
const SUB_STATUS = {
  'Черновик':        { label:'Черновик',        cls:''      },
  'На согласовании': { label:'На согласовании', cls:'amber' },
  'Согласован':      { label:'Согласован',      cls:'green' },
  'Отклонён':        { label:'Отклонён',        cls:'red'   },
};

// Визуализация типов отсутствий (коды absence_service)
const ABS_VISUAL = {
  VACATION: { bg:'var(--violet-soft)', color:'oklch(0.58 0.15 295)', icon:'calendar'  },
  SICK:     { bg:'var(--red-soft)',    color:'var(--red)',           icon:'shield'    },
  TRIP:     { bg:'var(--amber-soft)',  color:'var(--amber)',         icon:'briefcase' },
  DAY_OFF:  { bg:'var(--surface-3)',   color:'oklch(0.55 0.02 255)', icon:'clock'     },
};

// Кэши справочников (живут между открытиями экрана)
let _tsWorkTypeId = null;
const _tsCalCache = {}; // year -> {dateKey: {type, description}}

async function tsWorkTypeId(){
  if(_tsWorkTypeId) return _tsWorkTypeId;
  const types = await API.timesheet.getEntryTypes();
  _tsWorkTypeId = (types.find(t=>t.code==='WORK')||{}).id;
  return _tsWorkTypeId;
}
async function tsCalendar(year){
  if(_tsCalCache[year]) return _tsCalCache[year];
  const rows = await API.timesheet.getCalendar(year);
  const map = {};
  rows.forEach(r=>{ map[r.date] = { type:r.day_type, description:r.description }; });
  _tsCalCache[year] = map;
  return map;
}

function TimesheetScreen({ userId, role, showToast }){
  const sess = API.session()||{perms:[]};
  const perms = new Set(sess.permissions||[]);
  const canViewOthers = perms.has('employee:list');
  const canApprove = perms.has('timesheet:approve_period') || perms.has('timesheet:approve_period_team');
  const TODAY = useMemo(()=>{ const t=new Date(); t.setHours(0,0,0,0); return t; },[]);
  const todayKey = tsIso(TODAY.getFullYear(), TODAY.getMonth(), TODAY.getDate());

  const [viewId,setViewId]=useState(sess.userId);
  const viewingSelf = viewId===sess.userId;
  const readOnly = !viewingSelf;

  const [period,setPeriod]=useState('month');
  const [anchor,setAnchor]=useState(()=>new Date());
  const [range,setRange]=useState(null);

  const [cal,setCal]=useState({});                 // dateKey -> {type, description}
  const [periodsMap,setPeriodsMap]=useState({});   // 'y-m1' -> period
  const [entriesByPeriod,setEntriesByPeriod]=useState({}); // periodId -> entries[]
  const [viewedEmp,setViewedEmp]=useState(null);   // профиль просматриваемого (assignments)
  const [absences,setAbsences]=useState([]);
  const [employees,setEmployees]=useState([]);
  const [localRows,setLocalRows]=useState([]);     // добавленные задачи без записей
  const [collapsed,setCollapsed]=useState(()=>new Set());
  const [loading,setLoading]=useState(true);
  const [saving,setSaving]=useState(0);
  const [empOpen,setEmpOpen]=useState(false);
  const [dialog,setDialog]=useState(null);         // 'submit' | 'reject'
  const [commentDraft,setCommentDraft]=useState('');
  const [taskDetail,setTaskDetail]=useState(null);

  const dayInfo = (date)=>{
    const y=date.getFullYear(), m=date.getMonth(), d=date.getDate();
    let wd=date.getDay(); wd=wd===0?6:wd-1;
    const key=tsIso(y,m,d);
    const c=cal[key];
    // xmlcalendar помечает и обычные выходные как HOLIDAY (без описания) — не считаем их праздниками
    const weekendNoDesc = wd>=5 && !(c&&c.description);
    const holiday=c&&c.type==='HOLIDAY'&&!weekendNoDesc?(c.description||'Праздничный день'):null;
    const short=c&&c.type==='PRE_HOLIDAY'?7:null;
    const weekend=wd>=5;
    const working=!weekend&&!holiday;
    const cap=working?(short||8):0;
    return { y, m, d, date:new Date(y,m,d), wd, label:TS_WD[wd], weekend, holiday, short, working, cap, key, monthName:TS_MONTHS[m] };
  };

  const view = useMemo(()=>{
    if(period==='year' && !range){
      const yr=anchor.getFullYear();
      const cols = TS_MONTHS.map((name,m)=>({ kind:'month', m, y:yr, label:monShort[m], full:name,
        future: new Date(yr,m,1)>TODAY }));
      return { kind:'month', cols, year:yr };
    }
    let start, end;
    if(range){ start=range.start; end=range.end; }
    else if(period==='week'){ start=tsMonday(anchor); end=tsAdd(start,6); }
    else { start=new Date(anchor.getFullYear(),anchor.getMonth(),1); end=new Date(anchor.getFullYear(),anchor.getMonth()+1,0); }
    const cols=[]; let c=new Date(start); c.setHours(0,0,0,0);
    const last=new Date(end); last.setHours(0,0,0,0);
    let guard=0;
    while(c<=last && guard++<400){ cols.push({ kind:'day', ...dayInfo(new Date(c)) }); c.setDate(c.getDate()+1); }
    return { kind:'day', cols, start, end };
  },[period, anchor, range, cal]);

  const cols = view.cols;
  const colW = view.kind==='month' ? 64 : 40;

  // Годы и периоды, нужные текущему виду
  const neededYears = useMemo(()=>{
    const s=new Set();
    if(view.kind==='month') s.add(view.year);
    else cols.forEach(c=>s.add(c.y));
    return [...s];
  },[view]);
  const neededPeriodKeys = useMemo(()=>{
    const s=new Set();
    if(view.kind==='month') for(let m=1;m<=12;m++) s.add(perKey(view.year,m));
    else cols.forEach(c=>s.add(perKey(c.y,c.m+1)));
    return [...s];
  },[view]);

  // ── Загрузка данных ────────────────────────────────────────────────────────
  useEffect(()=>{ let alive=true;
    Promise.all(neededYears.map(tsCalendar)).then(maps=>{
      if(alive) setCal(Object.assign({}, ...maps));
    }).catch(()=>{});
    return ()=>{ alive=false; };
  },[neededYears.join()]);

  useEffect(()=>{ let alive=true;
    if(canViewOthers) API.management.getEmployees().then(l=>{ if(alive) setEmployees(l); }).catch(()=>{});
    return ()=>{ alive=false; };
  },[canViewOthers]);

  // Смена сотрудника: профиль, периоды, отсутствия — с нуля
  useEffect(()=>{ let alive=true;
    setLoading(true); setPeriodsMap({}); setEntriesByPeriod({}); setViewedEmp(null); setAbsences([]); setLocalRows([]);
    Promise.all([
      API.profile.getEmployee(viewId),
      API.timesheet.getPeriods(viewId),
      API.absence.getAbsences({ employee_id:viewId, status:'Согласована' }).catch(()=>[]),
    ]).then(([emp, periods, abs])=>{
      if(!alive) return;
      setViewedEmp(emp);
      const pm={}; periods.forEach(p=>{ pm[perKey(p.year,p.month)]=p; });
      setPeriodsMap(pm);
      setAbsences(abs);
    }).catch(err=>{ if(alive) showToast(err.detail||'Не удалось загрузить табель'); })
      .finally(()=>{ if(alive) setLoading(false); });
    return ()=>{ alive=false; };
  },[viewId]);

  // Подгрузка записей для периодов текущего вида
  useEffect(()=>{ let alive=true;
    const need = neededPeriodKeys.map(k=>periodsMap[k]).filter(p=>p && entriesByPeriod[p.id]===undefined);
    if(!need.length) return;
    Promise.all(need.map(p=>API.timesheet.getEntries(p.id).then(list=>[p.id,list]).catch(()=>[p.id,[]])))
      .then(pairs=>{ if(alive) setEntriesByPeriod(prev=>({ ...prev, ...Object.fromEntries(pairs) })); });
    return ()=>{ alive=false; };
  },[neededPeriodKeys.join(), periodsMap]);

  const reloadPeriod = async (periodId)=>{
    const list = await API.timesheet.getEntries(periodId).catch(()=>[]);
    setEntriesByPeriod(prev=>({ ...prev, [periodId]:list }));
  };
  const reloadPeriodsMeta = async ()=>{
    const periods = await API.timesheet.getPeriods(viewId);
    const pm={}; periods.forEach(p=>{ pm[perKey(p.year,p.month)]=p; });
    setPeriodsMap(pm);
  };

  // ── Ряды из записей ────────────────────────────────────────────────────────
  const assignmentInfo = useMemo(()=>{
    const map={};
    (viewedEmp?.assignments||[]).forEach(a=>{
      map[a.id]={ assignmentId:a.id, projectId:a.project.id, projectName:a.project.name,
        code:a.project.code, color:a.project.color||'var(--accent)', client:a.project.client,
        roleName:a.project_role.name, active:['ACTIVE','EXTENDED'].includes(a.assignment_status.code) };
    });
    return map;
  },[viewedEmp]);

  const rows = useMemo(()=>{
    const map=new Map();
    Object.values(entriesByPeriod).forEach(list=>list.forEach(e=>{
      if(!e.assignment) return; // SICK_LEAVE/VACATION без назначения — не в сетке
      const rowKey=e.assignment.id+'|'+(e.task_name||'');
      let r=map.get(rowKey);
      if(!r){
        r={ key:rowKey, assignmentId:e.assignment.id, projectId:e.assignment.project.id,
            projectName:e.assignment.project.name, task:e.task_name||'Без названия', hours:{}, comment:null, hasEntries:true };
        map.set(rowKey,r);
      }
      const k=e.date_from;
      const cell=r.hours[k]||(r.hours[k]={total:0, entries:[]});
      cell.total+=Number(e.spend_time);
      cell.entries.push(e);
      if(e.comment && !r.comment) r.comment=e.comment;
    }));
    localRows.forEach(lr=>{ if(!map.has(lr.key)) map.set(lr.key, {...lr, hours:{}, comment:null, hasEntries:false}); });
    return [...map.values()];
  },[entriesByPeriod, localRows]);

  // Проекты: из рядов + активные назначения без записей
  const projects = useMemo(()=>{
    const seen=new Map();
    rows.forEach(r=>{
      if(!seen.has(r.projectId)){
        const info=Object.values(assignmentInfo).find(a=>a.projectId===r.projectId);
        seen.set(r.projectId, { id:r.projectId, name:r.projectName, color:info?.color||'var(--accent)', code:info?.code, client:info?.client, assignmentId:info?.assignmentId||r.assignmentId });
      }
    });
    Object.values(assignmentInfo).filter(a=>a.active).forEach(a=>{
      if(!seen.has(a.projectId)) seen.set(a.projectId, { id:a.projectId, name:a.projectName, color:a.color, code:a.code, client:a.client, assignmentId:a.assignmentId });
    });
    return [...seen.values()];
  },[rows, assignmentInfo]);

  const monthTotal=(r,y,m)=>{ let s=0; for(const k in r.hours){ if(+k.slice(0,4)===y && (+k.slice(5,7)-1)===m) s+=r.hours[k].total; } return s; };
  const colVal=(r,col)=> col.kind==='month' ? monthTotal(r,col.y,col.m) : (r.hours[col.key]?.total||0);
  const taskTotal=(r)=> cols.reduce((a,col)=>a+colVal(r,col),0);
  const colTotal=(col)=> rows.reduce((a,r)=>a+colVal(r,col),0);
  // "Безымянная" строка (task_name=null) — часы прямо на проекте, без отдельной задачи;
  // редактируется прямо в шапке проекта, поэтому в список задач её не включаем
  const isNoTaskRow=(r)=>r.key===r.assignmentId+'|';
  const noTaskRowOf=(p)=>rows.find(r=>r.assignmentId===p.assignmentId && isNoTaskRow(r))
    || { key:p.assignmentId+'|', assignmentId:p.assignmentId, projectId:p.id, projectName:p.name, task:'', hours:{}, comment:null, hasEntries:false };
  const tasksOf=(pid)=>rows.filter(r=>r.projectId===pid && !isNoTaskRow(r));
  const projColVal=(pid,col)=>rows.reduce((a,r)=>a+(r.projectId===pid?colVal(r,col):0),0);
  const projTotal=(pid)=>rows.reduce((a,r)=>a+(r.projectId===pid?taskTotal(r):0),0);
  const grand=rows.reduce((a,r)=>a+taskTotal(r),0);
  const fmtH=(v)=>v?+v.toFixed(2):0;

  const periodNorm = useMemo(()=>{
    if(view.kind==='month'){
      let s=0;
      for(let m=0;m<12;m++){ const dim=new Date(view.year,m+1,0).getDate();
        for(let d=1;d<=dim;d++) s+=dayInfo(new Date(view.year,m,d)).cap; }
      return s;
    }
    return cols.reduce((a,c)=>a+(c.cap||0),0);
  },[view, cal]);
  const workdays = useMemo(()=>{
    if(view.kind==='month'){
      let n=0;
      for(let m=0;m<12;m++){ const dim=new Date(view.year,m+1,0).getDate();
        for(let d=1;d<=dim;d++) if(dayInfo(new Date(view.year,m,d)).working) n++; }
      return n;
    }
    return cols.filter(c=>c.working).length;
  },[view, cal]);

  // Отсутствия: dateKey -> код типа
  const absentMap = useMemo(()=>{
    const map={};
    absences.forEach(a=>{
      const s=new Date(a.date_from), e=new Date(a.date_to);
      const cur=new Date(s);
      while(cur<=e){ map[tsIso(cur.getFullYear(),cur.getMonth(),cur.getDate())]=a.absence_type.code; cur.setDate(cur.getDate()+1); }
    });
    return map;
  },[absences]);
  const absType=(k)=>{ const code=absentMap[k]; if(!code) return null; const v=ABS_VISUAL[code]||ABS_VISUAL.DAY_OFF;
    const a=absences.find(x=>x.absence_type.code===code); return { ...v, code, name:a?.absence_type?.name||code }; };

  // ── Статус и редактируемость ───────────────────────────────────────────────
  const anchorPeriod = periodsMap[perKey(anchor.getFullYear(), anchor.getMonth()+1)];
  const subStatus = anchorPeriod?.submission_status || 'Черновик';
  const st = SUB_STATUS[subStatus] || SUB_STATUS['Черновик'];
  const periodClosed = anchorPeriod?.status==='CLOSED';
  const canEditAnchor = viewingSelf && anchorPeriod && !periodClosed && subStatus!=='На согласовании';
  const cellPeriod=(col)=>periodsMap[perKey(col.y, col.m+1)];
  const cellEditable=(col)=>{
    if(readOnly || col.kind!=='day') return false;
    const p=cellPeriod(col);
    return !!p && p.status!=='CLOSED' && p.submission_status!=='На согласовании';
  };

  // ── Действия ───────────────────────────────────────────────────────────────
  const commitCell = async (row, col, raw)=>{
    let v = parseFloat(String(raw).replace(',','.'));
    if(isNaN(v)||v<0) v=0;
    v=Math.min(v,24);
    const cell=row.hours[col.key];
    const old=cell?cell.total:0;
    // Ограничение не на одну ячейку, а на СУММУ за день по всем проектам/задачам —
    // иначе несколько строк по 24ч дают нереальный суммарный день
    const otherRowsTotal = colTotal(col) - old;
    if(otherRowsTotal + v > 24){
      const maxAllowed = Math.max(0, 24 - otherRowsTotal);
      showToast(`За день нельзя списать больше 24 ч (уже ${fmtH(otherRowsTotal)} ч по другим проектам/задачам)`);
      v = maxAllowed;
    }
    if(v===old) return;
    const per=cellPeriod(col);
    if(!per){ showToast('Период не найден'); return; }
    setSaving(s=>s+1);
    try{
      for(const e of (cell?cell.entries:[])) await API.timesheet.deleteEntry(e.timesheet_period_id, e.id);
      if(v>0){
        const typeId=await tsWorkTypeId();
        await API.timesheet.createEntry(per.id, {
          type_id:typeId, assignment_id:row.assignmentId,
          date_from:col.key, date_to:col.key, spend_time:v, task_name:row.task||null,
          comment: row.comment||undefined,
        });
      }
      await reloadPeriod(per.id);
      setLocalRows(ls=>ls.filter(l=>l.key!==row.key)); // ряд теперь живёт в записях
    }catch(err){
      showToast(err.detail||'Не удалось сохранить часы');
      await reloadPeriod(per.id);
    }finally{ setSaving(s=>s-1); }
  };

  const addTask=(proj)=>{
    if(!proj.assignmentId){ showToast('Нет активного назначения на проект'); return; }
    setLocalRows(ls=>{
      let n=1, name='Новая задача';
      const names=new Set(rows.filter(r=>r.assignmentId===proj.assignmentId).map(r=>r.task));
      while(names.has(name)) name='Новая задача '+(++n);
      return [...ls, { key:proj.assignmentId+'|'+name, assignmentId:proj.assignmentId, projectId:proj.id, projectName:proj.name, task:name }];
    });
    setCollapsed(s=>{ const n=new Set(s); n.delete(proj.id); return n; });
  };

  const renameTask = async (row, name)=>{
    const clean=name.trim();
    if(!clean || clean===row.task) return;
    if(!row.hasEntries){
      setLocalRows(ls=>ls.map(l=>l.key===row.key?{...l, task:clean, key:l.assignmentId+'|'+clean}:l));
      return;
    }
    setSaving(s=>s+1);
    try{
      const all=Object.values(row.hours).flatMap(c=>c.entries);
      const touched=new Set();
      for(const e of all){ await API.timesheet.updateEntry(e.timesheet_period_id, e.id, { task_name:clean }); touched.add(e.timesheet_period_id); }
      for(const pid of touched) await reloadPeriod(pid);
    }catch(err){ showToast(err.detail||'Не удалось переименовать'); }
    finally{ setSaving(s=>s-1); }
  };

  const removeTask = async (row)=>{
    if(!row.hasEntries){ setLocalRows(ls=>ls.filter(l=>l.key!==row.key)); return; }
    setSaving(s=>s+1);
    try{
      const all=Object.values(row.hours).flatMap(c=>c.entries);
      const touched=new Set();
      for(const e of all){ await API.timesheet.deleteEntry(e.timesheet_period_id, e.id); touched.add(e.timesheet_period_id); }
      for(const pid of touched) await reloadPeriod(pid);
    }catch(err){ showToast(err.detail||'Не удалось удалить задачу'); }
    finally{ setSaving(s=>s-1); }
  };

  const saveTaskComment = async (row, text)=>{
    if(!row.hasEntries){ showToast('Сначала спишите часы на задачу'); return; }
    setSaving(s=>s+1);
    try{
      const all=Object.values(row.hours).flatMap(c=>c.entries);
      const touched=new Set();
      for(const e of all){ await API.timesheet.updateEntry(e.timesheet_period_id, e.id, { comment:text }); touched.add(e.timesheet_period_id); }
      for(const pid of touched) await reloadPeriod(pid);
      showToast('Комментарий сохранён');
    }catch(err){ showToast(err.detail||'Не удалось сохранить комментарий'); }
    finally{ setSaving(s=>s-1); }
  };

  const doSubmit=async ()=>{
    setDialog(null);
    try{ await API.timesheet.submitPeriod(anchorPeriod.id); await reloadPeriodsMeta(); showToast('Табель отправлен на согласование'); }
    catch(err){ showToast(err.detail||'Не удалось отправить'); }
  };
  const approve=async ()=>{
    try{ await API.timesheet.approvePeriod(anchorPeriod.id); await reloadPeriodsMeta(); showToast('Табель согласован'); }
    catch(err){ showToast(err.detail||'Не удалось согласовать'); }
  };
  const doReject=async ()=>{
    const comment=commentDraft.trim();
    if(!comment){ showToast('Укажите причину отклонения'); return; }
    setDialog(null);
    try{ await API.timesheet.rejectPeriod(anchorPeriod.id, comment); await reloadPeriodsMeta(); showToast('Табель отклонён'); }
    catch(err){ showToast(err.detail||'Не удалось отклонить'); }
  };

  const changePeriod=(p)=>{ setRange(null); setPeriod(p); };
  const stepPeriod=(dir)=>{ setRange(null); setAnchor(a=>{ const x=new Date(a);
    if(period==='week') x.setDate(x.getDate()+dir*7);
    else if(period==='month') x.setMonth(x.getMonth()+dir);
    else x.setFullYear(x.getFullYear()+dir);
    return x; }); };

  const pickerLabel = (()=>{
    if(range){ return `${range.start.getDate()} ${mShort(range.start.getMonth())} – ${range.end.getDate()} ${mShort(range.end.getMonth())} ${range.end.getFullYear()}`; }
    if(period==='week'){ const s=view.start,e=view.end;
      return s.getMonth()===e.getMonth()
        ? `${s.getDate()}–${e.getDate()} ${mShort(s.getMonth())} ${e.getFullYear()}`
        : `${s.getDate()} ${mShort(s.getMonth())} – ${e.getDate()} ${mShort(e.getMonth())} ${e.getFullYear()}`; }
    if(period==='month'){ return `${TS_MONTHS[anchor.getMonth()]} ${anchor.getFullYear()}`; }
    return `${anchor.getFullYear()}`;
  })();

  const empName=(e)=>`${e.first_name} ${e.last_name}`;
  const viewedName = viewedEmp ? empName(viewedEmp) : '…';
  const viewableList = useMemo(()=>{
    const others=employees.filter(e=>e.id!==sess.userId);
    const self=employees.find(e=>e.id===sess.userId);
    return self?[self,...others]:others;
  },[employees, sess.userId]);
  const pct = periodNorm? Math.round(grand/periodNorm*100):0;
  const showRejection = viewingSelf && subStatus==='Отклонён' && anchorPeriod?.rejection_comment;

  if(loading) return (
    <div className="fade-in" style={{display:'flex', flexDirection:'column', gap:16}}>
      <div><div className="skel" style={{width:160, height:26, marginBottom:8}}/><div className="skel" style={{width:300, height:14}}/></div>
      <div className="card" style={{padding:16}}><div className="skel" style={{height:34}}/></div>
      <div className="card" style={{padding:16}}>{[0,1,2,3,4].map(i=><div key={i} className="skel" style={{height:38, marginBottom:8}}/>)}</div>
    </div>
  );

  return (
    <div className="fade-in" style={{display:'flex', flexDirection:'column', gap:16}}>
      <PageHead
        title="Таймшит"
        subtitle={readOnly ? `Табель сотрудника · ${viewedName}` : 'Списание трудозатрат по проектам и задачам'}
        actions={<>
          {saving>0 && <span className="badge" style={{height:30}}><span className="dot" style={{background:'var(--amber)'}}/>Сохранение…</span>}
          {readOnly
            ? <>
                {canApprove && subStatus==='На согласовании' && <button className="btn sm" onClick={()=>{ setCommentDraft(''); setDialog('reject'); }} style={{color:'var(--red)'}}><Icon d={IC.x} size={15}/>Отклонить</button>}
                {canApprove && subStatus==='На согласовании' && <button className="btn sm primary" onClick={approve}><Icon d={IC.check} size={15}/>Согласовать</button>}
              </>
            : (anchorPeriod && !periodClosed && (subStatus==='Черновик'||subStatus==='Отклонён')
                ? <button className="btn sm primary" onClick={()=>setDialog('submit')}><Icon d={IC.send} size={15}/>Отправить на согласование</button>
                : subStatus==='На согласовании'
                  ? <button className="btn sm" disabled style={{opacity:.7}}><Icon d={IC.clock} size={15}/>На согласовании</button>
                  : null)
          }
        </>}/>

      {showRejection && (
        <div style={{padding:'12px 14px', borderRadius:10, background:'var(--red-soft)', border:'1px solid oklch(0.60 0.18 22 / 0.35)', display:'flex', gap:10}}>
          <span style={{color:'var(--red)', flexShrink:0, marginTop:1}}><Icon d={IC.x} size={16}/></span>
          <div style={{fontSize:13, color:'oklch(0.50 0.16 25)'}}><b>Табель отклонён.</b> {anchorPeriod.rejection_comment}</div>
        </div>
      )}

      {/* controls bar */}
      <div className="card" style={{padding:'13px 16px', display:'flex', alignItems:'center', gap:14, flexWrap:'wrap'}}>
        <div className="seg">
          {[['week','Неделя'],['month','Месяц'],['year','Год']].map(([id,lbl])=>(
            <button key={id} className={period===id&&!range?'on':''} onClick={()=>changePeriod(id)}>{lbl}</button>
          ))}
        </div>

        <div style={{display:'flex', alignItems:'center', gap:6}}>
          <button className="btn sm icon" onClick={()=>stepPeriod(-1)} disabled={!!range} style={range?{opacity:.4}:{}}><Icon d={IC.chevL} size={16}/></button>
          <WinDatePicker
            value={range?{range}:{date:anchor}}
            today={TODAY}
            label={pickerLabel}
            onPick={(d)=>{ setRange(null); setAnchor(d); }}
            onRange={(r)=>setRange(r)}/>
          <button className="btn sm icon" onClick={()=>stepPeriod(1)} disabled={!!range} style={range?{opacity:.4}:{}}><Icon d={IC.chevR} size={16}/></button>
        </div>

        {canViewOthers && (
          <div style={{position:'relative'}}>
            <button className="btn sm" onClick={()=>setEmpOpen(o=>!o)} style={{height:34, gap:8, paddingLeft:6}}>
              <Avatar id={viewId} name={viewedName} size={22}/>
              <span style={{fontWeight:600, maxWidth:150, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis'}}>{viewingSelf?'Мой табель':viewedName}</span>
              <Icon d={IC.chevD} size={14} style={{color:'var(--text-3)', marginLeft:-2}}/>
            </button>
            {empOpen && (
              <div className="card fade-in" style={{position:'absolute', top:'100%', left:0, zIndex:40, marginTop:4, width:286, boxShadow:'var(--shadow-lg)', padding:6, maxHeight:340, overflowY:'auto'}}>
                <div className="muted" style={{fontSize:10.5, fontWeight:700, letterSpacing:'.05em', textTransform:'uppercase', padding:'4px 10px 6px'}}>Чей табель</div>
                {viewableList.map(e=>{ const on=e.id===viewId; return (
                  <button key={e.id} onClick={()=>{ setViewId(e.id); setEmpOpen(false); }}
                    style={{display:'flex', alignItems:'center', gap:10, width:'100%', padding:'8px 10px', border:'none', background:on?'var(--accent-soft)':'transparent', borderRadius:8, cursor:'pointer', textAlign:'left'}}
                    onMouseEnter={ev=>{ if(!on) ev.currentTarget.style.background='var(--surface-2)'; }}
                    onMouseLeave={ev=>{ if(!on) ev.currentTarget.style.background='transparent'; }}>
                    <Avatar id={e.id} name={empName(e)} size={30}/>
                    <div style={{minWidth:0, flex:1}}>
                      <div style={{fontWeight:600, fontSize:13}}>{e.id===sess.userId ? empName(e)+' (вы)' : empName(e)}</div>
                      <div className="muted" style={{fontSize:11, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis'}}>{e.user?.email}</div>
                    </div>
                    {on && <Icon d={IC.check} size={15} stroke={2.6} style={{color:'var(--accent-strong)', flex:'none'}}/>}
                  </button>
                );})}
              </div>
            )}
          </div>
        )}

        {range && (
          <button className="badge accent" onClick={()=>setRange(null)} style={{border:'none', cursor:'pointer', height:26, paddingRight:6}}>
            Диапазон <Icon d={IC.x} size={12} style={{marginLeft:2}}/>
          </button>
        )}

        {readOnly
          ? <span className="badge" style={{background:'var(--surface-3)', color:'var(--text-2)'}}><Icon d={IC.search} size={12}/>Только просмотр</span>
          : <span className={'badge '+st.cls} title={periodClosed?'Период закрыт':''}><span className="dot"/>{periodClosed?'Закрыт':st.label}</span>}

        <div style={{flex:1}}/>
        <div style={{display:'flex', alignItems:'center', gap:18}}>
          <Meter label="Списано" value={fmtH(grand)} accent/>
          <Meter label="Норма" value={periodNorm}/>
          <Meter label="Заполнено" value={pct+'%'} warn={grand<periodNorm*0.5}/>
          <div style={{width:140}}>
            <div className="progress" style={{height:9}}><span style={{width:Math.min(pct,100)+'%', background: grand>periodNorm?'var(--amber)':'var(--accent)'}}/></div>
          </div>
        </div>
      </div>

      {/* grid */}
      <div className="card" style={{padding:0, overflow:'hidden'}}>
        <div className="ts-scroll" style={{overflowX:'auto'}}>
          <table style={{borderCollapse:'separate', borderSpacing:0, width:'100%', minWidth: view.kind==='month'?900:Math.max(640, 230+cols.length*colW+64)}}>
            <thead>
              <tr>
                <th style={{...thSticky, left:0, zIndex:5, minWidth:230, width:230, textAlign:'left', paddingLeft:18}}>Проект / задача</th>
                {cols.map((col,ci)=>{
                  if(col.kind==='month'){
                    return (
                      <th key={ci} style={{...thDay, width:colW, background: col.future?'var(--surface-3)':'var(--surface-2)',
                        color: (col.m===TODAY.getMonth()&&col.y===TODAY.getFullYear())?'var(--accent-strong)':'var(--text-3)'}}>
                        <div style={{fontSize:11.5, fontWeight:700}}>{col.label}</div>
                        <div style={{fontSize:9.5, opacity:.8}}>{col.y}</div>
                      </th>
                    );
                  }
                  const isToday=col.key===todayKey;
                  return (
                    <th key={ci} title={col.holiday||(col.short?'Сокращённый день · 7 ч':col.monthName)} style={{...thDay, width:colW,
                      background: col.holiday?'var(--red-soft)':col.weekend?'var(--weekend-soft)':'var(--surface-2)',
                      color: col.holiday?'oklch(0.50 0.16 25)':isToday?'var(--accent-strong)':'var(--text-3)'}}>
                      <div style={{fontSize:11, fontWeight:700}}>{col.d}</div>
                      <div style={{fontSize:9.5, opacity:.85}}>{col.holiday?'празд':col.label}</div>
                      {col.short && <div style={{position:'absolute', top:3, right:4, width:5, height:5, borderRadius:'50%', background:'var(--amber)'}} title="Сокращённый день"/>}
                    </th>
                  );
                })}
                <th style={{...thSticky, right:0, zIndex:5, width:64, minWidth:64, background:'var(--accent-softer)'}}>Итого</th>
              </tr>
            </thead>
            <tbody>
              {projects.length===0 && (
                <tr><td colSpan={cols.length+2} className="muted" style={{textAlign:'center', height:80}}>Нет назначений на проекты — обратитесь к менеджеру</td></tr>
              )}
              {projects.map(p=>{ const pid=p.id; const isCol=collapsed.has(pid);
                const tasks=tasksOf(pid); const pTotal=projTotal(pid); return (
                <React.Fragment key={pid}>
                  {/* project header row */}
                  <tr className="ts-proj">
                    <td style={{...tdSticky, left:0, zIndex:4, minWidth:230, width:230, background:'var(--surface-2)', cursor:'pointer'}} onClick={()=>setCollapsed(s=>{ const n=new Set(s); n.has(pid)?n.delete(pid):n.add(pid); return n; })}>
                      <div style={{display:'flex', alignItems:'center', gap:9}}>
                        <Icon d={isCol?IC.chevR:IC.chevD} size={15} style={{color:'var(--text-3)', flex:'none'}}/>
                        <span style={{width:28,height:28,borderRadius:7,background:p.color,color:'#fff',display:'flex',alignItems:'center',justifyContent:'center',fontWeight:700,fontSize:10,flex:'none'}}>{(p.code||p.name).slice(0,2).toUpperCase()}</span>
                        <div style={{minWidth:0, flex:1}}>
                          <div style={{fontWeight:700, fontSize:13, whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis'}}>{p.name}</div>
                          <div className="muted" style={{fontSize:11}}>{tasks.length} {plural(tasks.length,'задача','задачи','задач')} · <b style={{color:'var(--text-2)'}}>{fmtH(pTotal)||0}</b> ч</div>
                        </div>
                      </div>
                    </td>
                    {cols.map((col,ci)=>{
                      const ab=col.kind==='day'&&absType(col.key);
                      // Свёрнуто (или колонка "месяц") — как раньше, читаемый агрегат по всем задачам.
                      // Развёрнуто — шапка сама становится строкой "часы без задачи" (task_name=null),
                      // как обычная строка-задача, чтобы не путать с суммой по подзадачам ниже
                      if(isCol || col.kind==='month'){
                        const bg=ab?ab.bg:(col.holiday?'var(--red-soft)':col.weekend?'var(--weekend-soft)':col.future?'var(--surface-3)':'var(--surface-2)');
                        const dv=projColVal(pid,col);
                        const dim=col.kind==='day'?col.date>TODAY:col.future;
                        return (
                          <td key={ci} style={{padding:0, textAlign:'center', borderTop:'1px solid var(--border)', borderLeft:'1px solid var(--border)', background:bg, height:40}} className="mono">
                            {ab ? <Icon d={IC[ab.icon]||IC.calendar} size={12} style={{color:ab.color,opacity:.7}}/>
                                : <span style={{fontSize:12, fontWeight:700, color:dv?'var(--text-2)':'var(--text-3)', opacity:dim?0.4:1}}>{fmtH(dv)||''}</span>}
                          </td>
                        );
                      }
                      const ntRow=noTaskRowOf(p);
                      const v=colVal(ntRow,col);
                      const bg=ab?ab.bg:(col.holiday?'var(--red-soft)':col.weekend?'var(--weekend-soft)':'var(--surface-2)');
                      const future=col.date>TODAY;
                      const editable=cellEditable(col)&&!ab&&!future;
                      return (
                        <td key={ci} title={ab?ab.name:(col.holiday||'Часы без привязки к задаче')} style={{padding:0, textAlign:'center', borderTop:'1px solid var(--border)', borderLeft:'1px solid var(--border)', background:bg, height:40}} className="mono">
                          {ab ? (
                            <div style={{width:colW,height:36,display:'flex',alignItems:'center',justifyContent:'center'}}>
                              <Icon d={IC[ab.icon]||IC.calendar} size={13} style={{color:ab.color,opacity:.7}}/>
                            </div>
                          ) : editable ? (
                            <input key={ntRow.key+col.key+':'+v} defaultValue={v||''}
                              onBlur={e=>commitCell(ntRow,col,e.target.value)}
                              onKeyDown={e=>{ if(e.key==='Enter') e.currentTarget.blur(); }}
                              placeholder="·" className="mono"
                              style={{width:colW, height:36, border:'none', textAlign:'center', background:'transparent',
                                fontSize:12.5, fontWeight:v?700:400, color:v?'var(--text)':'var(--text-3)', outline:'none'}}/>
                          ) : (
                            <span className="mono" style={{display:'flex', alignItems:'center', justifyContent:'center', height:36,
                              fontSize:12.5, fontWeight:v?700:400, color:v?'var(--text)':'var(--text-3)', opacity:future?0.4:1}}>{fmtH(v)||''}</span>
                          )}
                        </td>
                      );
                    })}
                    <td style={{...tdSticky, right:0, zIndex:3, textAlign:'center', background:'var(--accent-soft)', fontWeight:800}} className="mono">{fmtH(pTotal)||''}</td>
                  </tr>

                  {/* task rows */}
                  {!isCol && tasks.map(r=>{ const rt=taskTotal(r); const hasOvertime=Object.values(r.hours).some(c=>c.entries.some(e=>e.entry_type?.code==='OVERTIME')); return (
                    <tr key={r.key} className="ts-row">
                      <td style={{...tdSticky, left:0, zIndex:4, minWidth:230, width:230, background:'var(--surface)'}}>
                        <div style={{display:'flex', alignItems:'center', gap:8, paddingLeft:28}}>
                          <span style={{width:6,height:6,borderRadius:'50%',background:p.color,flex:'none',opacity:.8}}/>
                          <input key={r.key+':'+r.task} defaultValue={r.task} disabled={!canEditAnchor}
                            onBlur={e=>renameTask(r, e.target.value)}
                            onKeyDown={e=>{ if(e.key==='Enter') e.currentTarget.blur(); }}
                            className="ts-taskname" placeholder="Название задачи"
                            style={{flex:1, minWidth:0, border:'1px solid transparent', borderRadius:6, padding:'4px 6px', fontSize:12.5, fontWeight:500, color:'var(--text)', background:'transparent', outline:'none'}}/>
                          {hasOvertime && <span title="Есть переработка (на согласовании у менеджера)" style={{color:'var(--amber)', display:'flex'}}><Icon d={IC.trend} size={13}/></span>}
                          <button className="btn ghost sm icon ts-info" onClick={()=>setTaskDetail({row:r, proj:p})} title="Комментарий к задаче"
                            style={{color:r.comment?'var(--accent-strong)':'var(--text-3)'}}>
                            <Icon d={IC.file} size={13}/>
                          </button>
                          {canEditAnchor && <button className="btn ghost sm icon ts-del" onClick={()=>removeTask(r)} title="Удалить задачу"><Icon d={IC.x} size={13}/></button>}
                        </div>
                      </td>
                      {cols.map((col,ci)=>{
                        const ab=col.kind==='day'&&absType(col.key);
                        const v=colVal(r,col);
                        if(col.kind==='month'){
                          return (
                            <td key={ci} style={{padding:0, textAlign:'center', borderTop:'1px solid var(--border)', borderLeft:'1px solid var(--border)', background:col.future?'var(--surface-2)':'var(--surface)'}} className="mono">
                              <span style={{fontSize:12.5, fontWeight:v?600:400, color:v?'var(--text)':'var(--text-3)', opacity:col.future?0.4:1}}>{fmtH(v)||(col.future?'':'·')}</span>
                            </td>
                          );
                        }
                        const bg=ab?ab.bg:(col.holiday?'var(--red-soft)':col.weekend?'var(--weekend-soft)':'var(--surface)');
                        const future=col.date>TODAY;
                        const editable=cellEditable(col)&&!ab&&!future;
                        return (
                          <td key={ci} title={ab?ab.name:(col.holiday||'')} style={{padding:0, textAlign:'center', borderTop:'1px solid var(--border)', borderLeft:'1px solid var(--border)', background:bg}}>
                            {ab ? (
                              <div style={{width:colW,height:36,display:'flex',alignItems:'center',justifyContent:'center'}}>
                                <Icon d={IC[ab.icon]||IC.calendar} size={13} style={{color:ab.color,opacity:.7}}/>
                              </div>
                            ) : editable ? (
                              <input key={r.key+col.key+':'+v} defaultValue={v||''}
                                onBlur={e=>commitCell(r,col,e.target.value)}
                                onKeyDown={e=>{ if(e.key==='Enter') e.currentTarget.blur(); }}
                                placeholder="·" className="mono"
                                style={{width:colW, height:36, border:'none', textAlign:'center', background:'transparent',
                                  fontSize:12.5, fontWeight:v?600:400, color:v?'var(--text)':'var(--text-3)', outline:'none'}}/>
                            ) : (
                              <span className="mono" style={{display:'flex', alignItems:'center', justifyContent:'center', height:36,
                                fontSize:12.5, fontWeight:v?600:400, color:v?'var(--text)':'var(--text-3)', opacity:future?0.4:1}}>{fmtH(v)||''}</span>
                            )}
                          </td>
                        );
                      })}
                      <td style={{...tdSticky, right:0, zIndex:3, textAlign:'center', background:'var(--accent-softer)', fontWeight:700}} className="mono">{fmtH(rt)||''}</td>
                    </tr>
                  );})}

                  {/* add task row */}
                  {!isCol && canEditAnchor && view.kind==='day' && (
                    <tr className="ts-addtask">
                      <td style={{...tdSticky, left:0, zIndex:4, background:'var(--surface)'}}>
                        <div style={{paddingLeft:28}}>
                          <button className="btn ghost sm" onClick={()=>addTask(p)} style={{color:'var(--accent-strong)', fontSize:12.5}}>
                            <Icon d={IC.plus} size={14}/>Добавить задачу
                          </button>
                        </div>
                      </td>
                      {cols.map((col,ci)=><td key={ci} style={{borderTop:'1px solid var(--border)', borderLeft:'1px solid var(--border)', background:col.holiday?'var(--red-soft)':col.weekend?'var(--weekend-soft)':col.future?'var(--surface-2)':'var(--surface)'}}/>)}
                      <td style={{...tdSticky, right:0, background:'var(--accent-softer)'}}/>
                    </tr>
                  )}
                </React.Fragment>
              );})}
            </tbody>
            <tfoot>
              <tr>
                <td style={{...tdSticky, left:0, zIndex:4, background:'var(--surface-3)', fontWeight:700, paddingLeft:18}}>{view.kind==='month'?'Итого за месяц':'Итого за день'}</td>
                {cols.map((col,ci)=>{ const dt=colTotal(col);
                  if(col.kind==='month'){
                    return <td key={ci} className="mono" style={{textAlign:'center', height:36, borderTop:'2px solid var(--border-strong)', borderLeft:'1px solid var(--border)',
                      background: col.future?'var(--surface-3)':'var(--surface-2)', fontWeight:700, fontSize:12, color:dt===0?'var(--text-3)':'var(--text)'}}>{fmtH(dt)||''}</td>;
                  }
                  const over=dt>col.cap && col.cap>0; const under=col.working && dt>0 && dt<col.cap;
                  const ab=absType(col.key);
                  const bgFoot=ab?ab.bg:(col.holiday?'var(--red-soft)':col.weekend?'var(--weekend-soft)':'var(--surface-2)');
                  return (
                    <td key={ci} className="mono" style={{textAlign:'center', height:36, borderTop:'2px solid var(--border-strong)', borderLeft:'1px solid var(--border)',
                      background: bgFoot, fontWeight:700, fontSize:12,
                      color: ab?ab.color:(dt===0?'var(--text-3)':(over?'var(--amber)':under?'var(--text-2)':'var(--text)'))
                    }}>{ab?<Icon d={IC[ab.icon]||IC.calendar} size={12}/>:(fmtH(dt)||'')}</td>
                  );
                })}
                <td style={{...tdSticky, right:0, zIndex:4, textAlign:'center', background:'var(--accent)', color:'#fff', fontWeight:800, borderTop:'2px solid var(--border-strong)'}} className="mono">{fmtH(grand)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      {/* legend */}
      <div style={{display:'flex', alignItems:'center', gap:18, flexWrap:'wrap'}}>
        <span className="muted" style={{fontSize:12, display:'flex', alignItems:'center', gap:8}}>
          <Icon d={IC.clock} size={14}/> Норма периода — {periodNorm} ч ({workdays} рабочих дней).
        </span>
        {view.kind==='day' && <>
          <span style={{display:'inline-flex', alignItems:'center', gap:7, fontSize:12, color:'var(--text-2)'}}><span style={{width:11,height:11,borderRadius:3,background:'var(--red-soft)',border:'1px solid var(--red)'}}/>Праздник</span>
          <span style={{display:'inline-flex', alignItems:'center', gap:7, fontSize:12, color:'var(--text-2)'}}><span style={{width:7,height:7,borderRadius:'50%',background:'var(--amber)'}}/>Сокращённый (7 ч)</span>
          <span style={{display:'inline-flex', alignItems:'center', gap:7, fontSize:12, color:'var(--text-2)'}}><Icon d={IC.trend} size={13} style={{color:'var(--amber)'}}/>Переработка</span>
          <span style={{display:'inline-flex', alignItems:'center', gap:7, fontSize:12, color:'var(--text-2)'}}><span style={{width:11,height:11,borderRadius:3,background:'var(--weekend-soft)',border:'1px solid var(--weekend)'}}/>Выходной</span>
        </>}
        {view.kind==='month' && <span className="muted" style={{fontSize:12}}>Годовой разрез — часы суммируются по месяцам.</span>}
      </div>

      {taskDetail && <TaskDetailDrawer row={taskDetail.row} proj={taskDetail.proj} readOnly={!canEditAnchor} onSave={saveTaskComment} onClose={()=>setTaskDetail(null)}/>}

      {dialog && (
        <div style={{position:'fixed',inset:0,zIndex:200,display:'flex',alignItems:'center',justifyContent:'center',background:'oklch(0.2 0.02 255 / 0.55)',backdropFilter:'blur(4px)'}}
          onClick={e=>{ if(e.target===e.currentTarget) setDialog(null); }}>
          <div className="card fade-in" style={{width:460,padding:28,boxShadow:'var(--shadow-lg)'}}>
            <h3 style={{margin:'0 0 6px', fontSize:17}}>{dialog==='submit'?'Отправить на согласование':'Отклонить табель'}</h3>
            <p className="muted" style={{fontSize:13, margin:'0 0 16px', lineHeight:1.5}}>
              {dialog==='submit'
                ? `Табель за ${TS_MONTHS[anchor.getMonth()].toLowerCase()} ${anchor.getFullYear()} уйдёт на проверку менеджеру. До решения записи будут заблокированы.`
                : 'Укажите причину — сотрудник получит уведомление.'}
            </p>
            {dialog==='reject' && (
              <textarea className="input" style={{height:96, resize:'vertical', padding:'10px 12px', lineHeight:1.5}}
                value={commentDraft} onChange={e=>setCommentDraft(e.target.value)}
                placeholder="Причина отклонения…"/>
            )}
            <div style={{display:'flex', gap:8, justifyContent:'flex-end', marginTop:16}}>
              <button className="btn" onClick={()=>setDialog(null)}>Отмена</button>
              <button className={'btn primary'} style={dialog==='reject'?{background:'var(--red)',borderColor:'var(--red)'}:{}}
                onClick={dialog==='submit'?doSubmit:doReject}>
                {dialog==='submit'?'Отправить':'Отклонить'}
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        .ts-row .ts-del, .ts-proj .ts-del, .ts-row .ts-info{ opacity:0; transition:opacity .12s; }
        .ts-row:hover .ts-del, .ts-proj:hover .ts-del, .ts-row:hover .ts-info{ opacity:.65; }
        .ts-row .ts-del:hover, .ts-proj .ts-del:hover{ opacity:1; color:var(--red); }
        .ts-row .ts-info:hover{ opacity:1 !important; }
        tr.ts-row:hover td input.mono{ background:var(--surface-2); }
        .ts-proj:hover > td:first-child{ background:var(--surface-3) !important; }
        .ts-taskname:hover{ border-color:var(--border) !important; }
        .ts-taskname:focus{ border-color:var(--accent) !important; background:var(--surface) !important; }
        .ts-scroll{ scrollbar-color: var(--border-strong) var(--surface-2); }
        .ts-scroll::-webkit-scrollbar{ height:12px; }
        .ts-scroll::-webkit-scrollbar-track{ background:var(--surface-2); border-top:1px solid var(--border); }
        .ts-scroll::-webkit-scrollbar-thumb{ background:var(--border-strong); border-radius:20px; border:3px solid var(--surface-2); background-clip:padding-box; min-width:48px; }
        .ts-scroll::-webkit-scrollbar-thumb:hover{ background:var(--text-3); }
      `}</style>
    </div>
  );
}

function plural(n,a,b,c){ const m=n%100, k=n%10; if(m>=11&&m<=14) return c; if(k===1) return a; if(k>=2&&k<=4) return b; return c; }

const thSticky={ position:'sticky', top:0, height:46, padding:'4px 6px', fontSize:11.5, fontWeight:600, color:'var(--text-3)',
  background:'var(--surface-2)', borderBottom:'1px solid var(--border)', textAlign:'center' };
const thDay={ ...thSticky };
const tdSticky={ position:'sticky', padding:'0 10px', height:46, borderTop:'1px solid var(--border)', verticalAlign:'middle' };

function Meter({ label, value, accent, warn }){
  return (
    <div style={{textAlign:'right'}}>
      <div className="muted" style={{fontSize:11, fontWeight:600}}>{label}</div>
      <div className="tnum" style={{fontSize:17, fontWeight:800, color:accent?'var(--accent-strong)':(warn?'var(--amber)':'var(--text)')}}>{value}</div>
    </div>
  );
}

/* ============ TASK DETAIL DRAWER: комментарий к задаче ============ */
function TaskDetailDrawer({ row, proj, readOnly, onSave, onClose }){
  const [text,setText]=useState(row.comment||'');

  return (
    <div style={{position:'fixed',inset:0,zIndex:180,display:'flex',justifyContent:'flex-end'}}>
      <div onClick={onClose} style={{position:'absolute',inset:0,background:'oklch(0.3 0.02 255 / 0.30)',backdropFilter:'blur(1px)'}}/>
      <div className="fade-in" style={{position:'relative',width:460,maxWidth:'94vw',height:'100%',background:'var(--surface)',
        borderLeft:'1px solid var(--border)',boxShadow:'var(--shadow-lg)',display:'flex',flexDirection:'column'}}>

        <div style={{padding:'20px 24px 16px',borderBottom:'1px solid var(--border)',flexShrink:0}}>
          <div style={{display:'flex',alignItems:'flex-start',justifyContent:'space-between',gap:12}}>
            <div style={{flex:1,minWidth:0}}>
              <div style={{fontWeight:700,fontSize:16,lineHeight:1.3,marginBottom:6}}>{row.task}</div>
              <div style={{display:'flex',gap:6,alignItems:'center',flexWrap:'wrap'}}>
                {proj&&<span style={{display:'inline-flex',alignItems:'center',gap:6,padding:'3px 9px',borderRadius:999,background:'var(--surface-2)',fontSize:11.5,fontWeight:600,color:'var(--text-2)'}}>
                  <span style={{width:7,height:7,borderRadius:2,background:proj.color,flexShrink:0}}/>{proj.name}
                </span>}
              </div>
            </div>
            <button className="btn ghost sm icon" onClick={onClose}><Icon d={IC.x} size={17}/></button>
          </div>
        </div>

        <div style={{flex:1,overflowY:'auto',padding:'20px 24px',display:'flex',flexDirection:'column',gap:14}}>
          <div style={{fontWeight:600,fontSize:13.5,display:'flex',alignItems:'center',gap:7}}>
            <Icon d={IC.fileText} size={15} style={{color:'var(--text-3)'}}/>Комментарий к задаче
          </div>
          {readOnly ? (
            <div style={{fontSize:13.5,lineHeight:1.6,color:text?'var(--text)':'var(--text-3)',
              padding:'10px 12px',borderRadius:'var(--radius-sm)',background:'var(--surface-2)',
              border:'1px solid var(--border)',minHeight:60,whiteSpace:'pre-wrap'}}>
              {text||'Комментария нет'}
            </div>
          ) : (
            <>
              <textarea className="input" value={text} onChange={e=>setText(e.target.value)}
                placeholder="Контекст задачи: цель, ссылка на тикет, пояснения к списаниям…"
                style={{height:140,resize:'vertical',padding:'10px 12px',lineHeight:1.55,fontSize:13.5}}/>
              <div style={{display:'flex',gap:8,justifyContent:'flex-end'}}>
                <button className="btn sm" onClick={onClose}>Отмена</button>
                <button className="btn sm primary" onClick={()=>{ onSave(row, text.trim()); onClose(); }} disabled={!row.hasEntries}>
                  <Icon d={IC.check} size={13}/>Сохранить
                </button>
              </div>
              {!row.hasEntries && <div className="muted" style={{fontSize:12}}>Комментарий хранится на записях — сначала спишите часы на задачу.</div>}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { TimesheetScreen });
