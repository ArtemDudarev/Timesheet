/* ============ SCREEN: Менеджерский блок — живые данные (этап 4a) ============ */
const PROJECT_COLORS = [
  { label:'Синий',    val:'oklch(0.55 0.13 250)' },
  { label:'Фиолет',  val:'oklch(0.58 0.15 295)' },
  { label:'Зелёный', val:'oklch(0.62 0.13 155)' },
  { label:'Янтарный',val:'oklch(0.74 0.13 75)'  },
  { label:'Красный', val:'oklch(0.60 0.18 22)'  },
  { label:'Серый',   val:'oklch(0.55 0.02 255)' },
];

// Бейджи по коду статуса проекта (management)
const MGMT_STATUS_CLS = { ACTIVE:'green', COMPLETED:'accent', ON_HOLD:'', PLANNED:'', ARCHIVED:'' };
const ACTIVE_ASG = ['ACTIVE','EXTENDED'];

const curPeriod = ()=>{ const d=new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}`; };

// identifier — то, что человек ввёл в «Забыли пароль»; email нечувствителен к регистру
// (бэк резолвит его так же), номер сотрудника только цифры — регистр ему не мешает
const resetRequestMatches=(identifier, e)=>{
  const id=(identifier||'').toLowerCase();
  return id===(e.email||'').toLowerCase()||id===(e.number||'').toLowerCase();
};

// «Под риском» — правило reporting: перерасход бюджета или просрочен дедлайн незавершённого
function projectAtRisk(p, spent){
  const today=new Date(); today.setHours(0,0,0,0);
  if(p.budget_hours && spent>p.budget_hours) return true;
  if(p.deadline && new Date(p.deadline)<today && p.project_status.code!=='COMPLETED' && p.project_status.code!=='ARCHIVED') return true;
  return false;
}

function ManagerScreen({ showToast, onNav, navTab }){
  const [tab,setTab]=useState(()=>navTab?.tab||'projects');
  // Переход из уведомления: если экран уже открыт на другой вкладке, remount не произойдёт —
  // догоняем вкладку эффектом по nonce (меняется даже при повторном клике на ту же вкладку)
  useEffect(()=>{ if(navTab?.tab) setTab(navTab.tab); },[navTab?.nonce]);
  const [data,setData]=useState(null);
  const [error,setError]=useState(null);
  const [catalogs,setCatalogs]=useState(null); // {roles, statuses, asgStatuses}
  const [detail,setDetail]=useState(null);
  const [createOpen,setCreateOpen]=useState(false);
  const [pwdModal,setPwdModal]=useState(null);
  const [cardEmp,setCardEmp]=useState(null);
  const [createEmp,setCreateEmp]=useState(false);
  const [approvalsData,setApprovalsData]=useState({ periods:[], overtime:[], trips:[] });
  const period = curPeriod();

  const loadApprovals = ()=>Promise.all([
    API.timesheet.getAllPeriods().catch(()=>[]),
    API.timesheet.getOvertimeApprovals(true).catch(()=>[]),
    API.absence.getAbsences().catch(()=>[]),
  ]).then(([periods, overtime, absences])=>{
    setApprovalsData({
      periods: periods.filter(p=>p.submission_status!=='Черновик'),
      overtime,
      trips: absences.filter(a=>a.absence_type.code==='TRIP' && a.status!=='Черновик'),
    });
  });

  const load = ()=>{
    return Promise.all([
      API.management.getProjects(),
      API.reporting.getProjectsReport(period).catch(()=>[]),
      API.management.getEmployees(),
      API.reporting.getUtilization(period).catch(()=>[]),
      API.auth.getResetRequests('Ожидает').catch(()=>[]),
      loadApprovals(),
    ]).then(([projects, stats, empList, util, resets])=>
      Promise.all(empList.map(e=>API.profile.getEmployee(e.id).catch(()=>null))).then(profiles=>{
        const statsMap={}; stats.forEach(s=>{ statsMap[s.project_id]=s; });
        const utilMap={}; util.forEach(u=>{ utilMap[u.employee_id]=u; });
        const team = empList.map((e,i)=>{
          const p=profiles[i];
          const u=utilMap[e.id];
          return {
            id:e.id,
            name:p?`${p.first_name} ${p.last_name}`:`${e.first_name} ${e.last_name}`,
            email:e.user.email,
            number:e.user.number,
            roles:(e.user.roles||[]).map(r=>r.name),
            position:p?.position||'—',
            grade:p?.grade?.name,
            dept:p?.department?.name,
            lead_id:p?.lead_id||null,
            skills:(p?.skills||[]).map(s=>s.name),
            assignments:(p?.assignments||[]).filter(a=>ACTIVE_ASG.includes(a.assignment_status.code)),
            logged:u?Number(u.logged_hours):0,
            norm:u?Number(u.norm_hours):0,
            utilPct:u?Math.round(u.utilization_pct):0,
          };
        });
        setData({ projects, statsMap, team, resets });
      })
    );
  };
  useEffect(()=>{ load().catch(err=>setError(err.detail||'Не удалось загрузить данные')); },[]);

  const ensureCatalogs = async ()=>{
    if(catalogs) return catalogs;
    const [roles, statuses, asgStatuses] = await Promise.all([
      API.management.getProjectRoles(),
      API.management.getProjectStatuses(),
      API.management.getAssignmentStatuses(),
    ]);
    const c={ roles, statuses, asgStatuses };
    setCatalogs(c);
    return c;
  };

  const reload = ()=>load().catch(err=>showToast(err.detail||'Не удалось обновить данные'));

  if(error) return <ErrorCard text={error}/>;
  if(!data) return (
    <div className="fade-in" style={{display:'flex', flexDirection:'column', gap:18}}>
      <div><div className="skel" style={{width:180, height:26, marginBottom:8}}/><div className="skel" style={{width:300, height:14}}/></div>
      <div className="card" style={{padding:18}}>{[0,1,2].map(i=><div key={i} className="skel" style={{height:44, marginBottom:10}}/>)}</div>
    </div>
  );

  // Заявки на сброс без сопоставленного сотрудника (несуществующий identifier) бэк
  // не даёт resolve'ить — только cancel, а этого действия в UI нет. Такие заявки
  // не показывают кнопку у карточки, поэтому и в счётчике их учитывать не нужно.
  const pendingPwd = data.resets.filter(r=>data.team.some(e=>resetRequestMatches(r.identifier, e))).length;
  const pendingApprovals =
    approvalsData.periods.filter(p=>p.submission_status==='На согласовании').length +
    approvalsData.overtime.filter(a=>a.status==='На согласовании').length +
    approvalsData.trips.filter(a=>a.status==='На согласовании').length;

  return (
    <div className="fade-in" style={{display:'flex', flexDirection:'column', gap:18}}>
      <PageHead title="Управление" subtitle="Проекты, команда и согласование табелей"/>

      <div className="seg">
        <button className={tab==='projects'?'on':''} onClick={()=>setTab('projects')}>Проекты</button>
        <button className={tab==='team'?'on':''} onClick={()=>setTab('team')} style={{display:'inline-flex',alignItems:'center',gap:7}}>
          Сотрудники {pendingPwd>0 && <span className="badge amber" style={{height:18, padding:'0 6px', fontSize:11}}>{pendingPwd}</span>}
        </button>
        <button className={tab==='approvals'?'on':''} onClick={()=>setTab('approvals')} style={{display:'inline-flex',alignItems:'center',gap:7}}>
          Согласование {pendingApprovals>0 && <span className="badge amber" style={{height:18, padding:'0 6px', fontSize:11}}>{pendingApprovals}</span>}
        </button>
      </div>

      {tab==='projects' && <ProjectsTab data={data} onOpen={setDetail} onCreate={async()=>{ await ensureCatalogs().catch(()=>{}); setCreateOpen(true); }}/>}
      {tab==='team' && <TeamTab data={data} onPwd={setPwdModal} onOpen={setCardEmp} onCreate={()=>setCreateEmp(true)} showToast={showToast}/>}
      {tab==='approvals' && <ApprovalsTab data={approvalsData} team={data.team} onChanged={()=>loadApprovals().catch(()=>{})} showToast={showToast}/>}

      {detail && <ProjectDrawer pid={detail} data={data} catalogs={catalogs} ensureCatalogs={ensureCatalogs}
        onClose={()=>setDetail(null)} onChanged={reload} onReport={()=>{ setDetail(null); onNav && onNav('reports'); }} showToast={showToast}/>}
      {createOpen && catalogs && <CreateProjectDrawer catalogs={catalogs} team={data.team}
        onClose={()=>setCreateOpen(false)} onSaved={()=>{ setCreateOpen(false); reload(); setTab('projects'); }} showToast={showToast}/>}
      {pwdModal && <TempPasswordModal req={pwdModal} onClose={()=>{ setPwdModal(null); reload(); }} showToast={showToast}/>}
      {cardEmp && <EmployeeCard empId={cardEmp} team={data.team} resets={data.resets}
        onPwd={setPwdModal} onClose={()=>setCardEmp(null)} onChanged={reload}
        onChat={()=>{ onNav && onNav('chat'); }} showToast={showToast}/>}
      {createEmp && <CreateEmployeeDrawer team={data.team}
        onClose={()=>setCreateEmp(false)} onSaved={()=>{ setCreateEmp(false); reload(); }} showToast={showToast}/>}
    </div>
  );
}

/* ---- Projects ---- */
const PROJ_FILTERS=[
  {id:'all',    label:'Все проекты'},
  {id:'ACTIVE', label:'Активный',      cls:'green'},
  {id:'risk',   label:'Под риском',    cls:'amber'},
  {id:'ON_HOLD',label:'Приостановлен', cls:''},
];
function ProjectsTab({ data, onOpen, onCreate }){
  const [q,setQ]=useState('');
  const [status,setStatus]=useState('all');
  const [filterOpen,setFilterOpen]=useState(false);
  const filterRef=useRef(null);
  useEffect(()=>{
    if(!filterOpen) return;
    const h=(e)=>{ if(filterRef.current && !filterRef.current.contains(e.target)) setFilterOpen(false); };
    document.addEventListener('mousedown',h);
    return ()=>document.removeEventListener('mousedown',h);
  },[filterOpen]);

  const rows = data.projects.map(p=>{
    const st=data.statsMap[p.id];
    const spent=st?Number(st.spent_hours):0;
    return { p, spent, risk:projectAtRisk(p, spent) };
  });

  const list=rows.filter(({p, risk})=>{
    if(status==='risk' && !risk) return false;
    if(status!=='all' && status!=='risk' && p.project_status.code!==status) return false;
    if(q.trim()){ const lo=q.toLowerCase();
      return p.name.toLowerCase().includes(lo)||(p.code||'').toLowerCase().includes(lo)||(p.client||'').toLowerCase().includes(lo); }
    return true;
  });
  const activeFilter=PROJ_FILTERS.find(f=>f.id===status);
  const ell={overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'};

  return (
    <div className="card" style={{padding:'18px 20px 8px'}}>
      <div style={{display:'flex', alignItems:'center', gap:12, marginBottom:6}}>
        <div style={{position:'relative', flex:1, maxWidth:300}}>
          <span style={{position:'absolute', left:11, top:9, color:'var(--text-3)'}}><Icon d={IC.search} size={16}/></span>
          <input className="input" value={q} onChange={e=>setQ(e.target.value)} style={{height:34, paddingLeft:34, fontSize:13}} placeholder="Поиск проекта…"/>
        </div>
        <div style={{position:'relative'}} ref={filterRef}>
          <button className="btn sm" onClick={()=>setFilterOpen(o=>!o)} style={{color:status!=='all'?'var(--accent-strong)':'var(--text)', borderColor:status!=='all'?'var(--accent)':undefined}}>
            <Icon d={IC.filter} size={14}/>{status==='all'?'Фильтр':activeFilter.label}
            {status!=='all' && <span onClick={e=>{e.stopPropagation();setStatus('all');}} style={{display:'inline-flex',marginLeft:2}}><Icon d={IC.x} size={13}/></span>}
          </button>
          {filterOpen && (
            <div className="card fade-in" style={{position:'absolute', top:'calc(100% + 6px)', left:0, zIndex:50, minWidth:190, padding:6, boxShadow:'var(--shadow-lg)'}}>
              <div className="muted" style={{fontSize:11, fontWeight:700, letterSpacing:'.04em', textTransform:'uppercase', padding:'6px 10px 4px'}}>Статус проекта</div>
              {PROJ_FILTERS.map(f=>{
                const on=status===f.id;
                return (
                  <button key={f.id} onClick={()=>{setStatus(f.id);setFilterOpen(false);}}
                    style={{display:'flex', alignItems:'center', gap:9, width:'100%', padding:'8px 10px', border:'none', borderRadius:8, cursor:'pointer', textAlign:'left', fontSize:13, fontWeight:on?700:500, background:on?'var(--accent-softer)':'transparent', color:on?'var(--accent-strong)':'var(--text)'}}
                    onMouseEnter={e=>{ if(!on) e.currentTarget.style.background='var(--surface-2)'; }}
                    onMouseLeave={e=>{ if(!on) e.currentTarget.style.background='transparent'; }}>
                    {f.id!=='all' ? <span className={'badge '+(f.cls||'')} style={{height:18,padding:'0 7px',fontSize:10.5}}><span className="dot"/>{f.label}</span> : <span style={{fontSize:13}}>Все проекты</span>}
                    <div style={{flex:1}}/>
                    {on && <Icon d={IC.check} size={14} stroke={2.6}/>}
                  </button>
                );
              })}
            </div>
          )}
        </div>
        <div style={{flex:1}}/>
        <button className="btn sm primary" onClick={onCreate}><Icon d={IC.plus} size={15}/>Добавить проект</button>
      </div>
      <table className="tbl" style={{marginTop:8, tableLayout:'fixed', width:'100%'}}>
        <colgroup>
          <col style={{width:'23%'}}/>
          <col style={{width:'13%'}}/>
          <col style={{width:'11%'}}/>
          <col style={{width:'11%'}}/>
          <col style={{width:'14%'}}/>
          <col style={{width:'17%'}}/>
          <col style={{width:'11%'}}/>
        </colgroup>
        <thead><tr>
          <th>Проект</th><th>Клиент</th><th>Руководитель</th><th>Прогресс (мес.)</th><th style={{textAlign:'right', whiteSpace:'nowrap'}}>Часы за месяц / бюджет</th><th>Период</th><th>Статус</th>
        </tr></thead>
        <tbody>
          {list.map(({p, spent, risk})=>{
            const cls = risk?'amber':(MGMT_STATUS_CLS[p.project_status.code] ?? '');
            const label = risk?'Под риском':p.project_status.name;
            const budget = p.budget_hours;
            const pct = budget? Math.min(Math.round(spent/budget*100),999):null;
            const over = budget && spent/budget>0.95;
            const color = p.color||'var(--accent)';
            return (
              <tr key={p.id} style={{cursor:'pointer'}} onClick={()=>onOpen(p.id)}>
                <td>
                  <div style={{display:'flex', alignItems:'center', gap:10, minWidth:0}}>
                    <span style={{width:32,height:32,flexShrink:0,borderRadius:8,background:color,color:'#fff',display:'flex',alignItems:'center',justifyContent:'center',fontWeight:700,fontSize:12.5,letterSpacing:'.01em',textTransform:'uppercase'}}>{(p.code||p.name).slice(0,2)}</span>
                    <div style={{minWidth:0}}><div style={{fontWeight:600, ...ell}} title={p.name}>{p.name}</div><div className="muted" style={{fontSize:11.5, ...ell}}>{p.code||'—'}</div></div>
                  </div>
                </td>
                <td className="muted" style={ell} title={p.client||''}>{p.client||'—'}</td>
                <td>{p.lead
                  ? <span style={{display:'inline-flex', alignItems:'center', gap:7, minWidth:0, maxWidth:'100%'}}><Avatar id={p.lead.id} name={p.lead.first_name+' '+p.lead.last_name} size={24}/><span style={ell}>{p.lead.first_name}</span></span>
                  : <span className="muted">—</span>}
                </td>
                <td>
                  {pct!==null ? (
                    <div style={{display:'flex', alignItems:'center', gap:8}}>
                      <div className="progress" style={{flex:1, minWidth:0}}><span style={{width:Math.min(pct,100)+'%', background:color}}/></div>
                      <span className="mono" style={{fontSize:11.5, fontWeight:600, flexShrink:0}}>{pct}%</span>
                    </div>
                  ) : <span className="muted">—</span>}
                </td>
                <td className="mono" style={{textAlign:'right', fontWeight:600, whiteSpace:'nowrap', color:over?'var(--red)':'var(--text)'}}>{spent||0} / {budget||'—'}</td>
                <td className="muted" style={{fontSize:11.5}}>
                  <div style={{lineHeight:1.6}}>
                    {p.start_date&&<div style={{color:'var(--text-3)'}}>{fmtDateY(p.start_date)}</div>}
                    {p.deadline&&<div style={{color:'var(--text-2)',fontWeight:600}}>{fmtDateY(p.deadline)}</div>}
                  </div>
                </td>
                <td><span className={'badge '+cls} style={{maxWidth:'100%'}}><span className="dot" style={{flexShrink:0}}/><span style={ell}>{label}</span></span></td>
              </tr>
            );})}
          {list.length===0 && (
            <tr><td colSpan={7}><div className="muted" style={{padding:'24px 4px', textAlign:'center', fontSize:13}}>Проекты не найдены</div></td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}

/* ---- Team ---- */
function TeamTab({ data, onPwd, onOpen, onCreate, showToast }){
  const [q,setQ]=useState('');
  const [view,setView]=useState('list');
  const [onlyDirect,setOnlyDirect]=useState(false);
  const myId = (API.session()||{}).userId;

  const filtered = useMemo(()=>{
    let list = onlyDirect ? data.team.filter(e=>e.lead_id===myId) : data.team;
    if(q.trim()){
      const lo=q.toLowerCase();
      list=list.filter(e=>e.name.toLowerCase().includes(lo)||(e.position||'').toLowerCase().includes(lo));
    }
    return list;
  },[data.team, q, onlyDirect]);

  const resetFor=(e)=>data.resets.find(r=>resetRequestMatches(r.identifier, e));

  return (
    <div style={{display:'flex',flexDirection:'column',gap:14}}>
      <div style={{display:'flex',alignItems:'center',gap:12,flexWrap:'wrap'}}>
        <div className="seg">
          <button className={view==='list'?'on':''} onClick={()=>setView('list')}><Icon d={IC.users} size={15}/>Список</button>
          <button className={view==='org'?'on':''} onClick={()=>setView('org')}><Icon d={IC.folder} size={15}/>Структура</button>
        </div>
        {view==='list' && (
          <div style={{position:'relative',flex:1,maxWidth:280}}>
            <span style={{position:'absolute',left:11,top:9,color:'var(--text-3)'}}><Icon d={IC.search} size={16}/></span>
            <input className="input" value={q} onChange={e=>setQ(e.target.value)} style={{height:34,paddingLeft:34,fontSize:13}} placeholder="Поиск сотрудника…"/>
          </div>
        )}
        {view==='list' && (
          <label style={{display:'flex',alignItems:'center',gap:8,cursor:'pointer',fontSize:13,fontWeight:600,color:'var(--text-2)',whiteSpace:'nowrap'}}>
            <input type="checkbox" checked={onlyDirect} onChange={e=>setOnlyDirect(e.target.checked)} style={{accentColor:'var(--accent)',width:15,height:15}}/>
            Только мои подчинённые
          </label>
        )}
        <div style={{flex:1}}/>
        <button className="btn sm primary" onClick={onCreate}><Icon d={IC.plus} size={15}/>Добавить сотрудника</button>
      </div>

      {view==='list' && (
        <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fill,minmax(290px,1fr))',gap:14}}>
          {filtered.map(e=>{
            const util=e.utilPct;
            const cl=util>100?'var(--red)':util>=85?'var(--green)':util>=60?'var(--accent)':'var(--amber)';
            const pwdReq=resetFor(e);
            return (
              <div key={e.id} className="card" style={{padding:18,cursor:'pointer'}} onClick={()=>onOpen(e.id)}>
                <div style={{display:'flex',gap:12,alignItems:'center'}}>
                  <Avatar id={e.id} name={e.name} size={46}/>
                  <div style={{flex:1,minWidth:0}}>
                    <div style={{fontWeight:700,fontSize:14.5}}>{e.name}</div>
                    <div className="muted" style={{fontSize:12}}>{e.position}</div>
                  </div>
                  {e.grade && <span className="badge accent">{e.grade}</span>}
                </div>
                <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-end',marginTop:16}}>
                  <div><div className="muted" style={{fontSize:11.5}}>Загрузка</div>
                    <div className="tnum" style={{fontSize:20,fontWeight:800,color:cl}}>{util}%</div>
                  </div>
                  <div style={{textAlign:'right'}}><div className="muted" style={{fontSize:11.5}}>Часов за месяц</div>
                    <div className="tnum" style={{fontSize:15,fontWeight:700}}>{e.logged} / {e.norm}</div>
                  </div>
                </div>
                <div className="progress" style={{marginTop:10}}><span style={{width:Math.min(util,100)+'%',background:cl}}/></div>
                <div style={{display:'flex',gap:6,marginTop:14,flexWrap:'wrap',alignItems:'center'}}>
                  {e.assignments.slice(0,3).map(a=>(
                    <span key={a.id} className="badge" style={{height:22,fontSize:11}}><span style={{width:7,height:7,borderRadius:2,background:a.project.color||'var(--accent)'}}/>{a.project.code||a.project.name.slice(0,6)}</span>
                  ))}
                  <div style={{flex:1}}/>
                  {pwdReq&&(
                    <button onClick={ev=>{ev.stopPropagation();onPwd({ ...pwdReq, emp:e });}} title="Запрос временного пароля"
                      style={{display:'flex',alignItems:'center',gap:5,padding:'4px 9px',border:'none',
                        borderRadius:999,background:'var(--amber-soft)',color:'oklch(0.48 0.12 70)',
                        cursor:'pointer',animation:'pulse 2s infinite'}}>
                      <span style={{width:7,height:7,borderRadius:50,background:'oklch(0.74 0.13 75)',
                        boxShadow:'0 0 0 2px oklch(0.74 0.13 75 / 0.35)',flexShrink:0}}/>
                      <Icon d={IC.key} size={13}/>
                    </button>
                  )}
                </div>
              </div>
            );
          })}
          {filtered.length===0 && <div className="muted" style={{fontSize:13, padding:12}}>Никого не нашлось</div>}
        </div>
      )}

      {view==='org' && <OrgChart team={data.team}/>}
      <style>{`@keyframes pulse{0%,100%{box-shadow:0 0 0 0 oklch(0.74 0.13 75/0.4);}50%{box-shadow:0 0 0 5px oklch(0.74 0.13 75/0);}}`}</style>
    </div>
  );
}

/* ---- OrgChart ---- */
function OrgChart({ team }){
  const roots = team.filter(e=>!e.lead_id);
  const childrenOf = (id)=>team.filter(e=>e.lead_id===id);

  function OrgNode({ e }){
    const children = childrenOf(e.id);
    const util=e.utilPct;
    const cl=util>100?'var(--red)':util>=85?'var(--green)':util>=60?'var(--accent)':'var(--amber)';
    const isMgr=!e.lead_id;
    return (
      <div style={{display:'flex',flexDirection:'column',alignItems:'center'}}>
        <div style={{display:'flex',alignItems:'center',gap:10,padding:'10px 14px',
            minWidth:210,maxWidth:248,flexShrink:0,
            border:`2px solid ${isMgr?'var(--accent)':'var(--border)'}`,
            borderRadius:12,background:isMgr?'var(--accent-softer)':'var(--surface)',
            textAlign:'left',boxShadow:'var(--shadow-sm)'}}>
          <Avatar id={e.id} name={e.name} size={36}/>
          <div style={{minWidth:0}}>
            <div style={{fontWeight:700,fontSize:13,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{e.name}</div>
            <div className="muted" style={{fontSize:11.5,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{e.position}</div>
            <div style={{display:'flex',alignItems:'center',gap:6,marginTop:4}}>
              {e.grade && <span className="badge accent" style={{height:18,padding:'0 6px',fontSize:10}}>{e.grade}</span>}
              <span className="tnum" style={{fontSize:11.5,fontWeight:700,color:cl}}>{util}%</span>
            </div>
          </div>
        </div>

        {children.length>0&&(
          <div style={{display:'flex',flexDirection:'column',alignItems:'center',width:'100%'}}>
            <div style={{width:2,height:22,background:'var(--border)',flexShrink:0}}/>
            {children.length===1?(
              <div style={{display:'flex',flexDirection:'column',alignItems:'center'}}>
                <OrgNode e={children[0]}/>
              </div>
            ):(
              <div style={{display:'flex',borderTop:'2px solid var(--border)'}}>
                {children.map(ch=>(
                  <div key={ch.id} style={{display:'flex',flexDirection:'column',alignItems:'center',
                    padding:'0 16px',flexShrink:0}}>
                    <div style={{width:2,height:22,background:'var(--border)'}}/>
                    <OrgNode e={ch}/>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="card" style={{padding:24,overflowX:'auto'}}>
      <div style={{display:'flex',gap:64,alignItems:'flex-start',justifyContent:'center',minWidth:'fit-content'}}>
        {roots.map(m=><OrgNode key={m.id} e={m}/>)}
      </div>
      <div className="muted" style={{fontSize:12,marginTop:18,textAlign:'center'}}>
        Иерархия строится по назначенным руководителям (lead)
      </div>
    </div>
  );
}

/* ---- Approvals: табели / переработки / командировки ---- */
const APPR_BADGE = {
  'На согласовании': { cls:'amber', label:'Ожидает' },
  'Согласован':      { cls:'green', label:'Утверждён' },
  'Согласовано':     { cls:'green', label:'Утверждено' },
  'Согласована':     { cls:'green', label:'Утверждена' },
  'Отклонён':        { cls:'red',   label:'Отклонён' },
  'Отклонено':       { cls:'red',   label:'Отклонено' },
  'Отклонена':       { cls:'red',   label:'Отклонена' },
  'Отменена':        { cls:'',      label:'Отменена' },
};
const apprBadge=(s)=>APPR_BADGE[s]||{ cls:'amber', label:s };
const isPending=(s)=>s==='На согласовании';
const monthLabel=(y,m)=>['Янв','Фев','Мар','Апр','Май','Июн','Июл','Авг','Сен','Окт','Ноя','Дек'][m-1]+' '+y;

function ApprovalsTab({ data, team, onChanged, showToast }){
  const [typeTab,setTypeTab]=useState('periods');
  const [statusFilter,setStatusFilter]=useState('pending'); // сиды дают десятки «Утверждён» — менеджеру важны ожидающие
  const [reject,setReject]=useState(null); // {kind, id, title}
  const [comment,setComment]=useState('');
  const [busy,setBusy]=useState(false);
  const empById=(id)=>team.find(e=>e.id===id);

  const items = useMemo(()=>{
    if(typeTab==='periods') return data.periods.map(p=>({
      kind:'period', id:p.id, status:p.submission_status,
      empName:`${p.employee.first_name} ${p.employee.last_name}`, empId:p.employee.id,
      main:'Табель за '+monthLabel(p.year,p.month), sub:p.rejection_comment?('Причина: '+p.rejection_comment):null,
      period:monthLabel(p.year,p.month), submitted:p.submitted_at,
    }));
    if(typeTab==='overtime') return data.overtime.map(a=>{
      const e=a.time_entry||{};
      const emp=e.employee_id?empById(e.employee_id):null;
      return {
        kind:'overtime', id:a.id, status:a.status,
        empName:emp?emp.name:'—', empId:e.employee_id, empPosition:emp?.position,
        main:'+'+Number(e.spend_time||0)+' ч '+(e.date_from?fmtDate(e.date_from):''),
        sub:[e.task_name, e.assignment?.project?.name].filter(Boolean).join(' · ')||null,
        period:e.date_from?monthLabel(+e.date_from.slice(0,4), +e.date_from.slice(5,7)):'—',
        submitted:a.created_at,
      };
    });
    return data.trips.map(a=>{
      const emp=empById(a.employee_id);
      return {
        kind:'trip', id:a.id, status:a.status,
        empName:emp?emp.name:'—', empId:a.employee_id, empPosition:emp?.position,
        main:fmtDateY(a.date_from)+' — '+fmtDateY(a.date_to),
        sub:a.days_count+' '+plural(a.days_count,'день','дня','дней')+(a.comment?' · '+a.comment.slice(0,40):''),
        period:monthLabel(+String(a.date_from).slice(0,4), +String(a.date_from).slice(5,7)),
        submitted:a.submitted_at,
      };
    });
  },[typeTab, data, team]);

  const cnt=(list)=>({
    all:list.length,
    pending:list.filter(i=>isPending(i.status)).length,
    approved:list.filter(i=>apprBadge(i.status).cls==='green').length,
    rejected:list.filter(i=>apprBadge(i.status).cls==='red').length,
  });
  const c=cnt(items);
  const filtered=items.filter(i=>{
    if(statusFilter==='pending') return isPending(i.status);
    if(statusFilter==='approved') return apprBadge(i.status).cls==='green';
    if(statusFilter==='rejected') return apprBadge(i.status).cls==='red';
    return true;
  });

  const approve=async(item)=>{
    setBusy(true);
    try{
      if(item.kind==='period') await API.timesheet.approvePeriod(item.id);
      else if(item.kind==='overtime') await API.timesheet.resolveOvertime(item.id, 'approve');
      else await API.absence.approveAbsence(item.id);
      showToast('Утверждено');
      onChanged();
    }catch(err){ showToast(err.detail||'Не удалось утвердить'); }
    finally{ setBusy(false); }
  };
  const doReject=async()=>{
    const item=reject;
    const text=comment.trim();
    if((item.kind==='period'||item.kind==='trip') && !text){ showToast('Укажите причину отклонения'); return; }
    setBusy(true);
    try{
      if(item.kind==='period') await API.timesheet.rejectPeriod(item.id, text);
      else if(item.kind==='overtime') await API.timesheet.resolveOvertime(item.id, 'reject', text||undefined);
      else await API.absence.rejectAbsence(item.id, text);
      showToast('Отклонено');
      setReject(null);
      onChanged();
    }catch(err){ showToast(err.detail||'Не удалось отклонить'); }
    finally{ setBusy(false); }
  };

  const STATUS_FILTERS=[
    {id:'all',      label:'Все',        count:c.all},
    {id:'pending',  label:'Ожидают',    count:c.pending},
    {id:'approved', label:'Утверждены', count:c.approved},
    {id:'rejected', label:'Отклонены',  count:c.rejected},
  ];

  return (
    <div className="card" style={{padding:'18px 20px 12px'}}>
      <div style={{display:'flex',alignItems:'center',gap:8,marginBottom:16}}>
        <div className="seg">
          {[['periods','Табели',data.periods.filter(p=>isPending(p.submission_status)).length],
            ['overtime','Переработки',data.overtime.filter(a=>isPending(a.status)).length],
            ['trip','Командировки',data.trips.filter(a=>isPending(a.status)).length]].map(([id,lbl,n])=>(
            <button key={id} className={typeTab===id?'on':''} onClick={()=>{setTypeTab(id);setStatusFilter('pending');}} style={{display:'inline-flex',alignItems:'center',gap:6}}>
              {lbl} {n>0&&<span className="badge amber" style={{height:16,padding:'0 5px',fontSize:10}}>{n}</span>}
            </button>
          ))}
        </div>
      </div>

      <div style={{display:'flex',gap:6,flexWrap:'wrap',marginBottom:16}}>
        {STATUS_FILTERS.map(f=>(
          <button key={f.id} onClick={()=>setStatusFilter(f.id)}
            style={{display:'inline-flex',alignItems:'center',gap:7,height:32,padding:'0 13px',
              borderRadius:'var(--radius-sm)',border:'1px solid',fontSize:13,fontWeight:600,cursor:'pointer',
              background:statusFilter===f.id?'var(--accent)':'var(--surface-2)',
              color:statusFilter===f.id?'#fff':'var(--text-2)',
              borderColor:statusFilter===f.id?'var(--accent)':'var(--border)',transition:'.14s'}}>
            {f.label}
            <span style={{display:'inline-flex',alignItems:'center',justifyContent:'center',
              minWidth:18,height:18,borderRadius:50,fontSize:10.5,fontWeight:700,padding:'0 4px',
              background:statusFilter===f.id?'rgba(255,255,255,0.22)':'var(--surface-3)',
              color:statusFilter===f.id?'#fff':'var(--text-3)'}}>
              {f.count}
            </span>
          </button>
        ))}
      </div>

      <table className="tbl" style={{tableLayout:'fixed',width:'100%'}}>
        <colgroup><col style={{width:'22%'}}/><col style={{width:'25%'}}/><col style={{width:'11%'}}/><col style={{width:'11%'}}/><col style={{width:'11%'}}/><col style={{width:'20%'}}/></colgroup>
        <thead><tr>
          <th>Сотрудник</th><th>{typeTab==='periods'?'Табель':typeTab==='overtime'?'Переработка':'Командировка'}</th>
          <th>Период</th><th>Отправлено</th><th>Статус</th>
          <th style={{textAlign:'right'}}>Действие</th>
        </tr></thead>
        <tbody>
          {filtered.map(item=>{
            const st=apprBadge(item.status);
            return (
              <tr key={item.kind+item.id}>
                <td style={{height:58}}><span style={{display:'inline-flex',alignItems:'center',gap:9}}>
                  <Avatar id={item.empId} name={item.empName} size={30}/>
                  <div><div style={{fontWeight:600,fontSize:13.5}}>{item.empName}</div>{item.empPosition&&<div className="muted" style={{fontSize:11}}>{item.empPosition}</div>}</div>
                </span></td>
                <td style={{height:58}}>
                  <div style={{fontSize:12.5,fontWeight:600,color:'oklch(0.48 0.12 70)'}}>{item.main}</div>
                  {item.sub&&<div className="muted" style={{fontSize:11.5,marginTop:2,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>{item.sub}</div>}
                </td>
                <td className="muted" style={{fontSize:12.5,height:58}}>{item.period}</td>
                <td className="muted mono" style={{fontSize:12,height:58}}>{item.submitted?fmtDate(item.submitted):'—'}</td>
                <td style={{height:58}}><span className={'badge '+st.cls}><span className="dot"/>{st.label}</span></td>
                <td style={{textAlign:'right',height:58}}>
                  {isPending(item.status)?(
                    <div style={{display:'inline-flex',gap:5,flexWrap:'nowrap',whiteSpace:'nowrap'}}>
                      <button className="btn sm" disabled={busy} onClick={()=>{setReject(item);setComment('');}} style={{color:'var(--red)',padding:'0 9px'}}><Icon d={IC.x} size={13}/>Отклонить</button>
                      <button className="btn sm primary" disabled={busy} onClick={()=>approve(item)} style={{padding:'0 9px'}}><Icon d={IC.check} size={13}/>Утвердить</button>
                    </div>
                  ):<span className="muted" style={{fontSize:12.5}}>—</span>}
                </td>
              </tr>
            );
          })}
          {filtered.length===0&&<tr><td colSpan={6}><div className="muted" style={{padding:'28px 4px',textAlign:'center',fontSize:13}}>Ничего нет по выбранным фильтрам</div></td></tr>}
        </tbody>
      </table>

      {reject && (
        <div style={{position:'fixed',inset:0,zIndex:200,display:'flex',alignItems:'center',justifyContent:'center',background:'oklch(0.2 0.02 255 / 0.55)',backdropFilter:'blur(4px)'}}
          onClick={e=>{ if(e.target===e.currentTarget) setReject(null); }}>
          <div className="card fade-in" style={{width:460,padding:28,boxShadow:'var(--shadow-lg)'}}>
            <h3 style={{margin:'0 0 6px', fontSize:17}}>Отклонить</h3>
            <p className="muted" style={{fontSize:13, margin:'0 0 16px', lineHeight:1.5}}>
              {reject.empName} · {reject.main}. {reject.kind==='overtime'?'Комментарий необязателен.':'Укажите причину — сотрудник получит уведомление.'}
            </p>
            <textarea className="input" style={{height:96, resize:'vertical', padding:'10px 12px', lineHeight:1.5}}
              value={comment} onChange={e=>setComment(e.target.value)} placeholder="Причина отклонения…"/>
            <div style={{display:'flex', gap:8, justifyContent:'flex-end', marginTop:16}}>
              <button className="btn" onClick={()=>setReject(null)}>Отмена</button>
              <button className="btn primary" style={{background:'var(--red)',borderColor:'var(--red)'}} disabled={busy} onClick={doReject}>Отклонить</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ---- Project Drawer ---- */
function ProjectDrawer({ pid, data, catalogs, ensureCatalogs, onClose, onChanged, onReport, showToast }){
  const p = data.projects.find(x=>x.id===pid);
  const stats = data.statsMap[pid];
  const spent = stats?Number(stats.spent_hours):0;
  const [edit,setEdit]=useState(false);
  const [saving,setSaving]=useState(false);
  const [name,setName]=useState(p?p.name:'');
  const [budget,setBudget]=useState(p&&p.budget_hours?String(p.budget_hours):'');
  const [editStartDate,setEditStartDate]=useState(p?.start_date||'');
  const [editDeadline,setEditDeadline]=useState(p?.deadline||'');
  const [addOpen,setAddOpen]=useState(false);
  if(!p) return null;

  const risk=projectAtRisk(p, spent);
  const cls = risk?'amber':(MGMT_STATUS_CLS[p.project_status.code] ?? '');
  const label = risk?'Под риском':p.project_status.name;
  const color=p.color||'var(--accent)';

  // Команда: сотрудники с активным назначением на проект
  const team = data.team
    .map(e=>({ e, asg:e.assignments.find(a=>a.project.id===pid) }))
    .filter(x=>x.asg);
  const candidates = data.team.filter(e=>!e.assignments.some(a=>a.project.id===pid));
  const budgetPct = p.budget_hours? Math.round(spent/p.budget_hours*100):null;
  const roles = catalogs?.roles||[];

  const startEdit=async()=>{
    await ensureCatalogs().catch(()=>{});
    setName(p.name); setBudget(p.budget_hours?String(p.budget_hours):'');
    setEditStartDate(p.start_date||''); setEditDeadline(p.deadline||'');
    setEdit(true);
  };
  const saveEdit=async()=>{
    setSaving(true);
    try{
      const body={};
      if(name.trim() && name.trim()!==p.name) body.name=name.trim();
      const b=parseFloat(budget);
      if(!isNaN(b) && b>0 && b!==p.budget_hours) body.budget_hours=b;
      if(editStartDate && editStartDate!==p.start_date) body.start_date=editStartDate;
      if(editDeadline && editDeadline!==p.deadline) body.deadline=editDeadline;
      if(Object.keys(body).length) await API.management.updateProject(pid, body);
      setEdit(false); setAddOpen(false);
      onChanged();
      showToast('Проект обновлён');
    }catch(err){ showToast(err.detail||'Не удалось сохранить'); }
    finally{ setSaving(false); }
  };

  const defaultRoleId = ()=>{ const r=roles.find(x=>x.name==='Разработчик')||roles[0]; return r?.id; };
  const activeAsgStatusId = ()=>{ const s=(catalogs?.asgStatuses||[]).find(x=>x.code==='ACTIVE'); return s?.id; };

  const addMember=async(emp)=>{
    try{
      await API.management.createAssignment(emp.id, {
        project_id:pid, project_role_id:defaultRoleId(), assignment_status_id:activeAsgStatusId(),
        start_date:new Date().toISOString().slice(0,10), end_date:p.deadline||p.end_date||undefined,
      });
      onChanged(); showToast(`${emp.name} добавлен в команду`);
    }catch(err){ showToast(err.detail||'Не удалось добавить'); }
  };
  const removeMember=async(emp, asg)=>{
    try{ await API.management.deleteAssignment(emp.id, asg.id); onChanged(); showToast(`${emp.name} убран из команды`); }
    catch(err){ showToast(err.detail||'Не удалось убрать'); }
  };
  const setRole=async(emp, asg, roleId)=>{
    try{ await API.management.updateAssignment(emp.id, asg.id, { project_role_id:roleId }); onChanged(); }
    catch(err){ showToast(err.detail||'Не удалось сменить роль'); }
  };

  return (
    <div style={{position:'fixed', inset:0, zIndex:120, display:'flex', justifyContent:'flex-end'}}>
      <div onClick={onClose} style={{position:'absolute', inset:0, background:'oklch(0.3 0.02 255 / 0.32)', backdropFilter:'blur(1px)'}}/>
      <div className="fade-in" style={{position:'relative', width:440, maxWidth:'92vw', height:'100%', background:'var(--surface)', borderLeft:'1px solid var(--border)', boxShadow:'var(--shadow-lg)', overflowY:'auto', padding:26}}>
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start'}}>
          <div style={{display:'flex', gap:12, alignItems:'center', flex:1, minWidth:0}}>
            <span style={{width:44,height:44,flexShrink:0,borderRadius:11,background:color,color:'#fff',display:'flex',alignItems:'center',justifyContent:'center',fontWeight:700,fontSize:15,textTransform:'uppercase'}}>{(p.code||p.name).slice(0,2)}</span>
            <div style={{flex:1,minWidth:0}}>
              {edit
                ? <input className="input" value={name} onChange={e=>setName(e.target.value)} style={{height:34,fontSize:16,fontWeight:700}} placeholder="Название проекта"/>
                : <h2 style={{fontSize:18}}>{p.name}</h2>}
              <div className="muted" style={{fontSize:12.5, marginTop:edit?6:0}}>{[p.client, p.code].filter(Boolean).join(' · ')||'—'}</div>
            </div>
          </div>
          <button className="btn ghost sm icon" onClick={onClose}><Icon d={IC.x} size={17}/></button>
        </div>
        <div style={{display:'flex', gap:8, marginTop:14}}>
          <span className={'badge '+cls}><span className="dot"/>{label}</span>
          {(p.start_date||p.deadline) && <span className="badge"><Icon d={IC.calendar} size={13}/>{p.start_date?fmtDateY(p.start_date)+' — ':''}{p.deadline?fmtDateY(p.deadline):'…'}</span>}
        </div>

        <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:12, marginTop:20}}>
          <div className="card" style={{padding:14, background:'var(--surface-2)'}}>
            <div className="muted" style={{fontSize:11.5, fontWeight:600}}>Руководитель</div>
            {p.lead ? (
              <div style={{display:'flex', alignItems:'center', gap:9, marginTop:10}}>
                <Avatar id={p.lead.id} name={p.lead.first_name+' '+p.lead.last_name} size={32}/>
                <div style={{fontWeight:700, fontSize:13}}>{p.lead.first_name}<br/>{p.lead.last_name}</div>
              </div>
            ) : <div className="muted" style={{marginTop:10}}>Не назначен</div>}
          </div>
          <div className="card" style={{padding:14, background:'var(--surface-2)'}}>
            <div className="muted" style={{fontSize:11.5, fontWeight:600}}>Бюджет часов · месяц</div>
            {edit ? (
              <>
                <input className="input" type="number" min="1" value={budget} onChange={e=>setBudget(e.target.value)} style={{height:34, marginTop:6, fontWeight:700}}/>
                <div className="muted mono" style={{fontSize:11.5, marginTop:8}}>списано {spent} ч за месяц</div>
              </>
            ) : budgetPct!==null ? (
              <>
                <div className="tnum" style={{fontSize:22, fontWeight:800, color:budgetPct>95?'var(--red)':'var(--text)'}}>{budgetPct}%</div>
                <div className="progress" style={{marginTop:8}}><span style={{width:Math.min(budgetPct,100)+'%', background:budgetPct>95?'var(--red)':color}}/></div>
                <div className="muted mono" style={{fontSize:11.5, marginTop:8}}>{spent} / {p.budget_hours} ч</div>
              </>
            ) : <div className="muted" style={{marginTop:10}}>Бюджет не задан</div>}
          </div>
        </div>

        {edit && (
          <div style={{marginTop:16,padding:'14px 16px',background:'var(--surface-2)',borderRadius:10,border:'1px solid var(--border)'}}>
            <div className="muted" style={{fontSize:12,fontWeight:600,marginBottom:10}}>Период проекта</div>
            <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
              <div>
                <div className="muted" style={{fontSize:11.5,marginBottom:4}}>Дата начала</div>
                <input className="input" type="date" value={editStartDate} onChange={e=>setEditStartDate(e.target.value)}/>
              </div>
              <div>
                <div className="muted" style={{fontSize:11.5,marginBottom:4}}>Срок завершения</div>
                <input className="input" type="date" value={editDeadline} onChange={e=>setEditDeadline(e.target.value)}/>
              </div>
            </div>
          </div>
        )}
        <div style={{marginTop:22}}>
          <SectionTitle title={'Команда · '+team.length} right={edit && (
            <button className="btn sm" onClick={()=>setAddOpen(o=>!o)} style={{color:addOpen?'var(--accent-strong)':'var(--text)'}}>
              <Icon d={IC.plus} size={14}/>Добавить
            </button>
          )}/>

          {edit && addOpen && (
            <div className="card" style={{marginTop:10, padding:8, background:'var(--surface-2)', maxHeight:240, overflowY:'auto'}}>
              {candidates.length===0 && <div className="muted" style={{fontSize:12.5, padding:'8px 6px'}}>Все сотрудники уже в команде</div>}
              {candidates.map(e=>(
                <button key={e.id} onClick={()=>addMember(e)}
                  style={{display:'flex', alignItems:'center', gap:10, width:'100%', padding:'7px 8px', border:'none', background:'transparent', borderRadius:8, cursor:'pointer', textAlign:'left'}}
                  onMouseEnter={ev=>ev.currentTarget.style.background='var(--surface-3)'}
                  onMouseLeave={ev=>ev.currentTarget.style.background='transparent'}>
                  <Avatar id={e.id} name={e.name} size={30}/>
                  <div style={{flex:1, minWidth:0}}><div style={{fontWeight:600, fontSize:13}}>{e.name}</div><div className="muted" style={{fontSize:11.5}}>{e.position}</div></div>
                  <span style={{width:24,height:24,borderRadius:50,flexShrink:0,background:'var(--accent-soft)',color:'var(--accent-strong)',display:'flex',alignItems:'center',justifyContent:'center'}}><Icon d={IC.plus} size={14} stroke={2.6}/></span>
                </button>
              ))}
            </div>
          )}

          <div style={{display:'flex', flexDirection:'column', gap:8, marginTop:12}}>
            {team.map(({e, asg})=>(
              <div key={e.id} style={{display:'flex', alignItems:'center', gap:10, padding:'8px 10px', border:'1px solid var(--border)', borderRadius:9}}>
                <Avatar id={e.id} name={e.name} size={32}/>
                <div style={{flex:1, minWidth:0}}>
                  <div style={{fontWeight:600, fontSize:13, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{e.name}</div>
                  <div className="muted" style={{fontSize:11.5, overflow:'hidden', textOverflow:'ellipsis', whiteSpace:'nowrap'}}>{e.position}</div>
                  {edit ? (
                    <select value={asg.project_role.id} onChange={ev=>setRole(e, asg, ev.target.value)} onClick={ev=>ev.stopPropagation()}
                      style={{marginTop:6, height:30, width:'100%', padding:'0 8px', borderRadius:7, border:'1px solid var(--border-strong)', background:'var(--surface)', color:'var(--text)', fontSize:12.5, fontWeight:600, cursor:'pointer', outline:'none'}}>
                      {roles.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}
                    </select>
                  ) : (
                    <div style={{marginTop:3, display:'inline-flex'}}><span className="badge accent" style={{height:18, padding:'0 8px', fontSize:11}}>{asg.project_role.name}</span></div>
                  )}
                </div>
                {edit
                  ? <button className="btn ghost sm icon" title="Убрать из команды" onClick={()=>removeMember(e, asg)} style={{color:'var(--red)', flexShrink:0, alignSelf:'flex-start'}}><Icon d={IC.x} size={15}/></button>
                  : <span className="mono muted" style={{fontSize:12, flexShrink:0}}>{e.utilPct}%</span>}
              </div>
            ))}
            {team.length===0 && <div className="muted" style={{fontSize:12.5, padding:'4px 2px'}}>В команде пока нет сотрудников</div>}
          </div>
        </div>

        <div style={{display:'flex', gap:8, marginTop:24}}>
          {edit ? (
            <>
              <button className="btn" style={{flex:1}} onClick={()=>{ setEdit(false); setAddOpen(false); }} disabled={saving}>Готово</button>
              <button className="btn primary" style={{flex:1}} onClick={saveEdit} disabled={saving}><Icon d={IC.check} size={15}/>{saving?'Сохранение…':'Сохранить'}</button>
            </>
          ) : (
            <>
              <button className="btn" style={{flex:1}} onClick={startEdit}><Icon d={IC.edit} size={15}/>Редактировать</button>
              <button className="btn primary" style={{flex:1}} onClick={onReport}><Icon d={IC.chart} size={15}/>Отчёт</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/* ---- TempPasswordModal: выдача серверного временного пароля ---- */
function TempPasswordModal({ req, onClose, showToast }){
  const e = req.emp;
  const [copied,setCopied]=useState(false);
  const [tempPwd,setTempPwd]=useState(null);
  const [busy,setBusy]=useState(false);

  const resolve=async()=>{
    setBusy(true);
    try{
      const res=await API.auth.resolveResetRequest(req.id);
      setTempPwd(res.temp_password);
    }catch(err){ showToast(err.detail||'Не удалось выдать пароль'); }
    finally{ setBusy(false); }
  };

  const copy=()=>{
    navigator.clipboard.writeText(tempPwd).catch(()=>{});
    setCopied(true);
    setTimeout(()=>setCopied(false),2000);
  };

  return (
    <div style={{position:'fixed',inset:0,zIndex:150,display:'flex',alignItems:'center',justifyContent:'center'}}>
      <div onClick={onClose} style={{position:'absolute',inset:0,background:'oklch(0.3 0.02 255 / 0.45)',backdropFilter:'blur(3px)'}}/>
      <div className="card fade-in" style={{position:'relative',width:420,maxWidth:'92vw',padding:28,boxShadow:'var(--shadow-lg)'}}>
        <div style={{display:'flex',alignItems:'flex-start',justifyContent:'space-between',marginBottom:18}}>
          <div style={{display:'flex',gap:12,alignItems:'center'}}>
            <span style={{width:44,height:44,borderRadius:11,background:'var(--amber-soft)',display:'flex',alignItems:'center',justifyContent:'center'}}>
              <Icon d={IC.key} size={22} style={{color:'oklch(0.48 0.12 70)'}}/>
            </span>
            <div>
              <h3 style={{fontSize:16}}>Временный пароль</h3>
              <div className="muted" style={{fontSize:12.5,marginTop:2}}>{e.name} · {e.position}</div>
            </div>
          </div>
          <button className="btn ghost sm icon" onClick={onClose}><Icon d={IC.x} size={17}/></button>
        </div>

        <div style={{padding:'14px 16px',background:'var(--amber-soft)',borderRadius:10,border:'1px solid oklch(0.74 0.13 75 / 0.3)',marginBottom:18}}>
          <div className="muted" style={{fontSize:11.5,fontWeight:600,marginBottom:6}}>ЗАПРОС ПОЛУЧЕН</div>
          <div style={{fontSize:13.5,lineHeight:1.5}}>
            Сотрудник запросил сброс пароля. Система сгенерирует временный пароль — передайте его по защищённому каналу связи.
          </div>
          <div className="muted" style={{fontSize:11.5,marginTop:6}}>
            Запрос от: {new Date(req.requested_at).toLocaleString('ru',{day:'numeric',month:'long',hour:'2-digit',minute:'2-digit'})}
          </div>
        </div>

        {tempPwd ? (
          <div style={{marginBottom:18}}>
            <div className="muted" style={{fontSize:12,fontWeight:600,marginBottom:8}}>Временный пароль</div>
            <div style={{display:'flex',gap:8}}>
              <div style={{flex:1,padding:'10px 14px',background:'var(--surface-2)',border:'1px solid var(--border)',borderRadius:9,
                fontFamily:'var(--mono)',fontSize:16,fontWeight:700,letterSpacing:'.1em',userSelect:'all'}}>
                {tempPwd}
              </div>
              <button className="btn" onClick={copy} style={{flexShrink:0,gap:6,color:copied?'var(--green)':'var(--text)'}}>
                <Icon d={copied?IC.check:IC.copy} size={16}/>
                {copied?'Скопировано':'Копировать'}
              </button>
            </div>
            <div className="muted" style={{fontSize:11.5,marginTop:6}}>
              После первого входа сотрудник обязан сменить пароль
            </div>
          </div>
        ) : (
          <div className="muted" style={{fontSize:13, marginBottom:18}}>
            Нажмите «Выдать пароль» — бэкенд сбросит пароль сотрудника и вернёт временный.
          </div>
        )}

        <div style={{display:'flex',gap:8}}>
          <button className="btn" style={{flex:1}} onClick={onClose}>{tempPwd?'Готово':'Отмена'}</button>
          {!tempPwd && (
            <button className="btn primary" style={{flex:1}} onClick={resolve} disabled={busy}>
              <Icon d={IC.check} size={15}/>{busy?'Генерация…':'Выдать пароль'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function fmtDate(iso){ const d=new Date(iso); return d.getDate()+' '+['янв','фев','мар','апр','мая','июн','июл','авг','сен','окт','ноя','дек'][d.getMonth()]; }
function fmtDateY(iso){ const d=new Date(iso); return d.getDate()+' '+['янв','фев','мар','апр','мая','июн','июл','авг','сен','окт','ноя','дек'][d.getMonth()]+' '+d.getFullYear(); }

/* ============ CREATE PROJECT DRAWER ============ */
function CreateProjectDrawer({ catalogs, team, onClose, onSaved, showToast }){
  const [step,setStep]=useState(1);
  const statuses=catalogs.statuses;
  const roles=catalogs.roles;
  const activeStatus=statuses.find(s=>s.code==='ACTIVE')||statuses[0];
  const leads=team.filter(e=>e.roles.includes('Менеджер')||e.roles.includes('Тимлид'));
  const defaultRole=(roles.find(r=>r.name==='Разработчик')||roles[0]);

  const [form,setForm]=useState({
    name:'', code:'', client:'', lead:leads[0]?.id||'',
    budget:'', startDate:'', deadline:'', color:PROJECT_COLORS[0].val, statusId:activeStatus?.id||'',
  });
  const [teamIds,setTeamIds]=useState([]);
  const [memberRoles,setMemberRoles]=useState({});
  const [errors,setErrors]=useState({});
  const [saving,setSaving]=useState(false);

  const set=(k,v)=>setForm(f=>({...f,[k]:v}));

  const autoCode=(n)=>n.toUpperCase().replace(/[^A-ZА-ЯЁ0-9]/gi,'').slice(0,6)||'';
  const onNameChange=(v)=>{
    setForm(f=>({...f, name:v, code:(!f.code||f.code===autoCode(f.name))?autoCode(v):f.code}));
  };

  const validate1=()=>{
    const e={};
    if(!form.name.trim()) e.name='Введите название';
    if(!form.code.trim()) e.code='Введите код';
    if(!form.client.trim()) e.client='Введите клиента';
    if(!form.budget||isNaN(+form.budget)||+form.budget<=0) e.budget='Введите бюджет';
    if(!form.deadline) e.deadline='Выберите срок';
    setErrors(e);
    return Object.keys(e).length===0;
  };

  const next=()=>{ if(validate1()) setStep(2); };

  const save=async()=>{
    setSaving(true);
    try{
      const project=await API.management.createProject({
        name:form.name.trim(),
        code:form.code.toUpperCase(),
        client:form.client.trim(),
        color:form.color,
        project_status_id:form.statusId,
        lead_id:form.lead||undefined,
        budget_hours:+form.budget,
        start_date:form.startDate||undefined,
        deadline:form.deadline,
      });
      const asgStatus=(catalogs.asgStatuses.find(s=>s.code==='ACTIVE')||catalogs.asgStatuses[0]);
      for(const empId of teamIds){
        await API.management.createAssignment(empId, {
          project_id:project.id,
          project_role_id:memberRoles[empId]||defaultRole?.id,
          assignment_status_id:asgStatus?.id,
          start_date:form.startDate||new Date().toISOString().slice(0,10),
          end_date:form.deadline,
        }).catch(err=>showToast(err.detail||'Не удалось назначить сотрудника'));
      }
      showToast('Проект «'+project.name+'» создан');
      onSaved();
    }catch(err){
      showToast(err.detail||'Не удалось создать проект');
      setStep(1);
    }finally{ setSaving(false); }
  };

  const toggleMember=(id)=>{
    setTeamIds(t=>t.includes(id)?t.filter(x=>x!==id):[...t,id]);
    setMemberRoles(r=>({ ...r, [id]: r[id]||defaultRole?.id }));
  };

  const Err=({k})=>errors[k]?<div style={{color:'var(--red)',fontSize:11.5,marginTop:4}}>{errors[k]}</div>:null;

  return (
    <div style={{position:'fixed',inset:0,zIndex:120,display:'flex',justifyContent:'flex-end'}}>
      <div onClick={onClose} style={{position:'absolute',inset:0,background:'oklch(0.3 0.02 255 / 0.32)',backdropFilter:'blur(1px)'}}/>
      <div className="fade-in" style={{position:'relative',width:520,maxWidth:'94vw',height:'100%',background:'var(--surface)',borderLeft:'1px solid var(--border)',boxShadow:'var(--shadow-lg)',display:'flex',flexDirection:'column'}}>

        {/* header */}
        <div style={{padding:'22px 26px 18px',borderBottom:'1px solid var(--border)',display:'flex',alignItems:'center',gap:14,flexShrink:0}}>
          <div style={{width:40,height:40,borderRadius:10,background:form.color,display:'flex',alignItems:'center',justifyContent:'center',color:'#fff',fontWeight:800,fontSize:14,flexShrink:0,transition:'background .2s'}}>
            {form.code.slice(0,2)||<Icon d={IC.folder} size={18}/>}
          </div>
          <div style={{flex:1,minWidth:0}}>
            <h2 style={{fontSize:17}}>{form.name||'Новый проект'}</h2>
            <div className="muted" style={{fontSize:12.5}}>{form.client||'Клиент не указан'}</div>
          </div>
          <div style={{display:'flex',alignItems:'center',gap:6}}>
            {[1,2].map(s=>(
              <React.Fragment key={s}>
                <div style={{width:26,height:26,borderRadius:50,display:'flex',alignItems:'center',justifyContent:'center',fontWeight:700,fontSize:12,
                  background:step>=s?'var(--accent)':'var(--surface-3)',color:step>=s?'#fff':'var(--text-3)',transition:'background .2s'}}>{s}</div>
                {s<2&&<div style={{width:20,height:2,borderRadius:1,background:step>1?'var(--accent)':'var(--border)',transition:'background .2s'}}/>}
              </React.Fragment>
            ))}
          </div>
          <button className="btn ghost sm icon" onClick={onClose}><Icon d={IC.x} size={17}/></button>
        </div>

        {/* body */}
        <div style={{flex:1,overflowY:'auto',padding:'24px 26px'}}>
          {step===1 && (
            <div style={{display:'flex',flexDirection:'column',gap:18}}>
              <div style={{fontWeight:700,fontSize:15,marginBottom:-4}}>Основная информация</div>

              <div style={{display:'grid',gridTemplateColumns:'1fr auto',gap:12}}>
                <div>
                  <Field label="Название проекта *">
                    <input className="input" value={form.name} onChange={e=>onNameChange(e.target.value)} placeholder="Omnichannel платформа"/>
                    <Err k="name"/>
                  </Field>
                </div>
                <div style={{width:120}}>
                  <Field label="Код проекта *">
                    <input className="input" value={form.code} onChange={e=>set('code',e.target.value.toUpperCase().slice(0,6))} placeholder="OMNI" style={{fontFamily:'var(--mono)',fontWeight:700,letterSpacing:'.04em'}}/>
                    <Err k="code"/>
                  </Field>
                </div>
              </div>

              <Field label="Клиент *">
                <input className="input" value={form.client} onChange={e=>set('client',e.target.value)} placeholder="Название компании-заказчика"/>
                <Err k="client"/>
              </Field>

              <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
                <Field label="Руководитель проекта">
                  <select className="input" value={form.lead} onChange={e=>set('lead',e.target.value)} style={{cursor:'pointer'}}>
                    <option value="">— Не назначен —</option>
                    {leads.map(e=><option key={e.id} value={e.id}>{e.name}</option>)}
                  </select>
                </Field>
                <Field label="Статус">
                  <select className="input" value={form.statusId} onChange={e=>set('statusId',e.target.value)} style={{cursor:'pointer'}}>
                    {statuses.map(s=><option key={s.id} value={s.id}>{s.name}</option>)}
                  </select>
                </Field>
              </div>

              <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
                <Field label="Дата начала">
                  <input className="input" type="date" value={form.startDate} onChange={e=>set('startDate',e.target.value)}/>
                </Field>
                <Field label="Срок завершения *">
                  <input className="input" type="date" value={form.deadline} onChange={e=>set('deadline',e.target.value)}/>
                  <Err k="deadline"/>
                </Field>
              </div>

              <Field label="Бюджет (часов) *">
                <input className="input" type="number" min="1" value={form.budget} onChange={e=>set('budget',e.target.value)} placeholder="1600"/>
                <Err k="budget"/>
              </Field>

              <div>
                <div className="muted" style={{fontSize:12,fontWeight:600,marginBottom:10}}>Цвет проекта</div>
                <div style={{display:'flex',gap:10,flexWrap:'wrap'}}>
                  {PROJECT_COLORS.map(c=>(
                    <button key={c.val} onClick={()=>set('color',c.val)} title={c.label}
                      style={{width:34,height:34,borderRadius:9,background:c.val,border:`3px solid ${form.color===c.val?'var(--text)':'transparent'}`,
                        cursor:'pointer',display:'flex',alignItems:'center',justifyContent:'center',transition:'.14s',transform:form.color===c.val?'scale(1.12)':'scale(1)'}}>
                      {form.color===c.val&&<Icon d={IC.check} size={15} stroke={3} style={{color:'#fff'}}/>}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {step===2 && (
            <div style={{display:'flex',flexDirection:'column',gap:14}}>
              <div>
                <div style={{fontWeight:700,fontSize:15}}>Команда проекта</div>
                <div className="muted" style={{fontSize:13,marginTop:3}}>Выберите сотрудников для участия в проекте</div>
              </div>
              {team.map(e=>{
                const on=teamIds.includes(e.id);
                const util=e.utilPct;
                const uColor=util>100?'var(--red)':util>=85?'var(--green)':util>=60?'var(--accent)':'var(--amber)';
                return (
                  <div key={e.id} style={{border:`1px solid ${on?'var(--accent)':'var(--border)'}`,borderRadius:11,background:on?'var(--accent-softer)':'var(--surface)',transition:'.14s',overflow:'hidden'}}>
                    <button onClick={()=>toggleMember(e.id)}
                      style={{display:'flex',alignItems:'center',gap:13,padding:'12px 14px',border:'none',
                        background:'transparent',cursor:'pointer',textAlign:'left',width:'100%'}}>
                      <Avatar id={e.id} name={e.name} size={38} ring={on}/>
                      <div style={{flex:1,minWidth:0}}>
                        <div style={{fontWeight:600,fontSize:14}}>{e.name}</div>
                        <div className="muted" style={{fontSize:12}}>{[e.position, e.dept].filter(Boolean).join(' · ')}</div>
                      </div>
                      <div style={{textAlign:'right',flexShrink:0}}>
                        <div className="tnum" style={{fontWeight:700,fontSize:13,color:uColor}}>{util}%</div>
                        <div className="muted" style={{fontSize:11}}>загрузка</div>
                      </div>
                      <div style={{width:22,height:22,borderRadius:50,flexShrink:0,border:`2px solid ${on?'var(--accent)':'var(--border)'}`,
                        background:on?'var(--accent)':'transparent',display:'flex',alignItems:'center',justifyContent:'center',transition:'.14s'}}>
                        {on&&<Icon d={IC.check} size={12} stroke={3} style={{color:'#fff'}}/>}
                      </div>
                    </button>
                    {on && (
                      <div style={{padding:'0 14px 12px',display:'flex',alignItems:'center',gap:10}}>
                        <span className="muted" style={{fontSize:12,fontWeight:600,flexShrink:0}}>Роль на проекте:</span>
                        <select value={memberRoles[e.id]||defaultRole?.id}
                          onChange={ev=>{ ev.stopPropagation(); setMemberRoles(r=>({...r,[e.id]:ev.target.value})); }}
                          onClick={ev=>ev.stopPropagation()}
                          style={{flex:1,height:32,padding:'0 10px',borderRadius:8,border:'1px solid var(--border-strong)',
                            background:'var(--surface)',fontSize:13,fontWeight:600,cursor:'pointer',outline:'none',color:'var(--text)'}}>
                          {roles.map(r=><option key={r.id} value={r.id}>{r.name}</option>)}
                        </select>
                      </div>
                    )}
                  </div>
                );
              })}
              {teamIds.length>0&&(
                <div style={{display:'flex',alignItems:'center',gap:8,padding:'10px 14px',background:'var(--accent-softer)',borderRadius:10,marginTop:4}}>
                  <span style={{fontSize:13,fontWeight:600,color:'var(--accent-strong)'}}>Выбрано {teamIds.length} {teamIds.length===1?'сотрудник':teamIds.length<5?'сотрудника':'сотрудников'}</span>
                </div>
              )}
            </div>
          )}
        </div>

        {/* footer */}
        <div style={{padding:'16px 26px',borderTop:'1px solid var(--border)',display:'flex',gap:10,alignItems:'center',flexShrink:0}}>
          {step===1?(
            <>
              <button className="btn" onClick={onClose}>Отмена</button>
              <div style={{flex:1}}/>
              <button className="btn primary" onClick={next}>Далее · Команда<Icon d={IC.chevR} size={16}/></button>
            </>
          ):(
            <>
              <button className="btn ghost" onClick={()=>setStep(1)} disabled={saving}><Icon d={IC.chevL} size={16}/>Назад</button>
              <div style={{flex:1}}/>
              <button className="btn primary" onClick={save} disabled={saving}><Icon d={IC.check} size={15}/>{saving?'Создание…':'Создать проект'}</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/* ============ CREATE EMPLOYEE DRAWER ============ */
// Временный пароль под правила бэка: 8+, заглавная, строчная, цифра, спецсимвол
function genTempPassword(){
  const U='ABCDEFGHJKMNPQRSTUVWXYZ', L='abcdefghjkmnpqrstuvwxyz', D='23456789', S='!@#$%';
  const pick=(s,n)=>Array.from({length:n},()=>s[Math.floor(Math.random()*s.length)]).join('');
  return pick(U,2)+pick(L,4)+pick(D,3)+pick(S,1);
}

function CreateEmployeeDrawer({ team, onClose, onSaved, showToast }){
  const [step,setStep]=useState(1);
  const [cats,setCats]=useState(null); // {roles, departments, grades}
  const [form,setForm]=useState({
    email:'', password:genTempPassword(), roleIds:[],
    firstName:'', lastName:'', position:'', departmentId:'', gradeId:'', leadId:'',
  });
  const [errors,setErrors]=useState({});
  const [saving,setSaving]=useState(false);
  const [created,setCreated]=useState(null); // UserRead после регистрации
  const [copied,setCopied]=useState(null);   // 'number' | 'password'

  useEffect(()=>{
    Promise.all([
      API.management.getRoles(),
      API.profile.getDepartments(),
      API.profile.getGrades(),
    ]).then(([roles, departments, grades])=>{
      setCats({ roles, departments, grades });
      const emp=roles.find(r=>r.name==='Сотрудник');
      if(emp) setForm(f=>f.roleIds.length?f:{ ...f, roleIds:[emp.id] });
    }).catch(err=>{ showToast(err.detail||'Не удалось загрузить справочники'); onClose(); });
  },[]);

  const set=(k,v)=>setForm(f=>({...f,[k]:v}));
  const toggleRole=(id)=>setForm(f=>({ ...f, roleIds:f.roleIds.includes(id)?f.roleIds.filter(x=>x!==id):[...f.roleIds,id] }));

  const validate1=()=>{
    const e={};
    if(!form.email.includes('@')) e.email='Введите рабочую почту';
    if(form.password.length<8) e.password='Минимум 8 символов';
    if(form.roleIds.length===0) e.roles='Выберите хотя бы одну роль';
    setErrors(e);
    return Object.keys(e).length===0;
  };
  const validate2=()=>{
    const e={};
    if(!form.firstName.trim()) e.firstName='Введите имя';
    if(!form.lastName.trim()) e.lastName='Введите фамилию';
    setErrors(e);
    return Object.keys(e).length===0;
  };

  // Kafka разносит профиль по сервисам асинхронно — ретраим, пока реплика не появится
  const waitFor=async(fn, tries=15)=>{
    for(let i=0;;i++){
      try{ return await fn(); }
      catch(err){
        if(i>=tries-1) throw err;
        await new Promise(r=>setTimeout(r,700));
      }
    }
  };

  const save=async()=>{
    if(!validate2()) return;
    setSaving(true);
    try{
      const user=await API.auth.register({ email:form.email.trim(), password:form.password, role_ids:form.roleIds });
      await waitFor(()=>API.profile.updateEmployee(user.id, {
        first_name:form.firstName.trim(),
        last_name:form.lastName.trim(),
        position:form.position.trim()||undefined,
        department_id:form.departmentId||undefined,
        grade_id:form.gradeId||undefined,
      }));
      if(form.leadId) await waitFor(()=>API.management.setLead(user.id, form.leadId));
      setCreated(user);
    }catch(err){ showToast(err.detail||'Не удалось создать сотрудника'); }
    finally{ setSaving(false); }
  };

  const copy=(what, text)=>{
    navigator.clipboard.writeText(text).catch(()=>{});
    setCopied(what);
    setTimeout(()=>setCopied(null),2000);
  };

  const Err=({k})=>errors[k]?<div style={{color:'var(--red)',fontSize:11.5,marginTop:4}}>{errors[k]}</div>:null;
  const initials=(form.firstName[0]||'')+(form.lastName[0]||'');

  return (
    <div style={{position:'fixed',inset:0,zIndex:120,display:'flex',justifyContent:'flex-end'}}>
      <div onClick={created?undefined:onClose} style={{position:'absolute',inset:0,background:'oklch(0.3 0.02 255 / 0.32)',backdropFilter:'blur(1px)'}}/>
      <div className="fade-in" style={{position:'relative',width:520,maxWidth:'94vw',height:'100%',background:'var(--surface)',borderLeft:'1px solid var(--border)',boxShadow:'var(--shadow-lg)',display:'flex',flexDirection:'column'}}>

        {/* header */}
        <div style={{padding:'22px 26px 18px',borderBottom:'1px solid var(--border)',display:'flex',alignItems:'center',gap:14,flexShrink:0}}>
          <div style={{width:40,height:40,borderRadius:50,background:'var(--accent)',display:'flex',alignItems:'center',justifyContent:'center',color:'#fff',fontWeight:800,fontSize:14,flexShrink:0}}>
            {initials.toUpperCase()||<Icon d={IC.user} size={18}/>}
          </div>
          <div style={{flex:1,minWidth:0}}>
            <h2 style={{fontSize:17}}>{(form.firstName||form.lastName)?`${form.firstName} ${form.lastName}`.trim():'Новый сотрудник'}</h2>
            <div className="muted" style={{fontSize:12.5}}>{form.email||'Почта не указана'}</div>
          </div>
          {!created&&(
            <div style={{display:'flex',alignItems:'center',gap:6}}>
              {[1,2].map(s=>(
                <React.Fragment key={s}>
                  <div style={{width:26,height:26,borderRadius:50,display:'flex',alignItems:'center',justifyContent:'center',fontWeight:700,fontSize:12,
                    background:step>=s?'var(--accent)':'var(--surface-3)',color:step>=s?'#fff':'var(--text-3)',transition:'background .2s'}}>{s}</div>
                  {s<2&&<div style={{width:20,height:2,borderRadius:1,background:step>1?'var(--accent)':'var(--border)',transition:'background .2s'}}/>}
                </React.Fragment>
              ))}
            </div>
          )}
          <button className="btn ghost sm icon" onClick={created?onSaved:onClose}><Icon d={IC.x} size={17}/></button>
        </div>

        {/* body */}
        <div style={{flex:1,overflowY:'auto',padding:'24px 26px'}}>
          {!cats&&<div style={{display:'flex',flexDirection:'column',gap:12}}>{[0,1,2].map(i=><div key={i} className="skel" style={{height:56}}/>)}</div>}

          {cats&&created&&(
            <div style={{display:'flex',flexDirection:'column',gap:18}}>
              <div style={{display:'flex',gap:12,alignItems:'center',padding:'14px 16px',background:'var(--green-soft)',borderRadius:10,border:'1px solid oklch(0.62 0.13 155 / 0.3)'}}>
                <Icon d={IC.check} size={20} style={{color:'var(--green)',flexShrink:0}}/>
                <div style={{fontSize:13.5,lineHeight:1.5}}>
                  Учётная запись <b>{form.firstName} {form.lastName}</b> создана. Передайте сотруднику данные для первого входа по защищённому каналу.
                </div>
              </div>
              <div>
                <div className="muted" style={{fontSize:12,fontWeight:600,marginBottom:8}}>Табельный номер</div>
                <div style={{display:'flex',gap:8}}>
                  <div style={{flex:1,padding:'10px 14px',background:'var(--surface-2)',border:'1px solid var(--border)',borderRadius:9,
                    fontFamily:'var(--mono)',fontSize:16,fontWeight:700,letterSpacing:'.06em',userSelect:'all'}}>{created.number}</div>
                  <button className="btn" onClick={()=>copy('number', created.number)} style={{flexShrink:0,gap:6,color:copied==='number'?'var(--green)':'var(--text)'}}>
                    <Icon d={copied==='number'?IC.check:IC.copy} size={16}/>{copied==='number'?'Скопировано':'Копировать'}
                  </button>
                </div>
              </div>
              <div>
                <div className="muted" style={{fontSize:12,fontWeight:600,marginBottom:8}}>Временный пароль</div>
                <div style={{display:'flex',gap:8}}>
                  <div style={{flex:1,padding:'10px 14px',background:'var(--surface-2)',border:'1px solid var(--border)',borderRadius:9,
                    fontFamily:'var(--mono)',fontSize:16,fontWeight:700,letterSpacing:'.1em',userSelect:'all'}}>{form.password}</div>
                  <button className="btn" onClick={()=>copy('password', form.password)} style={{flexShrink:0,gap:6,color:copied==='password'?'var(--green)':'var(--text)'}}>
                    <Icon d={copied==='password'?IC.check:IC.copy} size={16}/>{copied==='password'?'Скопировано':'Копировать'}
                  </button>
                </div>
                <div className="muted" style={{fontSize:11.5,marginTop:6}}>Вход — по почте {form.email} или табельному номеру</div>
              </div>
            </div>
          )}

          {cats&&!created&&step===1&&(
            <div style={{display:'flex',flexDirection:'column',gap:18}}>
              <div style={{fontWeight:700,fontSize:15,marginBottom:-4}}>Учётная запись</div>

              <Field label="Рабочая почта *">
                <input className="input" type="email" value={form.email} onChange={e=>set('email',e.target.value)} placeholder="ivanov@demo.com"/>
                <Err k="email"/>
              </Field>

              <Field label="Временный пароль *">
                <div style={{display:'flex',gap:8}}>
                  <input className="input" value={form.password} onChange={e=>set('password',e.target.value)}
                    style={{fontFamily:'var(--mono)',fontWeight:700,letterSpacing:'.06em'}}/>
                  <button className="btn" style={{flexShrink:0}} onClick={()=>set('password',genTempPassword())} title="Сгенерировать заново">
                    <Icon d={IC.key} size={15}/>
                  </button>
                </div>
                <Err k="password"/>
                <div className="muted" style={{fontSize:11.5,marginTop:4}}>Минимум 8 символов, заглавная и строчная буквы, цифра, спецсимвол</div>
              </Field>

              <div>
                <div className="muted" style={{fontSize:12,fontWeight:600,marginBottom:10}}>Роли в системе *</div>
                <div style={{display:'flex',flexDirection:'column',gap:8}}>
                  {cats.roles.map(r=>{
                    const on=form.roleIds.includes(r.id);
                    return (
                      <button key={r.id} onClick={()=>toggleRole(r.id)}
                        style={{display:'flex',alignItems:'center',gap:12,padding:'11px 14px',borderRadius:11,textAlign:'left',cursor:'pointer',
                          border:`1px solid ${on?'var(--accent)':'var(--border)'}`,background:on?'var(--accent-softer)':'var(--surface)',transition:'.14s'}}>
                        <div style={{flex:1,minWidth:0}}>
                          <div style={{fontWeight:600,fontSize:13.5}}>{r.name}</div>
                          {r.description&&<div className="muted" style={{fontSize:12,marginTop:2}}>{r.description}</div>}
                        </div>
                        <div style={{width:22,height:22,borderRadius:50,flexShrink:0,border:`2px solid ${on?'var(--accent)':'var(--border)'}`,
                          background:on?'var(--accent)':'transparent',display:'flex',alignItems:'center',justifyContent:'center',transition:'.14s'}}>
                          {on&&<Icon d={IC.check} size={12} stroke={3} style={{color:'#fff'}}/>}
                        </div>
                      </button>
                    );
                  })}
                </div>
                <Err k="roles"/>
              </div>
            </div>
          )}

          {cats&&!created&&step===2&&(
            <div style={{display:'flex',flexDirection:'column',gap:18}}>
              <div style={{fontWeight:700,fontSize:15,marginBottom:-4}}>Профиль</div>

              <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
                <Field label="Имя *">
                  <input className="input" value={form.firstName} onChange={e=>set('firstName',e.target.value)} placeholder="Иван"/>
                  <Err k="firstName"/>
                </Field>
                <Field label="Фамилия *">
                  <input className="input" value={form.lastName} onChange={e=>set('lastName',e.target.value)} placeholder="Иванов"/>
                  <Err k="lastName"/>
                </Field>
              </div>

              <Field label="Должность">
                <input className="input" value={form.position} onChange={e=>set('position',e.target.value)} placeholder="Frontend-разработчик"/>
              </Field>

              <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:12}}>
                <Field label="Отдел">
                  <select className="input" value={form.departmentId} onChange={e=>set('departmentId',e.target.value)} style={{cursor:'pointer'}}>
                    <option value="">— Не указан —</option>
                    {cats.departments.map(d=><option key={d.id} value={d.id}>{d.name}</option>)}
                  </select>
                </Field>
                <Field label="Грейд">
                  <select className="input" value={form.gradeId} onChange={e=>set('gradeId',e.target.value)} style={{cursor:'pointer'}}>
                    <option value="">— Не указан —</option>
                    {cats.grades.map(g=><option key={g.id} value={g.id}>{g.name}</option>)}
                  </select>
                </Field>
              </div>

              <Field label="Руководитель">
                <select className="input" value={form.leadId} onChange={e=>set('leadId',e.target.value)} style={{cursor:'pointer'}}>
                  <option value="">— Нет руководителя —</option>
                  {team.map(m=><option key={m.id} value={m.id}>{m.name}{m.position&&m.position!=='—'?' · '+m.position:''}</option>)}
                </select>
              </Field>

              <div className="muted" style={{fontSize:12.5,lineHeight:1.5,padding:'10px 14px',background:'var(--surface-2)',borderRadius:10}}>
                Назначить на проекты можно после создания — через карточку проекта или карточку сотрудника.
              </div>
            </div>
          )}
        </div>

        {/* footer */}
        <div style={{padding:'16px 26px',borderTop:'1px solid var(--border)',display:'flex',gap:10,alignItems:'center',flexShrink:0}}>
          {created?(
            <button className="btn primary" style={{flex:1}} onClick={onSaved}><Icon d={IC.check} size={15}/>Готово</button>
          ):step===1?(
            <>
              <button className="btn" onClick={onClose}>Отмена</button>
              <div style={{flex:1}}/>
              <button className="btn primary" onClick={()=>{ if(validate1()) setStep(2); }} disabled={!cats}>Далее · Профиль<Icon d={IC.chevR} size={16}/></button>
            </>
          ):(
            <>
              <button className="btn ghost" onClick={()=>setStep(1)} disabled={saving}><Icon d={IC.chevL} size={16}/>Назад</button>
              <div style={{flex:1}}/>
              <button className="btn primary" onClick={save} disabled={saving}><Icon d={IC.check} size={15}/>{saving?'Создание…':'Создать сотрудника'}</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { ManagerScreen, fmtDate, fmtDateY });
