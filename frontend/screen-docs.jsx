/* ============ SCREEN: Документооборот — живые данные (document_service) ============ */

// Статусы документа (русские значения enum бэка)
const DOC_ST_UI = {
  'Черновик':      { cls:''      },
  'На подписании': { cls:'amber' },
  'Подписан':      { cls:'green' },
  'Отклонён':      { cls:'red'   },
};
const STEP_ROLE_RU = { SIGNER:'Подписант', APPROVER:'Согласующий' };

function fmtBytes(n){
  if(n>1024*1024) return (n/1024/1024).toFixed(1).replace('.',',')+' МБ';
  if(n>1024) return Math.round(n/1024)+' КБ';
  return n+' Б';
}

// Текущий шаг маршрута: первый «Ожидает» по порядку, пока документ на подписании
function docCurrentStep(d){
  if(d.status!=='На подписании') return null;
  return [...d.route].sort((a,b)=>a.step_order-b.step_order).find(s=>s.status==='Ожидает')||null;
}

function DocsScreen({ showToast }){
  const [data,setData]=useState(null); // {docs, types, empMap, projects}
  const [error,setError]=useState(null);
  const [filter,setFilter]=useState('all');
  const [q,setQ]=useState('');
  const [open,setOpen]=useState(null);      // id документа
  const [wizard,setWizard]=useState(false);
  const [templatesOpen,setTemplatesOpen]=useState(false);

  const sess=API.session()||{};
  const myId=sess.userId;
  const canManageTpl=(sess.permissions||[]).includes('document:manage_templates');

  const load=()=>Promise.all([
    API.document.getAll('all'),
    API.document.getTypes(),
    API.management.getEmployees().catch(()=>[]),
    API.management.getProjects().catch(()=>[]),
  ]).then(([docs, types, emps, projects])=>{
    const empMap={};
    emps.forEach(e=>{ empMap[e.id]=`${e.first_name} ${e.last_name}`; });
    setData({ docs, types, empMap, projects });
  });
  useEffect(()=>{ load().catch(err=>setError(err.detail||'Не удалось загрузить документы')); },[]);
  const reload=()=>load().catch(err=>showToast(err.detail||'Не удалось обновить данные'));

  if(error) return <ErrorCard text={error}/>;
  if(!data) return (
    <div className="fade-in" style={{display:'flex',flexDirection:'column',gap:18}}>
      <div><div className="skel" style={{width:220,height:26,marginBottom:8}}/><div className="skel" style={{width:320,height:14}}/></div>
      <div style={{display:'grid',gridTemplateColumns:'repeat(4,1fr)',gap:14}}>{[0,1,2,3].map(i=><div key={i} className="skel" style={{height:86}}/>)}</div>
      <div className="card" style={{padding:18}}>{[0,1,2].map(i=><div key={i} className="skel" style={{height:44,marginBottom:10}}/>)}</div>
    </div>
  );

  const { docs, types, empMap, projects } = data;
  const projMap={}; projects.forEach(p=>{ projMap[p.id]=p; });
  const empName=(id)=>empMap[id]||(id===myId?'Вы':'Участник');

  const counts={
    pending:docs.filter(d=>d.status==='На подписании').length,
    mine:docs.filter(d=>d.author_id===myId).length,
    signed:docs.filter(d=>d.status==='Подписан').length,
    needMe:docs.filter(d=>{ const s=docCurrentStep(d); return s&&s.employee_id===myId; }).length,
  };
  const tabs=[
    {id:'all',label:'Все документы',n:docs.length},
    {id:'pending',label:'На подписании',n:counts.pending},
    {id:'mine',label:'Мои документы',n:counts.mine},
    {id:'signed',label:'Подписанные',n:counts.signed},
  ];

  let list=docs;
  if(filter==='pending') list=docs.filter(d=>d.status==='На подписании');
  else if(filter==='mine') list=docs.filter(d=>d.author_id===myId);
  else if(filter==='signed') list=docs.filter(d=>d.status==='Подписан');
  if(q.trim()) list=list.filter(d=>d.title.toLowerCase().includes(q.toLowerCase()));

  const openDoc=open&&docs.find(d=>d.id===open);

  return (
    <div className="fade-in" style={{display:'flex', flexDirection:'column', gap:18}}>
      <PageHead title="Документооборот" subtitle="Договоры, акты, заявления и маршруты подписания"
        actions={<>
          <button className="btn sm" onClick={()=>setTemplatesOpen(true)}><Icon d={IC.inbox} size={15}/>Шаблоны</button>
          <button className="btn sm primary" onClick={()=>setWizard(true)}><Icon d={IC.plus} size={15}/>Создать документ</button>
        </>}/>

      <div style={{display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:14}}>
        <StatCard label="На подписании" value={counts.pending} sub="активных маршрутов" icon="clock" accent/>
        <StatCard label="Подписано" value={counts.signed} sub="завершено" icon="signature"/>
        <StatCard label="Мои документы" value={counts.mine} sub="создано вами" icon="fileText"/>
        <StatCard label="Требуют вашей подписи" value={counts.needMe} sub="ваш шаг маршрута" icon="pen"/>
      </div>

      <div className="card" style={{padding:'16px 20px 8px'}}>
        <div style={{display:'flex', alignItems:'center', gap:12, flexWrap:'wrap', marginBottom:8}}>
          <div className="seg">
            {tabs.map(t=>(
              <button key={t.id} className={filter===t.id?'on':''} onClick={()=>setFilter(t.id)} style={{display:'inline-flex',alignItems:'center',gap:7}}>
                {t.label}<span className="badge" style={{height:18,padding:'0 6px',fontSize:11,background:filter===t.id?'var(--accent-soft)':'var(--surface-3)',color:filter===t.id?'var(--accent-strong)':'var(--text-3)'}}>{t.n}</span>
              </button>
            ))}
          </div>
          <div style={{flex:1}}/>
          <div style={{position:'relative', width:240}}>
            <span style={{position:'absolute', left:11, top:9, color:'var(--text-3)'}}><Icon d={IC.search} size={16}/></span>
            <input className="input" value={q} onChange={e=>setQ(e.target.value)} style={{height:34, paddingLeft:34, fontSize:13}} placeholder="Поиск документа…"/>
          </div>
        </div>

        <table className="tbl" style={{marginTop:4}}>
          <thead><tr><th>Документ</th><th>Тип</th><th>Автор</th><th>Проект</th><th>Дата</th><th>Маршрут</th><th>Статус</th></tr></thead>
          <tbody>
            {list.length===0&&<tr><td colSpan={7} style={{textAlign:'center',padding:'24px 0',color:'var(--text-3)'}}>Документов нет</td></tr>}
            {list.map(d=>{
              const tp=d.document_type;
              const st=DOC_ST_UI[d.status]||{cls:''};
              const p=d.project_id&&projMap[d.project_id];
              return (
                <tr key={d.id} style={{cursor:'pointer'}} onClick={()=>setOpen(d.id)}>
                  <td>
                    <div style={{display:'flex', alignItems:'center', gap:11}}>
                      <span style={{width:32,height:32,borderRadius:8,background:tp.color,display:'flex',alignItems:'center',justifyContent:'center',color:'#fff',flex:'none',opacity:.92}}><Icon d={IC.fileText} size={16}/></span>
                      <div style={{minWidth:0}}><div style={{fontWeight:600}}>{d.title}</div><div className="muted" style={{fontSize:11.5}}>{fmtBytes(d.file_size)}</div></div>
                    </div>
                  </td>
                  <td><span className="badge" style={{height:22,fontSize:11.5}}><span style={{width:7,height:7,borderRadius:2,background:tp.color}}/>{tp.name}</span></td>
                  <td><span style={{display:'inline-flex',alignItems:'center',gap:7}}><Avatar id={d.author_id} name={empName(d.author_id)} size={24}/>{empName(d.author_id).split(' ')[0]}</span></td>
                  <td className="muted">{p?(p.code||p.name):'—'}</td>
                  <td className="muted mono" style={{fontSize:12.5}}>{fmtDate(d.created_at)}</td>
                  <td><RouteMini route={d.route} empName={empName}/></td>
                  <td><span className={'badge '+st.cls}><span className="dot"/>{d.status}</span></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {openDoc && <DocDrawer doc={openDoc} empName={empName} projMap={projMap} myId={myId}
        onClose={()=>setOpen(null)} onChanged={reload} showToast={showToast}/>}
      {wizard && <CreateDocWizard types={types} teamList={Object.entries(empMap).map(([id,name])=>({id,name}))}
        projects={projects} myId={myId}
        onClose={()=>setWizard(false)}
        onSaved={()=>{ setWizard(false); reload(); showToast('Документ создан и отправлен на подписание'); }} showToast={showToast}/>}
      {templatesOpen && <TemplatesModal types={types} canManage={canManageTpl} onClose={()=>setTemplatesOpen(false)} showToast={showToast}/>}
    </div>
  );
}

function RouteMini({ route, empName }){
  const steps=[...route].sort((a,b)=>a.step_order-b.step_order);
  const curIdx=steps.findIndex(s=>s.status==='Ожидает');
  return (
    <div style={{display:'flex', alignItems:'center'}}>
      {steps.map((s,i)=>{
        const cur=i===curIdx;
        const c = s.status==='Подписано'?'var(--green)':s.status==='Отклонено'?'var(--red)':cur?'var(--accent)':'var(--border-strong)';
        const name=empName(s.employee_id);
        return (
          <span key={s.id} title={name+' · '+s.status} style={{width:22,height:22,borderRadius:50,marginLeft:i?-6:0,border:'2px solid var(--surface)',display:'flex',alignItems:'center',justifyContent:'center',
            background:c, color:'#fff', fontSize:9, fontWeight:700, zIndex:steps.length-i}}>
            {s.status==='Подписано'?<Icon d={IC.check} size={11} stroke={3}/>:s.status==='Отклонено'?<Icon d={IC.x} size={10} stroke={3}/>:initials(name).slice(0,1)}
          </span>
        );
      })}
    </div>
  );
}

function DocDrawer({ doc, empName, projMap, myId, onClose, onChanged, showToast }){
  const tp=doc.document_type;
  const st=DOC_ST_UI[doc.status]||{cls:''};
  const p=doc.project_id&&projMap[doc.project_id];
  const steps=[...doc.route].sort((a,b)=>a.step_order-b.step_order);
  const cur=docCurrentStep(doc);
  const myTurn=cur&&cur.employee_id===myId;
  const [busy,setBusy]=useState(false);
  const [rejectOpen,setRejectOpen]=useState(false);
  const [rejectComment,setRejectComment]=useState('');

  const act=async(fn, msg)=>{
    setBusy(true);
    try{ await fn(); showToast(msg); onChanged(); onClose(); }
    catch(err){ showToast(err.detail||'Не удалось выполнить действие'); }
    finally{ setBusy(false); }
  };
  const doReject=()=>{
    if(!rejectComment.trim()){ showToast('Укажите причину отклонения'); return; }
    act(()=>API.document.reject(doc.id, rejectComment.trim()), 'Документ отклонён');
  };

  return (
    <div style={{position:'fixed', inset:0, zIndex:120, display:'flex', justifyContent:'flex-end'}}>
      <div onClick={onClose} style={{position:'absolute', inset:0, background:'oklch(0.3 0.02 255 / 0.32)', backdropFilter:'blur(1px)'}}/>
      <div className="fade-in" style={{position:'relative', width:460, maxWidth:'92vw', height:'100%', background:'var(--surface)', borderLeft:'1px solid var(--border)', boxShadow:'var(--shadow-lg)', overflowY:'auto', padding:26}}>
        <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start', gap:12}}>
          <div style={{display:'flex', gap:12, alignItems:'flex-start'}}>
            <span style={{width:44,height:44,borderRadius:11,background:tp.color,color:'#fff',display:'flex',alignItems:'center',justifyContent:'center',flex:'none'}}><Icon d={IC.fileText} size={20}/></span>
            <div><h2 style={{fontSize:17, lineHeight:1.25}}>{doc.title}</h2><div className="muted" style={{fontSize:12.5, marginTop:2}}>{tp.name} · {fmtBytes(doc.file_size)}</div></div>
          </div>
          <button className="btn ghost sm icon" onClick={onClose}><Icon d={IC.x} size={17}/></button>
        </div>
        <div style={{display:'flex', gap:8, marginTop:14, flexWrap:'wrap'}}>
          <span className={'badge '+st.cls}><span className="dot"/>{doc.status}</span>
          {p && <span className="badge"><span style={{width:7,height:7,borderRadius:2,background:p.color||'var(--accent)'}}/>{p.code||p.name}</span>}
          <span className="badge"><Icon d={IC.calendar} size={13}/>{fmtDateY(doc.created_at)}</span>
          <span className="badge"><Icon d={IC.user} size={13}/>{empName(doc.author_id)}</span>
        </div>

        {doc.comment&&(
          <div style={{marginTop:16,padding:'12px 14px',background:'var(--surface-2)',borderRadius:10,border:'1px solid var(--border)'}}>
            <div className="muted" style={{fontSize:11.5,fontWeight:600,marginBottom:5}}>Комментарий автора</div>
            <div style={{fontSize:13.5,lineHeight:1.5}}>{doc.comment}</div>
          </div>
        )}

        <div style={{marginTop:22}}>
          <SectionTitle title="Маршрут подписания"/>
          <div style={{marginTop:14, position:'relative'}}>
            {steps.map((s,i)=>{
              const last=i===steps.length-1;
              const isCur=cur&&s.id===cur.id;
              const c = s.status==='Подписано'?'var(--green)':s.status==='Отклонено'?'var(--red)':isCur?'var(--accent)':'var(--border-strong)';
              const lbl = s.status==='Подписано'?'Подписано':s.status==='Отклонено'?'Отклонено':isCur?'Ожидает действия':'В очереди';
              return (
                <div key={s.id} style={{display:'flex', gap:13, paddingBottom:last?0:18, position:'relative'}}>
                  {!last && <span style={{position:'absolute', left:15, top:32, bottom:0, width:2, background:'var(--border)'}}/>}
                  <span style={{width:32,height:32,borderRadius:50,background:c,color:'#fff',display:'flex',alignItems:'center',justifyContent:'center',flex:'none',zIndex:1, fontSize:11, fontWeight:700}}>
                    {s.status==='Подписано'?<Icon d={IC.check} size={15} stroke={3}/>:s.status==='Отклонено'?<Icon d={IC.x} size={14} stroke={3}/>:s.step_order}
                  </span>
                  <div style={{paddingTop:1}}>
                    <div style={{fontWeight:600, fontSize:13.5}}>
                      {empName(s.employee_id)} {s.employee_id===myId && <span className="muted" style={{fontWeight:500}}>· вы</span>}
                    </div>
                    <div className="muted" style={{fontSize:11.5}}>{STEP_ROLE_RU[s.role]||s.role}</div>
                    <div style={{fontSize:12, color:c, fontWeight:600}}>{lbl}{s.acted_at?' · '+fmtDate(s.acted_at):''}</div>
                    {s.status==='Отклонено'&&s.comment&&<div style={{fontSize:12.5,marginTop:3,color:'var(--text-2)'}}>Причина: {s.comment}</div>}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {myTurn&&!rejectOpen&&(
          <div style={{display:'flex', gap:8, marginTop:24}}>
            <button className="btn" style={{flex:1, color:'var(--red)'}} disabled={busy} onClick={()=>setRejectOpen(true)}><Icon d={IC.x} size={15}/>Отклонить</button>
            <button className="btn primary" style={{flex:1}} disabled={busy}
              onClick={()=>act(()=>API.document.sign(doc.id), 'Документ подписан')}><Icon d={IC.check} size={15}/>Подписать</button>
          </div>
        )}
        {myTurn&&rejectOpen&&(
          <div style={{marginTop:24,padding:'14px 16px',background:'var(--surface-2)',borderRadius:10,border:'1px solid var(--border)'}}>
            <div className="muted" style={{fontSize:12,fontWeight:600,marginBottom:8}}>Причина отклонения *</div>
            <textarea className="input" value={rejectComment} onChange={e=>setRejectComment(e.target.value)}
              placeholder="Маршрут будет прерван, автор увидит причину" autoFocus
              style={{height:70,resize:'none',padding:'10px 12px',lineHeight:1.5}}/>
            <div style={{display:'flex',gap:8,marginTop:10}}>
              <button className="btn sm" style={{flex:1}} disabled={busy} onClick={()=>setRejectOpen(false)}>Отмена</button>
              <button className="btn sm primary" style={{flex:1,background:'var(--red)',borderColor:'var(--red)'}} disabled={busy} onClick={doReject}>Отклонить</button>
            </div>
          </div>
        )}
        <button className="btn" style={{width:'100%', marginTop:myTurn?10:24}} disabled={busy}
          onClick={()=>API.document.downloadFile(doc.id, doc.title).catch(err=>showToast(err.detail||'Не удалось скачать файл'))}>
          <Icon d={IC.download} size={15}/>Скачать файл
        </button>
      </div>
    </div>
  );
}

/* ============ CreateDocWizard ============ */
function CreateDocWizard({ types, teamList, projects, myId, onClose, onSaved, showToast }){
  const [step,setStep]=useState(1);
  const [typeId,setTypeId]=useState('');
  const [title,setTitle]=useState('');
  const [projectId,setProjectId]=useState('');
  const [comment,setComment]=useState('');
  const [file,setFile]=useState(null);
  const [dragging,setDragging]=useState(false);
  const [route,setRoute]=useState([]); // [{employee_id, role}]
  const [addingEmp,setAddingEmp]=useState(false);
  const [saving,setSaving]=useState(false);
  const [myLead,setMyLead]=useState(undefined); // undefined=грузим, null=нет руководителя
  const fileRef=useRef(null);

  const canPickTeam=teamList.length>0; // у сотрудника нет employee:list — маршрут строится по его руководителю
  useEffect(()=>{
    if(canPickTeam) return;
    API.profile.getEmployee(myId)
      .then(p=>{ setMyLead(p.lead_id||null); if(p.lead_id) setRoute([{employee_id:p.lead_id, role:'SIGNER'}]); })
      .catch(()=>setMyLead(null));
  },[]);

  const selType=types.find(t=>t.id===typeId);

  const goNext=()=>{
    if(step===1&&!typeId) return;
    if(step===2&&(!title.trim()||!file)){ if(!file) showToast('Прикрепите файл документа'); return; }
    setStep(s=>s+1);
  };

  const handleFile=(f)=>{ if(f) setFile(f); };
  const onDrop=(e)=>{ e.preventDefault(); setDragging(false); const f=e.dataTransfer.files[0]; if(f) handleFile(f); };

  const addRouteStep=(emp)=>{ setRoute(r=>[...r,{employee_id:emp.id, role:'SIGNER'}]); setAddingEmp(false); };
  const removeRouteStep=(idx)=>setRoute(r=>r.filter((_,i)=>i!==idx));
  const setStepRole=(idx,role)=>setRoute(r=>r.map((s,i)=>i===idx?{...s,role}:s));
  const moveStep=(idx,dir)=>{
    setRoute(r=>{ const a=[...r]; if(idx+dir<0||idx+dir>=a.length) return a; [a[idx],a[idx+dir]]=[a[idx+dir],a[idx]]; return a; });
  };

  const submit=async()=>{
    setSaving(true);
    try{
      const fd=new FormData();
      fd.append('file', file);
      fd.append('title', title.trim());
      fd.append('type_id', typeId);
      if(projectId) fd.append('project_id', projectId);
      if(comment.trim()) fd.append('comment', comment.trim());
      fd.append('route', JSON.stringify(route.map((s,i)=>({ employee_id:s.employee_id, role:s.role, step_order:i+1 }))));
      await API.document.create(fd);
      onSaved();
    }catch(err){ showToast(err.detail||'Не удалось создать документ'); }
    finally{ setSaving(false); }
  };

  const nameOf=(id)=>(teamList.find(t=>t.id===id)||{}).name||'Ваш руководитель';
  const STEP_LABELS=['Тип документа','Детали','Маршрут'];

  return (
    <div style={{position:'fixed',inset:0,zIndex:200,display:'flex',alignItems:'center',justifyContent:'center',background:'oklch(0.25 0.02 255 / 0.5)',backdropFilter:'blur(3px)'}}
      onClick={e=>{ if(e.target===e.currentTarget) onClose(); }}>
      <div className="card fade-in" style={{width:600,maxWidth:'95vw',maxHeight:'90vh',display:'flex',flexDirection:'column',padding:0,overflow:'hidden',boxShadow:'var(--shadow-lg)'}}>

        {/* header */}
        <div style={{padding:'20px 24px 0',borderBottom:'1px solid var(--border)'}}>
          <div style={{display:'flex',alignItems:'center',marginBottom:16}}>
            <div style={{fontWeight:800,fontSize:17,flex:1}}>Новый документ</div>
            <button className="btn ghost sm icon" onClick={onClose}><Icon d={IC.x} size={16}/></button>
          </div>
          <div style={{display:'flex',gap:0,marginBottom:0}}>
            {STEP_LABELS.map((lbl,i)=>{
              const n=i+1; const done=step>n; const active=step===n;
              return (
                <div key={n} style={{flex:1,display:'flex',flexDirection:'column',alignItems:'center',paddingBottom:12,position:'relative',cursor:done?'pointer':'default'}}
                  onClick={()=>done&&setStep(n)}>
                  {i>0&&<div style={{position:'absolute',top:11,right:'50%',left:'-50%',height:2,background:done||active?'var(--accent)':'var(--border)'}}/>}
                  <div style={{width:24,height:24,borderRadius:'50%',background:done||active?'var(--accent)':'var(--surface-3)',
                    border:'2px solid '+(done||active?'var(--accent)':'var(--border)'),
                    color:done||active?'#fff':'var(--text-3)',display:'flex',alignItems:'center',justifyContent:'center',
                    fontSize:11,fontWeight:700,zIndex:1,position:'relative'}}>
                    {done?<Icon d={IC.check} size={12} stroke={3}/>:n}
                  </div>
                  <div style={{fontSize:11,fontWeight:600,color:active?'var(--accent-strong)':done?'var(--text-2)':'var(--text-3)',marginTop:4}}>{lbl}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* body */}
        <div style={{flex:1,overflowY:'auto',padding:'20px 24px'}}>

          {/* STEP 1: тип из каталога */}
          {step===1&&(
            <div>
              <p className="muted" style={{fontSize:13,marginBottom:16}}>Выберите тип документа из справочника.</p>
              <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:10}}>
                {types.map(t=>(
                  <button key={t.id} onClick={()=>setTypeId(t.id)}
                    style={{display:'flex',alignItems:'flex-start',gap:14,padding:'14px 16px',border:'2px solid '+(typeId===t.id?'var(--accent)':'var(--border)'),
                      borderRadius:12,cursor:'pointer',textAlign:'left',background:typeId===t.id?'var(--accent-soft)':'var(--surface)',
                      transition:'border-color .14s, background .14s'}}>
                    <span style={{width:38,height:38,borderRadius:9,background:t.color,color:'#fff',display:'flex',alignItems:'center',justifyContent:'center',flex:'none'}}>
                      <Icon d={IC.fileText} size={18}/>
                    </span>
                    <div>
                      <div style={{fontWeight:700,fontSize:14,color:typeId===t.id?'var(--accent-strong)':'var(--text)'}}>{t.name}</div>
                      {t.description&&<div className="muted" style={{fontSize:11.5,marginTop:2}}>{t.description}</div>}
                    </div>
                    {typeId===t.id&&<span style={{marginLeft:'auto',flex:'none',color:'var(--accent)'}}><Icon d={IC.check} size={16} stroke={2.5}/></span>}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* STEP 2: детали */}
          {step===2&&(
            <div style={{display:'flex',flexDirection:'column',gap:16}}>
              <Field label="Название документа *">
                <input className="input" value={title} onChange={e=>setTitle(e.target.value)}
                  placeholder={selType?`Например: ${selType.name} №114`:''} style={{width:'100%',fontSize:14,height:40}}/>
              </Field>
              {projects.length>0&&(
                <Field label="Проект (необязательно)">
                  <select className="input" value={projectId} onChange={e=>setProjectId(e.target.value)} style={{width:'100%',height:40,fontSize:13.5,cursor:'pointer'}}>
                    <option value="">— Без проекта —</option>
                    {projects.map(p=><option key={p.id} value={p.id}>{p.code?p.code+' · ':''}{p.name}</option>)}
                  </select>
                </Field>
              )}
              <Field label="Комментарий">
                <textarea className="input" value={comment} onChange={e=>setComment(e.target.value)}
                  placeholder="Опишите содержание или оставьте инструкцию подписантам…"
                  rows={3} style={{width:'100%',resize:'vertical',fontSize:13,padding:'10px 14px',lineHeight:1.5}}/>
              </Field>
              <div>
                <label style={{fontSize:12.5,fontWeight:700,color:'var(--text-2)',display:'block',marginBottom:6}}>Файл документа <span style={{color:'var(--red)'}}>*</span></label>
                <div onDrop={onDrop} onDragOver={e=>{e.preventDefault();setDragging(true);}} onDragLeave={()=>setDragging(false)}
                  onClick={()=>fileRef.current?.click()}
                  style={{border:'2px dashed '+(dragging?'var(--accent)':file?'var(--green)':'var(--border-strong)'),
                    borderRadius:12,padding:'22px 16px',textAlign:'center',cursor:'pointer',
                    background:dragging?'var(--accent-soft)':file?'var(--green-soft)':'var(--surface-2)',
                    transition:'all .15s'}}>
                  <input ref={fileRef} type="file" style={{display:'none'}} onChange={e=>handleFile(e.target.files[0])} accept=".pdf,.docx,.xlsx,.png,.jpg"/>
                  {file ? (
                    <div style={{display:'flex',alignItems:'center',justifyContent:'center',gap:10}}>
                      <Icon d={IC.fileText} size={22} style={{color:'var(--green)'}}/>
                      <div>
                        <div style={{fontWeight:600,fontSize:13.5,color:'var(--text)'}}>{file.name}</div>
                        <div className="muted" style={{fontSize:11.5}}>{fmtBytes(file.size)}</div>
                      </div>
                      <button onClick={e=>{e.stopPropagation();setFile(null);}} style={{border:'none',background:'transparent',cursor:'pointer',color:'var(--text-3)',padding:4}}>
                        <Icon d={IC.x} size={14}/>
                      </button>
                    </div>
                  ):(
                    <div>
                      <Icon d={IC.upload} size={28} style={{color:'var(--text-3)',marginBottom:8}}/>
                      <div style={{fontWeight:600,fontSize:13.5,color:'var(--text)'}}>Перетащите файл или нажмите для выбора</div>
                      <div className="muted" style={{fontSize:12,marginTop:4}}>PDF, DOCX, XLSX, PNG</div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* STEP 3: маршрут */}
          {step===3&&(
            <div>
              {canPickTeam ? (
                <p className="muted" style={{fontSize:13,marginBottom:4}}>Соберите маршрут: участники подписывают по порядку. Отклонение любым участником прерывает маршрут.</p>
              ):(
                <p className="muted" style={{fontSize:13,marginBottom:4}}>
                  {myLead===undefined?'Определяем вашего руководителя…':myLead===null
                    ?'У вас не указан руководитель — отправить документ некому. Обратитесь к менеджеру.'
                    :'Документ уйдёт на подпись вашему руководителю.'}
                </p>
              )}
              <div style={{display:'flex',flexDirection:'column',gap:0,marginTop:14,position:'relative'}}>
                {route.map((s,i)=>{ const last=i===route.length-1; return (
                  <div key={i} style={{display:'flex',gap:12,alignItems:'flex-start',paddingBottom:last?0:22,position:'relative'}}>
                    {!last&&<span style={{position:'absolute',left:15,top:32,bottom:0,width:2,background:'var(--border)'}}/>}
                    <div style={{width:32,height:32,borderRadius:'50%',flex:'none',zIndex:1,display:'flex',alignItems:'center',justifyContent:'center',fontWeight:700,fontSize:12,
                      background:'var(--accent)',color:'#fff'}}>{i+1}</div>
                    <div style={{flex:1,paddingTop:2}}>
                      <div style={{fontWeight:700,fontSize:13.5}}>{nameOf(s.employee_id)}</div>
                      {canPickTeam?(
                        <select value={s.role} onChange={e=>setStepRole(i,e.target.value)}
                          style={{marginTop:4,height:28,padding:'0 8px',borderRadius:7,border:'1px solid var(--border)',background:'var(--surface)',fontSize:12,cursor:'pointer',outline:'none',color:'var(--text)'}}>
                          <option value="SIGNER">Подписант</option>
                          <option value="APPROVER">Согласующий</option>
                        </select>
                      ):(
                        <div className="muted" style={{fontSize:11.5}}>{STEP_ROLE_RU[s.role]}</div>
                      )}
                    </div>
                    {canPickTeam&&(
                      <div style={{display:'flex',gap:4,alignItems:'center',paddingTop:4}}>
                        {i>0&&<button className="btn ghost sm icon" onClick={()=>moveStep(i,-1)} title="Выше" style={{width:26,height:26}}><Icon d={IC.chevU} size={12}/></button>}
                        {!last&&<button className="btn ghost sm icon" onClick={()=>moveStep(i,1)} title="Ниже" style={{width:26,height:26}}><Icon d={IC.chevD} size={12}/></button>}
                        <button className="btn ghost sm icon" onClick={()=>removeRouteStep(i)} title="Удалить" style={{width:26,height:26,color:'var(--red)'}}><Icon d={IC.x} size={12}/></button>
                      </div>
                    )}
                  </div>
                );})}
                {route.length===0&&canPickTeam&&<div className="muted" style={{fontSize:13,padding:'8px 0'}}>Маршрут пуст — добавьте хотя бы одного участника</div>}
              </div>
              {canPickTeam&&(addingEmp ? (
                <div style={{marginTop:14,border:'1px solid var(--border)',borderRadius:10,overflow:'hidden',maxHeight:220,overflowY:'auto'}}>
                  <div className="muted" style={{padding:'8px 12px 4px',fontSize:11,fontWeight:700,textTransform:'uppercase',letterSpacing:'.05em'}}>Добавить участника</div>
                  {teamList.filter(e=>e.id!==myId&&!route.some(s=>s.employee_id===e.id)).map(e=>(
                    <button key={e.id} onClick={()=>addRouteStep(e)}
                      style={{display:'flex',alignItems:'center',gap:10,padding:'8px 12px',width:'100%',border:'none',background:'transparent',cursor:'pointer',textAlign:'left'}}
                      onMouseEnter={ev=>ev.currentTarget.style.background='var(--surface-2)'}
                      onMouseLeave={ev=>ev.currentTarget.style.background='transparent'}>
                      <Avatar id={e.id} name={e.name} size={28}/>
                      <div style={{fontWeight:600,fontSize:13}}>{e.name}</div>
                    </button>
                  ))}
                </div>
              ):(
                <button className="btn ghost sm" style={{marginTop:14,color:'var(--accent-strong)'}} onClick={()=>setAddingEmp(true)}>
                  <Icon d={IC.plus} size={14}/>Добавить участника
                </button>
              ))}
              <div className="card" style={{marginTop:16,background:'var(--accent-soft)',border:'1px solid var(--accent-soft)',padding:'12px 14px',gap:6,display:'flex',flexDirection:'column'}}>
                <div style={{fontWeight:700,fontSize:12.5,color:'var(--accent-strong)',display:'flex',alignItems:'center',gap:7}}><Icon d={IC.clock} size={14}/>После отправки</div>
                <div className="muted" style={{fontSize:12}}>Документ получит статус <b>«На подписании»</b>. Участники маршрута получат уведомление и смогут подписать или отклонить.</div>
              </div>
            </div>
          )}
        </div>

        {/* footer */}
        <div style={{padding:'14px 24px',borderTop:'1px solid var(--border)',display:'flex',alignItems:'center',gap:10,background:'var(--surface)'}}>
          {step>1
            ? <button className="btn sm" onClick={()=>setStep(s=>s-1)} disabled={saving}><Icon d={IC.chevL} size={14}/>Назад</button>
            : <button className="btn sm" onClick={onClose}>Отмена</button>}
          <div style={{flex:1}}/>
          <div className="muted" style={{fontSize:12}}>Шаг {step} из 3</div>
          {step<3
            ? <button className="btn sm primary" onClick={goNext} disabled={step===1?!typeId:!title.trim()||!file}>
                Далее<Icon d={IC.chevR} size={14}/>
              </button>
            : <button className="btn sm primary" onClick={submit} disabled={saving||route.length===0}>
                <Icon d={IC.send} size={14}/>{saving?'Отправка…':'Отправить на подписание'}
              </button>}
        </div>
      </div>
    </div>
  );
}

/* ============ Библиотека шаблонов ============ */
function TemplatesModal({ types, canManage, onClose, showToast }){
  const [templates,setTemplates]=useState(null);
  const [pendingFile,setPendingFile]=useState(null);
  const [tplTitle,setTplTitle]=useState('');
  const [tplTypeId,setTplTypeId]=useState(types[0]?.id||'');
  const [dragging,setDragging]=useState(false);
  const [busy,setBusy]=useState(false);
  const fileRef=useRef(null);

  const load=()=>API.document.getTemplates().then(setTemplates);
  useEffect(()=>{ load().catch(err=>{ showToast(err.detail||'Не удалось загрузить шаблоны'); onClose(); }); },[]);

  const pickFile=(f)=>{ if(!f) return; setPendingFile(f); setTplTitle(f.name.replace(/\.[^.]+$/,'')); };

  const upload=async()=>{
    if(!tplTitle.trim()||!tplTypeId) return;
    setBusy(true);
    try{
      const fd=new FormData();
      fd.append('file', pendingFile);
      fd.append('title', tplTitle.trim());
      fd.append('type_id', tplTypeId);
      await API.document.uploadTemplate(fd);
      setPendingFile(null);
      showToast('Шаблон добавлен');
      await load();
    }catch(err){ showToast(err.detail||'Не удалось загрузить шаблон'); }
    finally{ setBusy(false); }
  };
  const remove=async(t)=>{
    try{ await API.document.deleteTemplate(t.id); showToast('Шаблон удалён'); await load(); }
    catch(err){ showToast(err.detail||'Не удалось удалить шаблон'); }
  };

  return (
    <div style={{position:'fixed',inset:0,zIndex:200,display:'flex',alignItems:'center',justifyContent:'center',background:'oklch(0.25 0.02 255 / 0.5)',backdropFilter:'blur(3px)'}}
      onClick={e=>{ if(e.target===e.currentTarget) onClose(); }}>
      <div className="card fade-in" style={{width:580,maxWidth:'95vw',maxHeight:'85vh',display:'flex',flexDirection:'column',padding:0,overflow:'hidden',boxShadow:'var(--shadow-lg)'}}>
        <div style={{padding:'20px 24px 16px',borderBottom:'1px solid var(--border)',display:'flex',alignItems:'center',gap:12}}>
          <span style={{width:38,height:38,borderRadius:9,background:'var(--accent)',color:'#fff',display:'flex',alignItems:'center',justifyContent:'center',flex:'none'}}>
            <Icon d={IC.inbox} size={18}/>
          </span>
          <div style={{flex:1}}>
            <div style={{fontWeight:800,fontSize:16}}>Библиотека шаблонов</div>
            <div className="muted" style={{fontSize:12}}>Готовые шаблоны документов для скачивания</div>
          </div>
          <button className="btn ghost sm icon" onClick={onClose}><Icon d={IC.x} size={16}/></button>
        </div>

        {canManage && (
          <div style={{padding:'12px 24px',borderBottom:'1px solid var(--border)',background:'var(--surface-2)'}}>
            {pendingFile ? (
              <div style={{display:'flex',gap:8,alignItems:'center',flexWrap:'wrap'}}>
                <Icon d={IC.fileText} size={18} style={{color:'var(--accent)',flexShrink:0}}/>
                <input className="input" value={tplTitle} onChange={e=>setTplTitle(e.target.value)} placeholder="Название шаблона"
                  style={{flex:2,minWidth:160,height:34,fontSize:13}}/>
                <select className="input" value={tplTypeId} onChange={e=>setTplTypeId(e.target.value)} style={{flex:1,minWidth:120,height:34,fontSize:13,cursor:'pointer'}}>
                  {types.map(t=><option key={t.id} value={t.id}>{t.name}</option>)}
                </select>
                <button className="btn sm primary" onClick={upload} disabled={busy||!tplTitle.trim()}>{busy?'Загрузка…':'Загрузить'}</button>
                <button className="btn ghost sm icon" onClick={()=>setPendingFile(null)}><Icon d={IC.x} size={14}/></button>
              </div>
            ):(
              <div onDrop={e=>{e.preventDefault();setDragging(false);pickFile(e.dataTransfer.files[0]);}}
                onDragOver={e=>{e.preventDefault();setDragging(true);}} onDragLeave={()=>setDragging(false)}
                onClick={()=>fileRef.current?.click()}
                style={{border:'2px dashed '+(dragging?'var(--accent)':'var(--border-strong)'),borderRadius:10,padding:'14px 16px',
                  textAlign:'center',cursor:'pointer',background:dragging?'var(--accent-soft)':'var(--surface)',transition:'all .15s',display:'flex',alignItems:'center',gap:12}}>
                <input ref={fileRef} type="file" style={{display:'none'}} accept=".pdf,.docx,.xlsx,.pptx"
                  onChange={e=>{pickFile(e.target.files[0]);e.target.value='';}}/>
                <Icon d={IC.upload} size={20} style={{color:'var(--accent)',flex:'none'}}/>
                <div style={{textAlign:'left'}}>
                  <div style={{fontWeight:600,fontSize:13}}>Перетащите файл или нажмите для загрузки шаблона</div>
                  <div className="muted" style={{fontSize:11.5}}>PDF, DOCX, XLSX, PPTX</div>
                </div>
              </div>
            )}
          </div>
        )}

        <div style={{flex:1,overflowY:'auto',padding:'8px 16px 16px'}}>
          {templates===null&&<div style={{padding:'8px 0'}}>{[0,1,2].map(i=><div key={i} className="skel" style={{height:48,marginBottom:8}}/>)}</div>}
          {templates&&templates.length===0 && <div className="muted" style={{textAlign:'center',padding:'32px 0',fontSize:13}}>Шаблоны пока не добавлены</div>}
          {(templates||[]).map(t=>(
            <div key={t.id} style={{display:'flex',alignItems:'center',gap:12,padding:'10px 8px',borderRadius:9,transition:'background .12s'}}
              onMouseEnter={e=>e.currentTarget.style.background='var(--surface-2)'}
              onMouseLeave={e=>e.currentTarget.style.background='transparent'}>
              <span style={{width:36,height:36,borderRadius:8,background:t.document_type.color,color:'#fff',display:'flex',alignItems:'center',justifyContent:'center',flex:'none'}}>
                <Icon d={IC.fileText} size={16}/>
              </span>
              <div style={{flex:1,minWidth:0}}>
                <div style={{fontWeight:600,fontSize:13,whiteSpace:'nowrap',overflow:'hidden',textOverflow:'ellipsis'}}>{t.title}</div>
                <div className="muted" style={{fontSize:11.5}}>{t.document_type.name} · {fmtDateY(t.created_at)}</div>
              </div>
              <div style={{display:'flex',gap:6,alignItems:'center'}}>
                <button className="btn sm" title="Скачать" style={{height:30,gap:5}}
                  onClick={()=>API.document.downloadTemplate(t.id, t.title).catch(err=>showToast(err.detail||'Не удалось скачать шаблон'))}>
                  <Icon d={IC.download} size={13}/>Скачать
                </button>
                {canManage && (
                  <button className="btn ghost sm icon" title="Удалить" style={{width:28,height:28,color:'var(--red)'}} onClick={()=>remove(t)}>
                    <Icon d={IC.trash} size={13}/>
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        <div style={{padding:'12px 24px',borderTop:'1px solid var(--border)',display:'flex',alignItems:'center',gap:10}}>
          {canManage
            ? <div className="muted" style={{fontSize:12,flex:1}}>Управление шаблонами доступно администратору</div>
            : <div className="muted" style={{fontSize:12,flex:1}}>Шаблоны доступны только для скачивания</div>}
          <button className="btn sm" onClick={onClose}>Закрыть</button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { DocsScreen });
