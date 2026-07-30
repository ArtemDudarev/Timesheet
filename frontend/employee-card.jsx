/* ============ EMPLOYEE CARD DRAWER (живые данные) ============ */

// Статусы сотрудника из каталога management (у справочника нет кодов — матчим по имени)
const EMP_STATUS_VISUAL = {
  'Новый':         { color:'var(--accent-strong)',   bg:'var(--accent-soft)' },
  'Активный':      { color:'oklch(0.42 0.11 155)',   bg:'var(--green-soft)'  },
  'В отпуске':     { color:'oklch(0.48 0.12 70)',    bg:'var(--amber-soft)'  },
  'На больничном': { color:'oklch(0.48 0.12 70)',    bg:'var(--amber-soft)'  },
  'Уволен':        { color:'oklch(0.5 0.19 27)',     bg:'oklch(0.5 0.19 27 / 0.12)' },
};
const empStatusVisual = (name)=>EMP_STATUS_VISUAL[name]||{ color:'var(--text-2)', bg:'var(--surface-2)' };

// Статусы назначения на проект (code с бэка)
const ASG_STATUS_CLS = { ACTIVE:'green', EXTENDED:'accent', COMPLETED:'', CANCELLED:'red' };

const EC_MON = ['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'];

function tenure(hireDate){
  const d=new Date(hireDate), now=new Date();
  let y=now.getFullYear()-d.getFullYear(), m=now.getMonth()-d.getMonth();
  if(m<0){y--;m+=12;}
  if(y>0) return y+' '+(y===1?'год':y<5?'года':'лет')+(m>0?' '+m+' мес.':'');
  return m+' мес.';
}

function EmployeeCard({ empId, team, resets, onPwd, onClose, onChat, onChanged, showToast }){
  const [emp,setEmp] = useState(null);          // профиль (profile_service)
  const [summary,setSummary] = useState(null);
  const [periods,setPeriods] = useState([]);
  const [cats,setCats] = useState(null);        // {statuses, grades, skills}
  const [error,setError] = useState(null);

  const [editSkills,setEditSkills] = useState(false);
  const [skills,setSkills] = useState([]);      // [{id,name}]
  const [skillQ,setSkillQ] = useState('');
  const [skillOpen,setSkillOpen] = useState(false);
  const [showGradeEdit,setShowGradeEdit] = useState(false);
  const [busy,setBusy] = useState(false);

  const canManage = (API.session()?.permissions||[]).includes('employee:edit_any');

  useEffect(()=>{
    let alive=true;
    Promise.all([
      API.profile.getEmployee(empId),
      API.timesheet.getSummary(empId).catch(()=>null),
      API.timesheet.getPeriods(empId).catch(()=>[]),
      Promise.all([
        API.management.getEmployeeStatuses().catch(()=>[]),
        API.profile.getGrades().catch(()=>[]),
        API.profile.getSkills().catch(()=>[]),
      ]),
    ]).then(([p, s, pers, [statuses, grades, skillCat]])=>{
      if(!alive) return;
      setEmp(p); setSummary(s); setPeriods(pers);
      setCats({ statuses, grades, skills:skillCat });
      setSkills(p.skills||[]);
    }).catch(err=>{ if(alive) setError(err.detail||'Не удалось загрузить сотрудника'); });
    return ()=>{ alive=false; };
  },[empId]);

  // Общая обёртка мутаций: оптимистично обновляем профиль в карточке, роняем тостом
  const mutate = async (fn, patch)=>{
    setBusy(true);
    try{
      await fn();
      if(patch) setEmp(e=>({ ...e, ...patch }));
      onChanged && onChanged();
    }catch(err){ showToast(err.detail||'Не удалось сохранить'); }
    finally{ setBusy(false); }
  };

  const setGrade  = (g)=>mutate(()=>API.profile.updateEmployee(empId,{ grade_id:g.id }), { grade:g });
  const setStatus = (st)=>mutate(()=>API.management.setStatus(empId, st.id), { status:st });
  const setLead   = (leadId)=>mutate(()=>API.management.setLead(empId, leadId||null), { lead_id:leadId||null });
  const saveSkills = ()=>{
    setEditSkills(false);
    mutate(()=>API.profile.updateSkills(empId, skills.map(s=>s.id)), { skills });
  };

  const overlay = (children)=>(
    <div style={{position:'fixed',inset:0,zIndex:120,display:'flex',justifyContent:'flex-end'}}>
      <div onClick={onClose} style={{position:'absolute',inset:0,background:'oklch(0.3 0.02 255 / 0.32)',backdropFilter:'blur(1px)'}}/>
      <div className="fade-in" style={{position:'relative',width:620,maxWidth:'96vw',height:'100%',background:'var(--surface)',
        borderLeft:'1px solid var(--border)',boxShadow:'var(--shadow-lg)',display:'flex',flexDirection:'column',overflowY:'auto'}}>
        {children}
      </div>
    </div>
  );

  if(error) return overlay(<div style={{padding:26}}><ErrorCard text={error}/></div>);
  if(!emp || !cats) return overlay(
    <div style={{padding:26,display:'flex',flexDirection:'column',gap:14}}>
      <div style={{display:'flex',gap:16,alignItems:'center'}}>
        <div className="skel" style={{width:72,height:72,borderRadius:50}}/>
        <div style={{flex:1}}><div className="skel" style={{width:220,height:22,marginBottom:8}}/><div className="skel" style={{width:160,height:14}}/></div>
      </div>
      {[0,1,2].map(i=><div key={i} className="skel" style={{height:80}}/>)}
    </div>
  );

  const name = `${emp.first_name} ${emp.last_name}`;
  const stVis = empStatusVisual(emp.status.name);
  const teamList = team||[];
  const manager = emp.lead_id ? teamList.find(t=>t.id===emp.lead_id) : null;
  const directReports = teamList.filter(t=>t.lead_id===empId && t.id!==empId);
  const pwdReq = (resets||[]).find(r=>resetRequestMatches(r.identifier, emp.user));

  const logged = summary?Number(summary.logged_hours):0;
  const norm = summary?Number(summary.norm_hours):0;
  const utilPct = summary?Math.round(summary.utilization_pct):0;
  const utilColor = utilPct>100?'var(--red)':utilPct>=85?'var(--green)':utilPct>=60?'var(--accent)':'var(--amber)';

  // Назначения: активные сверху
  const asgs = [...(emp.assignments||[])].sort((a,b)=>
    (ACTIVE_ASG.includes(b.assignment_status.code)?1:0)-(ACTIVE_ASG.includes(a.assignment_status.code)?1:0));

  // История табелей: прошедшие и текущий месяц, свежие сверху
  const now = new Date();
  const hist = periods
    .filter(p=>p.year<now.getFullYear()||(p.year===now.getFullYear()&&p.month<=now.getMonth()+1))
    .sort((a,b)=>(b.year-a.year)||(b.month-a.month))
    .slice(0,6);

  const weekly = (summary?.weekly_dynamics||[]).map(w=>({ ...w, hours:Number(w.hours) }));
  const recent = summary?.recent_entries||[];

  const skillSugs = (()=>{
    const have = new Set(skills.map(s=>s.id));
    const lo = skillQ.toLowerCase();
    return cats.skills.filter(s=>!have.has(s.id)&&(!lo||s.name.toLowerCase().includes(lo))).slice(0,8);
  })();
  const addSkill=(s)=>{ setSkills(ss=>ss.some(x=>x.id===s.id)?ss:[...ss,s]); setSkillQ(''); };
  const rmSkill=(s)=>setSkills(ss=>ss.filter(x=>x.id!==s.id));

  return overlay(<>
    {/* ── шапка ── */}
    <div style={{padding:'22px 26px 20px',borderBottom:'1px solid var(--border)',background:'var(--surface-2)',flexShrink:0}}>
      <div style={{display:'flex',alignItems:'flex-start',gap:16}}>
        <Avatar id={emp.id} name={name} size={72} ring imageUrl={emp.image_url}/>
        <div style={{flex:1,minWidth:0}}>
          <div style={{display:'flex',alignItems:'center',gap:10,flexWrap:'wrap'}}>
            <h2 style={{fontSize:20}}>{name}</h2>
            {canManage?(
              <div style={{position:'relative'}}>
                <button className="badge accent" style={{cursor:'pointer',border:'none'}} disabled={busy}
                  onClick={()=>setShowGradeEdit(o=>!o)}>{emp.grade?.name||'Грейд'} ▾</button>
                {showGradeEdit&&(
                  <div className="card fade-in" style={{position:'absolute',top:'100%',left:0,zIndex:10,marginTop:4,padding:4,boxShadow:'var(--shadow-md)'}}>
                    {cats.grades.map(g=>(
                      <button key={g.id} onClick={()=>{setShowGradeEdit(false);setGrade(g);}}
                        style={{display:'block',width:'100%',padding:'6px 14px',border:'none',background:g.id===emp.grade?.id?'var(--accent-soft)':'transparent',
                          borderRadius:6,cursor:'pointer',fontWeight:700,color:g.id===emp.grade?.id?'var(--accent-strong)':'var(--text)',fontSize:13}}>
                        {g.name}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ):emp.grade&&<span className="badge accent">{emp.grade.name}</span>}
            {canManage?(
              <select value={emp.status.id} disabled={busy}
                onChange={ev=>{const st=cats.statuses.find(s=>s.id===ev.target.value); if(st) setStatus(st);}}
                style={{padding:'3px 8px',borderRadius:999,fontSize:12,fontWeight:600,border:'1px solid var(--border)',
                  background:stVis.bg,color:stVis.color,cursor:'pointer',outline:'none'}}>
                {cats.statuses.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            ):(
              <span className="badge" style={{background:stVis.bg,color:stVis.color}}><span className="dot"/>{emp.status.name}</span>
            )}
            <span className="badge" style={{fontFamily:'var(--mono)',fontSize:11}}>{emp.user.number}</span>
          </div>
          <div className="muted" style={{fontSize:14,marginTop:4}}>
            {emp.position||'Должность не указана'}{emp.department?' · '+emp.department.name:''}
          </div>
          <div style={{display:'flex',gap:16,marginTop:10,flexWrap:'wrap',color:'var(--text-2)',fontSize:13}}>
            <span style={{display:'inline-flex',alignItems:'center',gap:7}}><Icon d={IC.mail} size={15}/>{emp.user.email}</span>
            {emp.phone&&<span style={{display:'inline-flex',alignItems:'center',gap:7}}><Icon d={IC.briefcase} size={14}/>{emp.phone}</span>}
            {emp.birthday&&<span style={{display:'inline-flex',alignItems:'center',gap:7}}><Icon d={IC.calendar} size={14}/>{new Date(emp.birthday).toLocaleDateString('ru',{day:'numeric',month:'long',year:'numeric'})}</span>}
            {emp.address&&<span style={{display:'inline-flex',alignItems:'center',gap:7}}><Icon d={IC.flag} size={14}/>{emp.address}</span>}
            {manager&&<span style={{display:'inline-flex',alignItems:'center',gap:7}}><Icon d={IC.user} size={14}/>Рук.: <span style={{fontWeight:600,color:'var(--text)'}}>{manager.name}</span></span>}
          </div>
        </div>
        <button className="btn ghost sm icon" onClick={onClose}><Icon d={IC.x} size={17}/></button>
      </div>
      <div style={{display:'flex',gap:8,marginTop:16}}>
        <button className="btn sm" onClick={()=>onChat&&onChat(emp.id)}><Icon d={IC.chat} size={15}/>Написать</button>
        {canManage&&pwdReq&&(
          <button onClick={()=>onPwd&&onPwd({ ...pwdReq, emp:{ name, position:emp.position||'' } })}
            style={{display:'flex',alignItems:'center',gap:7,padding:'4px 12px',border:'none',borderRadius:999,
              background:'var(--amber-soft)',color:'oklch(0.48 0.12 70)',cursor:'pointer',fontWeight:700,fontSize:12,animation:'pulse 2s infinite'}}>
            <span style={{width:8,height:8,borderRadius:50,background:'oklch(0.74 0.13 75)',boxShadow:'0 0 0 3px oklch(0.74 0.13 75 / 0.3)'}}/>
            <Icon d={IC.key} size={14}/>Временный пароль
          </button>
        )}
      </div>
      {canManage&&(
        <div style={{display:'flex',alignItems:'center',gap:10,marginTop:12}}>
          <span className="muted" style={{fontSize:12.5,fontWeight:600,whiteSpace:'nowrap',flexShrink:0}}>Руководитель:</span>
          <select value={emp.lead_id||''} disabled={busy} onChange={ev=>setLead(ev.target.value||null)}
            style={{flex:1,height:32,padding:'0 10px',borderRadius:8,border:'1px solid var(--border)',
              background:'var(--surface)',fontSize:13,cursor:'pointer',outline:'none',color:'var(--text)'}}>
            <option value="">— Нет руководителя —</option>
            {teamList.filter(m=>m.id!==emp.id).map(m=>(
              <option key={m.id} value={m.id}>{m.name}{m.position&&m.position!=='—'?' · '+m.position:''}</option>
            ))}
          </select>
        </div>
      )}
    </div>

    {/* ── контент ── */}
    <div style={{padding:'22px 26px',display:'flex',flexDirection:'column',gap:22}}>

      {/* загрузка */}
      <div style={{display:'flex',flexDirection:'column',gap:10}}>
        <div style={{display:'grid',gridTemplateColumns:'1fr 1fr 1fr 1fr',gap:10}}>
          <MiniStat label={summary?'Списано за '+summary.period_name.toLowerCase():'Списано'} value={logged+' ч'} accent/>
          <MiniStat label="Норма периода" value={norm+' ч'}/>
          <MiniStat label="Загрузка" value={utilPct+'%'} color={utilColor}/>
          <MiniStat label="Стаж в компании" value={tenure(emp.user.register_date)}/>
        </div>
        {norm>0&&(
          <div>
            <div style={{display:'flex',justifyContent:'space-between',fontSize:11.5,marginBottom:4}} className="muted"><span>Часов за месяц</span><span className="tnum">{logged}/{norm}</span></div>
            <div className="progress"><span style={{width:Math.min(logged/norm*100,100)+'%',background:utilColor}}/></div>
          </div>
        )}
      </div>

      {/* динамика по неделям */}
      {weekly.length>1&&(
        <div className="card" style={{padding:'16px 18px'}}>
          <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:14}}>
            <h3 style={{fontSize:14.5}}>Динамика часов</h3>
            <span className="muted" style={{fontSize:12}}>{weekly.length} {plural(weekly.length,'неделя','недели','недель')}</span>
          </div>
          <WeeklyChart data={weekly}/>
        </div>
      )}

      {/* проекты */}
      <div>
        <SectionTitle title={'Проекты · '+asgs.length}/>
        <div style={{display:'flex',flexDirection:'column',gap:8,marginTop:12}}>
          {asgs.map(a=>{
            const p=a.project;
            const active=ACTIVE_ASG.includes(a.assignment_status.code);
            return (
              <div key={a.id} style={{display:'flex',alignItems:'center',gap:12,padding:'11px 14px',border:'1px solid var(--border)',borderRadius:10,
                background:'var(--surface-2)',opacity:active?1:0.65}}>
                <span style={{width:34,height:34,borderRadius:8,background:p.color||'var(--accent)',color:'#fff',display:'flex',alignItems:'center',justifyContent:'center',fontWeight:700,fontSize:10,flexShrink:0}}>
                  {(p.code||p.name).slice(0,2).toUpperCase()}
                </span>
                <div style={{flex:1,minWidth:0}}>
                  <div style={{fontWeight:600,fontSize:13.5}}>{p.name}</div>
                  <div style={{display:'flex',alignItems:'center',gap:8,marginTop:3,flexWrap:'wrap'}}>
                    {p.client&&<span className="muted" style={{fontSize:12}}>{p.client}</span>}
                    <span style={{fontSize:11.5,fontWeight:600,color:'var(--accent-strong)',background:'var(--accent-soft)',padding:'1px 7px',borderRadius:4}}>{a.project_role.name}</span>
                    {a.end_date&&<span className="muted mono" style={{fontSize:11}}>до {fmtDate(a.end_date)}</span>}
                  </div>
                </div>
                <span className={'badge '+(ASG_STATUS_CLS[a.assignment_status.code]||'')} style={{height:22,fontSize:11,flexShrink:0}}>
                  <span className="dot"/>{a.assignment_status.name}
                </span>
              </div>
            );
          })}
          {asgs.length===0&&<div className="muted" style={{fontSize:13,padding:'12px 0'}}>Нет назначений на проекты</div>}
        </div>
      </div>

      {/* навыки */}
      <div>
        <div style={{display:'flex',alignItems:'center',justifyContent:'space-between',marginBottom:12}}>
          <h3 style={{fontSize:14.5}}>Навыки</h3>
          {canManage&&(editSkills
            ?<button className="btn sm primary" onClick={saveSkills} disabled={busy}><Icon d={IC.check} size={14}/>Сохранить</button>
            :<button className="btn ghost sm" onClick={()=>setEditSkills(true)}><Icon d={IC.edit} size={14}/>Редактировать</button>)}
        </div>
        {editSkills?(
          <div style={{position:'relative'}}>
            <div style={{minHeight:42,padding:'6px 8px',border:'1px solid var(--border-strong)',borderRadius:'var(--radius-sm)',
              background:'var(--surface)',display:'flex',flexWrap:'wrap',gap:6,alignItems:'center',cursor:'text'}}
              onClick={()=>setSkillOpen(true)}>
              {skills.map(s=>(
                <span key={s.id} style={{display:'inline-flex',alignItems:'center',gap:5,height:26,padding:'0 8px 0 10px',
                  borderRadius:999,background:'var(--accent-soft)',color:'var(--accent-strong)',fontSize:12.5,fontWeight:600}}>
                  {s.name}
                  <button onClick={e=>{e.stopPropagation();rmSkill(s);}}
                    style={{width:16,height:16,borderRadius:50,border:'none',background:'var(--accent-softer)',
                      color:'var(--accent-strong)',cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center',padding:0}}>
                    <Icon d={IC.x} size={10} stroke={2.5}/>
                  </button>
                </span>
              ))}
              <input value={skillQ} onChange={e=>{setSkillQ(e.target.value);setSkillOpen(true);}}
                onKeyDown={e=>{if(e.key==='Backspace'&&!skillQ&&skills.length)rmSkill(skills[skills.length-1]);else if(e.key==='Escape')setSkillOpen(false);}}
                onFocus={()=>setSkillOpen(true)} onBlur={()=>setTimeout(()=>setSkillOpen(false),150)}
                placeholder="Поиск по каталогу…"
                style={{border:'none',outline:'none',background:'transparent',fontSize:13.5,minWidth:120,flex:1,padding:'2px 4px'}}/>
            </div>
            {skillOpen&&skillSugs.length>0&&(
              <div className="card" style={{position:'absolute',top:'100%',left:0,right:0,zIndex:40,marginTop:4,boxShadow:'var(--shadow-lg)',padding:6,maxHeight:200,overflowY:'auto'}}>
                {skillSugs.map(s=>(
                  <button key={s.id} onMouseDown={e=>{e.preventDefault();addSkill(s);}}
                    style={{display:'flex',alignItems:'center',gap:9,width:'100%',padding:'7px 10px',border:'none',background:'transparent',borderRadius:8,cursor:'pointer',fontSize:13.5,textAlign:'left'}}
                    onMouseEnter={e=>e.currentTarget.style.background='var(--surface-2)'}
                    onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
                    <Icon d={IC.plus} size={14} style={{color:'var(--accent)',flexShrink:0}}/>{s.name}
                  </button>
                ))}
              </div>
            )}
          </div>
        ):(
          <div style={{display:'flex',flexWrap:'wrap',gap:8}}>
            {skills.map(s=><span key={s.id} className="badge" style={{height:27,fontSize:12.5}}>{s.name}</span>)}
            {skills.length===0&&<span className="muted" style={{fontSize:13}}>Навыки не указаны</span>}
          </div>
        )}
      </div>

      {/* подчинённые — только если есть */}
      {directReports.length>0 && (
        <div>
          <SectionTitle title={'Подчинённые · '+directReports.length}/>
          <div style={{display:'flex',flexDirection:'column',gap:8,marginTop:12}}>
            {directReports.map(r=>{
              const rCl=r.utilPct>100?'var(--red)':r.utilPct>=85?'var(--green)':r.utilPct>=60?'var(--accent)':'var(--amber)';
              return (
                <div key={r.id} style={{display:'flex',alignItems:'center',gap:12,padding:'10px 14px',border:'1px solid var(--border)',borderRadius:10,background:'var(--surface-2)'}}>
                  <Avatar id={r.id} name={r.name} size={34}/>
                  <div style={{flex:1,minWidth:0}}>
                    <div style={{fontWeight:600,fontSize:13.5}}>{r.name}</div>
                    <div className="muted" style={{fontSize:12}}>{r.position}{r.dept?' · '+r.dept:''}</div>
                  </div>
                  {r.grade&&<span className="badge accent" style={{height:20,fontSize:11}}>{r.grade}</span>}
                  <div style={{textAlign:'right',flexShrink:0}}>
                    <div className="tnum" style={{fontWeight:700,fontSize:13,color:rCl}}>{r.utilPct}%</div>
                    <div className="muted" style={{fontSize:11}}>загрузка</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* история табелей */}
      <div>
        <SectionTitle title="История табелей"/>
        <div style={{display:'flex',flexDirection:'column',gap:8,marginTop:12}}>
          {hist.map(p=>{
            const st=SUB_STATUS[p.submission_status]||{ label:p.submission_status, cls:'' };
            return (
              <div key={p.id} style={{display:'flex',alignItems:'center',gap:14,padding:'10px 14px',border:'1px solid var(--border)',borderRadius:10,background:'var(--surface-2)'}}>
                <div style={{flex:1}}>
                  <div style={{fontWeight:600,fontSize:13.5}}>{EC_MON[p.month-1]} {p.year}</div>
                  {p.rejection_comment&&<div className="muted" style={{fontSize:12,marginTop:3}}>Причина: {p.rejection_comment}</div>}
                </div>
                {p.status==='CLOSED'&&<span className="badge" style={{height:22,fontSize:11}}>Закрыт</span>}
                <span className={'badge '+st.cls} style={{height:22,fontSize:11}}><span className="dot"/>{st.label}</span>
              </div>
            );
          })}
          {hist.length===0&&<div className="muted" style={{fontSize:13,padding:'12px 0'}}>Табелей пока нет</div>}
        </div>
      </div>

      {/* последние записи */}
      <div>
        <SectionTitle title={'Последние записи · '+recent.length}/>
        <div style={{border:'1px solid var(--border)',borderRadius:10,overflow:'hidden',marginTop:12}}>
          {recent.map((r,i)=>(
            <div key={i} style={{display:'flex',alignItems:'center',gap:10,padding:'9px 14px',
              borderTop:i>0?'1px solid var(--border)':'none',
              background:i%2===0?'var(--surface)':'var(--surface-2)'}}>
              <span className="muted mono" style={{fontSize:11,whiteSpace:'nowrap',flexShrink:0,minWidth:50}}>{fmtDate(r.date_from)}</span>
              {r.project_name&&<span style={{fontSize:11.5,fontWeight:700,flexShrink:0,maxWidth:140,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{r.project_name}</span>}
              <span style={{flex:1,fontSize:13,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{r.task_name||'Без названия'}</span>
              <span className="mono" style={{fontWeight:700,fontSize:13,flexShrink:0,color:'var(--accent-strong)'}}>{Number(r.spend_time)}ч</span>
            </div>
          ))}
          {recent.length===0&&<div className="muted" style={{padding:18,textAlign:'center',fontSize:13}}>Записей пока нет</div>}
        </div>
      </div>
    </div>
  </>);
}

function WeeklyChart({ data }){
  const n=data.length;
  const hours=data.map(d=>d.hours);
  const maxVal=Math.max(...hours), minVal=Math.min(...hours);
  const avg=+(hours.reduce((a,b)=>a+b,0)/n).toFixed(1);
  const weekNorm=40;
  const svgW=320, svgH=112, padL=28, padR=14, padT=20, padB=22;
  const gW=svgW-padL-padR, gH=svgH-padT-padB;
  const scaleMax=Math.max(maxVal,weekNorm)*1.2;
  const sy=v=>padT+gH-(v/scaleMax)*gH;
  const colW=gW/n, barW=colW*0.58, sx=i=>padL+i*colW+colW/2;
  const normY=sy(weekNorm), avgY=sy(avg);
  const maxIdx=hours.indexOf(maxVal), minIdx=hours.indexOf(minVal);
  const wLabel=(w)=>{ const d=new Date(w.week_start); return d.getDate()+'.'+String(d.getMonth()+1).padStart(2,'0'); };
  return (
    <div>
      <svg width="100%" viewBox={'0 0 '+svgW+' '+svgH} style={{display:'block',overflow:'visible'}}>
        {[20,30,40].map(v=>{ const y=sy(v); return y>=padT-2&&y<=padT+gH+2?(
          <g key={v}>
            <line x1={padL} y1={y} x2={padL+gW} y2={y} stroke="var(--border)" strokeWidth="1"/>
            <text x={padL-4} y={y+3.5} textAnchor="end" fontSize="9" fill="var(--text-3)" fontFamily="var(--mono)">{v}</text>
          </g>
        ):null;})}
        <line x1={padL} y1={normY} x2={padL+gW} y2={normY} stroke="oklch(0.74 0.13 75)" strokeWidth="1.5" strokeDasharray="5,3"/>
        <line x1={padL} y1={avgY} x2={padL+gW} y2={avgY} stroke="var(--accent)" strokeWidth="1.5" strokeDasharray="5,3" opacity="0.55"/>
        {data.map((w,i)=>{
          const v=w.hours;
          const x=sx(i)-barW/2, bH=(v/scaleMax)*gH, y=sy(v);
          const isCur=i===n-1, isMax=i===maxIdx, isMin=i===minIdx;
          const fill=isCur?'var(--accent)':isMax?'var(--green)':isMin?'var(--amber)':'var(--accent-soft)';
          return (
            <g key={i}>
              <rect x={x} y={y} width={barW} height={bH} rx="3" fill={fill} opacity={isCur?1:0.72}/>
              {(isCur||isMax||isMin)&&v>0&&(
                <text x={sx(i)} y={y-5} textAnchor="middle" fontSize="9" fontWeight="700"
                  fill={isCur?'var(--accent-strong)':isMax?'oklch(0.42 0.11 155)':'oklch(0.48 0.12 70)'}>
                  {v}ч
                </text>
              )}
              <text x={sx(i)} y={padT+gH+14} textAnchor="middle" fontSize="9"
                fill={isCur?'var(--accent-strong)':'var(--text-3)'} fontWeight={isCur?'700':'400'}>
                {wLabel(w)}
              </text>
            </g>
          );
        })}
      </svg>
      <div style={{display:'flex',gap:16,marginTop:4,fontSize:11.5,color:'var(--text-2)',flexWrap:'wrap'}}>
        <span style={{display:'inline-flex',alignItems:'center',gap:5}}>
          <span style={{width:8,height:8,borderRadius:2,background:'var(--green)',flexShrink:0}}/>
          Макс.: <strong style={{color:'oklch(0.42 0.11 155)'}}>{maxVal}ч</strong>
        </span>
        <span style={{display:'inline-flex',alignItems:'center',gap:5}}>
          <span style={{width:8,height:8,borderRadius:2,background:'var(--amber)',flexShrink:0}}/>
          Мин.: <strong style={{color:'oklch(0.48 0.12 70)'}}>{minVal}ч</strong>
        </span>
        <span style={{display:'inline-flex',alignItems:'center',gap:5}}>
          <span style={{width:8,height:8,borderRadius:2,background:'var(--accent)',flexShrink:0}}/>
          Ср./нед.: <strong style={{color:'var(--accent)'}}>{avg}ч</strong>
        </span>
        <span style={{display:'inline-flex',alignItems:'center',gap:5}}>
          <span style={{width:36,height:2,background:'oklch(0.74 0.13 75)',flexShrink:0,borderRadius:1}}/>
          Норма: <strong>{weekNorm}ч</strong>
        </span>
      </div>
    </div>
  );
}

function MiniStat({ label, value, accent, color }){
  return (
    <div style={{padding:'10px 12px',background:'var(--surface-2)',borderRadius:9,border:'1px solid var(--border)'}}>
      <div className="muted" style={{fontSize:11,fontWeight:600}}>{label}</div>
      <div className="tnum" style={{fontSize:17,fontWeight:800,color:accent?'var(--accent-strong)':color||'var(--text)',marginTop:3}}>{value}</div>
    </div>
  );
}

Object.assign(window, { EmployeeCard });
