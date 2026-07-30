/* ============ SCREEN: Профиль сотрудника ============ */
const PROJ_STATUS_CLS = { ACTIVE:'green', COMPLETED:'accent', ON_HOLD:'', PLANNED:'', ARCHIVED:'' };
const ACTIVE_ASSIGNMENT_CODES = ['ACTIVE','EXTENDED'];

function primaryRoleName(){
  const roles = (API.session()||{}).roles || [];
  for(const r of ['Администратор','Менеджер','Тимлид','HR']) if(roles.includes(r)) return r;
  return 'Сотрудник';
}

function ProfileScreen({ userId, onNav, showToast }){
  const [emp,setEmp]=useState(null);
  const [summary,setSummary]=useState(null);
  const [error,setError]=useState(null);

  useEffect(()=>{
    let alive=true;
    setEmp(null); setSummary(null); setError(null);
    Promise.all([
      API.profile.getEmployee(userId),
      API.timesheet.getSummary(userId),
    ]).then(([e,s])=>{ if(alive){ setEmp(e); setSummary(s); } })
      .catch(err=>{ if(alive) setError(err.detail||'Не удалось загрузить профиль'); });
    return ()=>{ alive=false; };
  },[userId]);

  if(error) return <ErrorCard text={error}/>;
  if(!emp || !summary) return <ProfileSkeleton/>;

  const name = `${emp.first_name} ${emp.last_name}`;
  const logged = Number(summary.logged_hours);
  const norm = Number(summary.norm_hours);
  const loadPct = Math.round(summary.utilization_pct);
  const activeAssignments = emp.assignments.filter(a=>ACTIVE_ASSIGNMENT_CODES.includes(a.assignment_status.code));
  const weekly = summary.weekly_dynamics.map(w=>Number(w.hours));
  const projectColor = (projName)=>{
    const a = emp.assignments.find(x=>x.project.name===projName);
    return (a && a.project.color) || 'var(--text-3)';
  };

  return (
    <div className="fade-in" style={{display:'flex', flexDirection:'column', gap:18}}>
      <PageHead title="Мой профиль" subtitle="Личные данные, загрузка и активность за период"
        />

      {/* identity card */}
      <div className="card" style={{padding:24, display:'flex', gap:22, alignItems:'center', flexWrap:'wrap'}}>
        <Avatar id={emp.id} name={name} size={84} imageUrl={emp.image_url}/>
        <div style={{flex:1, minWidth:240}}>
          <div style={{display:'flex', alignItems:'center', gap:10, flexWrap:'wrap'}}>
            <h2 style={{fontSize:22}}>{name}</h2>
            {emp.grade && <span className="badge accent">{emp.grade.name}</span>}
            <span className="badge">{primaryRoleName()}</span>
          </div>
          <div className="muted" style={{fontSize:14, marginTop:4}}>{[emp.position, emp.department?.name].filter(Boolean).join(' · ')||'—'}</div>
          <div style={{display:'flex', gap:20, marginTop:14, flexWrap:'wrap', color:'var(--text-2)', fontSize:13}}>
            <span style={{display:'inline-flex', alignItems:'center', gap:7}}><Icon d={IC.mail} size={15}/>{emp.user.email}</span>
            <span style={{display:'inline-flex', alignItems:'center', gap:7}}><Icon d={IC.briefcase} size={15}/>В компании с {new Date(emp.user.register_date).getFullYear()} г.</span>
            {emp.birthday && <span style={{display:'inline-flex', alignItems:'center', gap:7}}><Icon d={IC.calendar} size={15}/>{new Date(emp.birthday).toLocaleDateString('ru',{day:'numeric',month:'long'})}</span>}
            {emp.phone && <span style={{display:'inline-flex', alignItems:'center', gap:7}}><Icon d={IC.mail} size={15}/>{emp.phone}</span>}
            {emp.address && <span style={{display:'inline-flex', alignItems:'center', gap:7}}><Icon d={IC.flag} size={15}/>{emp.address}</span>}
            <span style={{display:'inline-flex', alignItems:'center', gap:7}}><Icon d={IC.folder} size={15}/>{activeAssignments.length} активных проекта</span>
          </div>
        </div>
        <div style={{display:'flex', alignItems:'center', gap:8, paddingLeft:18, borderLeft:'1px solid var(--border)'}}>
          <Donut value={loadPct/100} label={loadPct+'%'} sub="загрузка" size={108}/>
        </div>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'repeat(4, 1fr)', gap:14}}>
        <StatCard label="Списано за период" value={logged+' ч'} sub={summary.period_name+' · норма '+norm+' ч'} icon="clock" accent/>
        <StatCard label="Утилизация" value={summary.prev_month_utilization_pct!=null?Math.round(summary.prev_month_utilization_pct)+'%':'—'}
          trend={summary.utilization_delta!=null?Math.round(summary.utilization_delta):undefined} sub="прошлый месяц, к позапрошлому" icon="trend"/>
        <StatCard label="Активных проектов" value={summary.active_projects_count} sub={'из '+summary.total_projects_count+' в портфеле'} icon="folder"/>
        <StatCard label="Остаток до нормы" value={Number(summary.remaining_hours)+' ч'} sub="до конца месяца" icon="target"/>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'1.4fr 1fr', gap:18}}>
        {/* projects */}
        <div className="card" style={{padding:20}}>
          <SectionTitle title="Мои проекты" right={<button className="btn ghost sm" onClick={()=>onNav('timesheet')}>Открыть таймшит<Icon d={IC.chevR} size={14}/></button>}/>
          <div style={{display:'flex', flexDirection:'column', gap:10, marginTop:14}}>
            {activeAssignments.length===0 && <div className="muted" style={{fontSize:13, padding:'8px 2px'}}>Нет активных назначений на проекты</div>}
            {activeAssignments.map(a=>{
              const p=a.project;
              const st=PROJ_STATUS_CLS[p.project_status.code] ?? '';
              return (
                <div key={a.id} style={{display:'flex', alignItems:'center', gap:14, padding:'12px 14px', border:'1px solid var(--border)', borderRadius:10, background:'var(--surface-2)'}}>
                  <span style={{width:38, height:38, borderRadius:9, background:p.color||'var(--accent)', color:'#fff', display:'flex', alignItems:'center', justifyContent:'center', fontWeight:700, fontSize:12, flex:'none'}}>{(p.code||p.name).slice(0,2).toUpperCase()}</span>
                  <div style={{flex:1, minWidth:0}}>
                    <div style={{fontWeight:600, fontSize:14}}>{p.name}</div>
                    <div style={{display:'flex', alignItems:'center', gap:8, marginTop:3}}>
                      <span className="muted" style={{fontSize:12}}>{[p.client, p.code].filter(Boolean).join(' · ')}</span>
                      <span style={{fontSize:11.5, fontWeight:600, color:'var(--text-2)', background:'var(--surface-3)', padding:'1px 7px', borderRadius:4}}>{a.project_role.name}</span>
                    </div>
                  </div>
                  <span className={'badge '+st}><span className="dot"/>{p.project_status.name}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* skills + activity */}
        <div style={{display:'flex', flexDirection:'column', gap:18}}>
          <div className="card" style={{padding:20}}>
            <SectionTitle title="Динамика часов" right={<span className="muted" style={{fontSize:12}}>8 недель</span>}/>
            <div style={{marginTop:14, display:'flex', alignItems:'flex-end', justifyContent:'space-between'}}>
              <div>
                <div className="tnum" style={{fontSize:28, fontWeight:800}}>{Number(summary.avg_weekly_hours)} ч</div>
                <div className="muted" style={{fontSize:12}}>средняя неделя</div>
              </div>
              {weekly.length>1
                ? <Sparkline data={weekly} w={170} h={50}/>
                : <span className="muted" style={{fontSize:12}}>Недостаточно данных</span>}
            </div>
          </div>
          <div className="card" style={{padding:20}}>
            <SectionTitle title="Навыки"/>
            <div style={{display:'flex', flexWrap:'wrap', gap:8, marginTop:14}}>
              {emp.skills.length===0 && <span className="muted" style={{fontSize:13}}>Навыки не указаны</span>}
              {emp.skills.map(s=><span key={s.id} className="badge" style={{height:28, fontSize:12.5}}>{s.name}</span>)}
            </div>
          </div>
        </div>
      </div>

      {/* recent entries */}
      <div className="card" style={{padding:'20px 20px 8px'}}>
        <SectionTitle title="Последние записи" right={<button className="btn ghost sm" onClick={()=>onNav('timesheet')}>Все записи<Icon d={IC.chevR} size={14}/></button>}/>
        <table className="tbl" style={{marginTop:10}}>
          <thead><tr><th>Дата</th><th>Проект</th><th>Задача</th><th style={{textAlign:'right'}}>Часы</th></tr></thead>
          <tbody>
            {summary.recent_entries.length===0 && (
              <tr><td colSpan={4} className="muted" style={{textAlign:'center'}}>За период ещё нет записей</td></tr>
            )}
            {summary.recent_entries.map((r,i)=>(
              <tr key={i}>
                <td className="muted">{new Date(r.date_from).toLocaleDateString('ru',{day:'numeric',month:'short'})}</td>
                <td><span style={{display:'inline-flex', alignItems:'center', gap:8}}><span style={{width:8,height:8,borderRadius:3,background:projectColor(r.project_name)}}/>{r.project_name||'—'}</span></td>
                <td className="muted">{r.task_name||'—'}</td>
                <td className="mono" style={{textAlign:'right', fontWeight:600}}>{Number(r.spend_time).toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ErrorCard({ text }){
  return (
    <div className="card fade-in" style={{padding:24, display:'flex', gap:12, alignItems:'center'}}>
      <span style={{color:'var(--red)', display:'flex'}}><Icon d={IC.shield} size={20}/></span>
      <div style={{fontWeight:600}}>{text}</div>
    </div>
  );
}

function ProfileSkeleton(){
  return (
    <div className="fade-in" style={{display:'flex', flexDirection:'column', gap:18}}>
      <div><div className="skel" style={{width:180, height:26, marginBottom:8}}/><div className="skel" style={{width:320, height:14}}/></div>
      <div className="card" style={{padding:24, display:'flex', gap:22, alignItems:'center'}}>
        <div className="skel" style={{width:84, height:84, borderRadius:'50%'}}/>
        <div style={{flex:1}}>
          <div className="skel" style={{width:240, height:22, marginBottom:10}}/>
          <div className="skel" style={{width:340, height:14}}/>
        </div>
        <div className="skel" style={{width:108, height:108, borderRadius:'50%'}}/>
      </div>
      <div style={{display:'grid', gridTemplateColumns:'repeat(4, 1fr)', gap:14}}>
        {[0,1,2,3].map(i=><div key={i} className="card" style={{padding:18}}><div className="skel" style={{width:'60%', height:13, marginBottom:12}}/><div className="skel" style={{width:'40%', height:26}}/></div>)}
      </div>
      <div style={{display:'grid', gridTemplateColumns:'1.4fr 1fr', gap:18}}>
        <div className="card" style={{padding:20}}>{[0,1,2].map(i=><div key={i} className="skel" style={{height:62, marginBottom:10, borderRadius:10}}/>)}</div>
        <div className="card" style={{padding:20}}><div className="skel" style={{height:140}}/></div>
      </div>
    </div>
  );
}

function PageHead({ title, subtitle, actions }){
  return (
    <div style={{display:'flex', alignItems:'flex-end', justifyContent:'space-between', gap:16, flexWrap:'wrap'}}>
      <div>
        <h1 style={{fontSize:23}}>{title}</h1>
        {subtitle && <div className="muted" style={{fontSize:13.5, marginTop:3}}>{subtitle}</div>}
      </div>
      {actions && <div style={{display:'flex', gap:8}}>{actions}</div>}
    </div>
  );
}
function SectionTitle({ title, right }){
  return (
    <div style={{display:'flex', alignItems:'center', justifyContent:'space-between'}}>
      <h3 style={{fontSize:15.5}}>{title}</h3>
      {right}
    </div>
  );
}

Object.assign(window, { ProfileScreen, PageHead, SectionTitle, ErrorCard, primaryRoleName });
