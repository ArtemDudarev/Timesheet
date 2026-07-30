/* ============ SCREEN: Отчётность для руководства ============ */
function ReportsScreen({ showToast }){
  const [period,setPeriod]=useState('month');

  const totalLogged = DB.EMPLOYEES.reduce((a,e)=>a+e.logged,0);
  const totalCap = DB.EMPLOYEES.reduce((a,e)=>a+e.capacity,0);
  const avgUtil = Math.round(totalLogged/totalCap*100);
  const totalBudget = DB.PROJECTS.reduce((a,p)=>a+p.budget,0);
  const totalSpent = DB.PROJECTS.reduce((a,p)=>a+p.spent,0);
  const atRisk = DB.PROJECTS.filter(p=>p.status==='risk').length;

  // utilization bars sorted
  const utilItems = [...DB.EMPLOYEES].sort((a,b)=>b.util-a.util).map(e=>({
    label:e.name.split(' ')[0]+' '+e.name.split(' ')[1][0]+'.', value:Math.round(e.util*100),
    color: e.util>1?'var(--red)':e.util>=0.85?'var(--green)':e.util>=0.6?'var(--accent)':'var(--amber)', over:e.util>1
  }));

  // project hours
  const projItems = DB.PROJECTS.map(p=>({ label:p.code, value:p.spent, color:p.color, dot:p.color }));

  // plan/fact (по департаментам, демо)
  const pfData=[
    {label:'Веб', plan:980, fact:1024},
    {label:'Бэкенд', plan:520, fact:498},
    {label:'Аналитика', plan:640, fact:602},
    {label:'QA', plan:380, fact:341},
    {label:'Дизайн', plan:300, fact:288},
    {label:'DevOps', plan:340, fact:372},
  ];

  const exportCsv=()=>{
    const rows=[['Проект','Клиент','Факт, ч','Бюджет, ч','Прогресс','Статус']];
    DB.PROJECTS.forEach(p=>rows.push([p.name,p.client,p.spent,p.budget,Math.round(p.progress*100)+'%',PROJ_STATUS[p.status].label]));
    const csv=rows.map(r=>r.join(';')).join('\n');
    const blob=new Blob(['\ufeff'+csv],{type:'text/csv'});
    const url=URL.createObjectURL(blob); const a=document.createElement('a');
    a.href=url; a.download='Отчёт_по_проектам_Май2026.csv'; a.click(); URL.revokeObjectURL(url);
    showToast('Отчёт выгружен в CSV');
  };

  return (
    <div className="fade-in" style={{display:'flex', flexDirection:'column', gap:18}}>
      <PageHead title="Отчётность" subtitle="Сводка для руководства · Май 2026"
        actions={<>
          <div className="seg">
            <button className={period==='month'?'on':''} onClick={()=>setPeriod('month')}>Месяц</button>
            <button className={period==='quarter'?'on':''} onClick={()=>setPeriod('quarter')}>Квартал</button>
          </div>
          <button className="btn sm primary" onClick={exportCsv}><Icon d={IC.download} size={15}/>Выгрузить в Excel</button>
        </>}/>

      {/* KPI */}
      <div style={{display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:14}}>
        <StatCard label="Средняя утилизация" value={avgUtil+'%'} trend={3} sub="по всей команде" icon="trend" accent/>
        <StatCard label="Списано часов" value={totalLogged.toLocaleString('ru')} sub={'из '+totalCap.toLocaleString('ru')+' доступных'} icon="clock"/>
        <StatCard label="Бюджет проектов" value={Math.round(totalSpent/totalBudget*100)+'%'} sub={totalSpent+' / '+totalBudget+' ч'} icon="briefcase"/>
        <StatCard label="Проекты под риском" value={atRisk} sub="требуют внимания" icon="flag"/>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'1fr 1fr', gap:18}}>
        {/* utilization */}
        <div className="card" style={{padding:20}}>
          <SectionTitle title="Загрузка сотрудников" right={<span className="muted" style={{fontSize:12}}>% от нормы</span>}/>
          <div style={{marginTop:16}}><BarsH items={utilItems} max={110} fmt={v=>v+'%'}/></div>
          <div style={{display:'flex', gap:16, marginTop:16, flexWrap:'wrap'}}>
            <Legend color="var(--green)" label="85–100% оптимально"/>
            <Legend color="var(--amber)" label="< 60% недозагрузка"/>
            <Legend color="var(--red)" label="> 100% переработка"/>
          </div>
        </div>

        {/* project hours */}
        <div className="card" style={{padding:20}}>
          <SectionTitle title="Затраты по проектам" right={<span className="muted" style={{fontSize:12}}>часов за период</span>}/>
          <div style={{marginTop:16}}><BarsH items={projItems} fmt={v=>v}/></div>
          <div className="divider" style={{margin:'16px 0'}}/>
          <div style={{display:'flex', justifyContent:'space-between', fontSize:13}}>
            <span className="muted">Итого списано</span>
            <span className="mono" style={{fontWeight:700}}>{totalSpent.toLocaleString('ru')} ч</span>
          </div>
        </div>
      </div>

      <div style={{display:'grid', gridTemplateColumns:'1fr 1.2fr', gap:18}}>
        {/* plan/fact */}
        <div className="card" style={{padding:20}}>
          <SectionTitle title="План / факт по отделам"/>
          <div style={{marginTop:18}}><ColumnsPF data={pfData}/></div>
          <div style={{display:'flex', gap:16, marginTop:14}}>
            <Legend color="var(--surface-3)" label="План" square/>
            <Legend color="var(--accent)" label="Факт" square/>
          </div>
        </div>

        {/* project status table */}
        <div className="card" style={{padding:'20px 20px 8px'}}>
          <SectionTitle title="Прогресс и сроки проектов"/>
          <table className="tbl" style={{marginTop:12}}>
            <thead><tr><th>Проект</th><th>Прогресс</th><th>Бюджет</th><th>Срок</th><th>Статус</th></tr></thead>
            <tbody>
              {DB.PROJECTS.map(p=>{ const st=PROJ_STATUS[p.status]; const bp=Math.round(p.spent/p.budget*100); return (
                <tr key={p.id}>
                  <td><span style={{display:'inline-flex', alignItems:'center', gap:8}}><span style={{width:8,height:8,borderRadius:3,background:p.color}}/>{p.code}</span></td>
                  <td>
                    <div style={{display:'flex', alignItems:'center', gap:8, width:100}}>
                      <div className="progress" style={{flex:1}}><span style={{width:p.progress*100+'%', background:p.color}}/></div>
                      <span className="mono" style={{fontSize:11}}>{Math.round(p.progress*100)}%</span>
                    </div>
                  </td>
                  <td className="mono" style={{fontSize:12.5, color:bp>95?'var(--red)':'var(--text-2)'}}>{bp}%</td>
                  <td className="muted mono" style={{fontSize:12}}>{fmtDate(p.deadline)}</td>
                  <td><span className={'badge '+st.cls} style={{height:22, fontSize:11}}><span className="dot"/>{st.label}</span></td>
                </tr>
              );})}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function Legend({ color, label, square }){
  return (
    <span style={{display:'inline-flex', alignItems:'center', gap:7, fontSize:12, color:'var(--text-2)'}}>
      <span style={{width:11, height:11, borderRadius:square?3:50, background:color}}/>{label}
    </span>
  );
}

Object.assign(window, { ReportsScreen, Legend });
