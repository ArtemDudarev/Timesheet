/* ============ MOCK DATA (Russian) ============ */
(function(){
  const MONTHS = ['Январь','Февраль','Март','Апрель','Май','Июнь','Июль','Август','Сентябрь','Октябрь','Ноябрь','Декабрь'];
  const WD = ['Пн','Вт','Ср','Чт','Пт','Сб','Вс'];

  // current demo period: Май 2026
  const YEAR = 2026, MONTH = 4; // 0-indexed May

  // Производственный календарь — Май 2026
  const HOLIDAYS = { 1:'Праздник Весны и Труда', 11:'День Победы (перенос с 9 мая)' };
  const SHORT_DAYS = { 8:7 }; // предпраздничный сокращённый день — 7 ч

  function daysInMonth(y,m){ return new Date(y,m+1,0).getDate(); }
  function iso(y,m,d){ return `${y}-${String(m+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`; }
  function buildDays(y,m){
    const n = daysInMonth(y,m);
    const holMonth = (y===YEAR && m===MONTH);
    const arr = [];
    for(let d=1; d<=n; d++){
      const date = new Date(y,m,d);
      let wd = date.getDay(); wd = wd===0?6:wd-1;
      const weekend = wd>=5;
      const holiday = holMonth ? (HOLIDAYS[d] || null) : null;
      const short = holMonth ? (SHORT_DAYS[d] || null) : null;
      const working = !weekend && !holiday;
      const cap = working ? (short || 8) : 0;
      arr.push({ d, wd, label:WD[wd], weekend, holiday, short, working, cap, key:iso(y,m,d) });
    }
    return arr;
  }
  function dayInfo(date){
    const y=date.getFullYear(), m=date.getMonth(), d=date.getDate();
    let wd=date.getDay(); wd=wd===0?6:wd-1;
    const weekend=wd>=5;
    const holMonth=(y===YEAR&&m===MONTH);
    const holiday=holMonth?(HOLIDAYS[d]||null):null;
    const short=holMonth?(SHORT_DAYS[d]||null):null;
    const working=!weekend&&!holiday;
    const cap=working?(short||8):0;
    return { y, m, d, date:new Date(y,m,d), wd, label:WD[wd], weekend, holiday, short, working, cap,
      key:iso(y,m,d), monthName:MONTHS[m], monthShort:MONTHS[m].slice(0,3) };
  }

  const PROJECTS = [
    { id:'p1', code:'OMNI',  name:'Omnichannel платформа', client:'РТ-Банк',        color:'oklch(0.55 0.13 250)', status:'active',   budget:2400, spent:1612, deadline:'2026-08-30', lead:'e2' },
    { id:'p2', code:'LOYAL', name:'Программа лояльности',   client:'Маркет+',        color:'oklch(0.58 0.15 295)', status:'active',   budget:1600, spent:1180, deadline:'2026-06-15', lead:'e2' },
    { id:'p3', code:'DWH',   name:'Хранилище данных DWH',   client:'Энерго-Холдинг', color:'oklch(0.62 0.13 155)', status:'active',   budget:3200, spent:1020, deadline:'2026-11-01', lead:'e5' },
    { id:'p4', code:'MOBILE',name:'Мобильное приложение',   client:'СтримМедиа',     color:'oklch(0.74 0.13 75)',  status:'risk',     budget:1800, spent:1690, deadline:'2026-05-28', lead:'e2' },
    { id:'p5', code:'INFRA', name:'Миграция в облако',      client:'Внутренний',     color:'oklch(0.60 0.02 255)', status:'paused',   budget:900,  spent:540,  deadline:'2026-09-10', lead:'e5' },
    { id:'p6', code:'CRM',   name:'Внедрение CRM',          client:'ТоргСеть',       color:'oklch(0.60 0.18 22)',  status:'active',   budget:2000, spent:430,  deadline:'2026-10-20', lead:'e2' },
  ].map(p=>({ ...p, progress: Math.min(p.spent / p.budget, 1) }));

  const ABSENCE_TYPES = [
    { id:'ab1', code:'vacation',  name:'Отпуск',       color:'oklch(0.58 0.15 295)', bg:'var(--violet-soft)', icon:'calendar' },
    { id:'ab2', code:'sick',      name:'Больничный',   color:'var(--red)',            bg:'var(--red-soft)',    icon:'shield'   },
    { id:'ab3', code:'trip',      name:'Командировка', color:'var(--amber)',          bg:'var(--amber-soft)', icon:'briefcase'},
    { id:'ab4', code:'day_off',   name:'Отгул',        color:'oklch(0.55 0.02 255)', bg:'var(--surface-3)',  icon:'clock'    },
  ];

  const ABSENCE_STATUSES = [
    { id:'abs1', code:'draft',    name:'Черновик',           cls:''      },
    { id:'abs2', code:'pending',  name:'На согласовании',    cls:'amber' },
    { id:'abs3', code:'approved', name:'Утверждён',          cls:'green' },
    { id:'abs4', code:'rejected', name:'Отклонён',           cls:'red'   },
  ];

  const ABSENCES = [
    { id:'av1', empId:'e1', typeId:'ab1', typeName:'Отпуск',       start:'2026-06-12', end:'2026-06-26', days:11, statusCode:'approved', comment:'Плановый ежегодный отпуск', submittedAt:'2026-05-03', approvedBy:'e2' },
    { id:'av2', empId:'e1', typeId:'ab2', typeName:'Больничный',   start:'2026-05-15', end:'2026-05-15', days:1,  statusCode:'approved', comment:'ОРВИ',                       submittedAt:'2026-05-15', approvedBy:'e2' },
    { id:'av3', empId:'e1', typeId:'ab3', typeName:'Командировка', start:'2026-04-07', end:'2026-04-09', days:3,  statusCode:'approved', comment:'Встреча с клиентом РТ-Банк',  submittedAt:'2026-04-01', approvedBy:'e2' },
    { id:'av4', empId:'e1', typeId:'ab4', typeName:'Отгул',        start:'2026-07-04', end:'2026-07-04', days:1,  statusCode:'pending',  comment:'Отгул за переработку',       submittedAt:'2026-05-20', approvedBy:null },
    { id:'av5', empId:'e6', typeId:'ab1', typeName:'Отпуск',       start:'2026-05-20', end:'2026-06-05', days:13, statusCode:'approved', comment:'Ежегодный отпуск',           submittedAt:'2026-04-25', approvedBy:'e2' },
    { id:'av6', empId:'e7', typeId:'ab3', typeName:'Командировка', start:'2026-05-26', end:'2026-05-30', days:5,  statusCode:'approved', comment:'Конференция DevOps Days',     submittedAt:'2026-05-10', approvedBy:'e5' },
  ];

  function buildAbsentDays(empId, year, month){
    const result={};
    ABSENCES.filter(a=>a.empId===empId&&a.statusCode==='approved').forEach(a=>{
      const s=new Date(a.start), e=new Date(a.end);
      const cur=new Date(s);
      while(cur<=e){
        if(cur.getFullYear()===year&&cur.getMonth()===month){
          result[cur.getDate()]=a.typeId;
        }
        cur.setDate(cur.getDate()+1);
      }
    });
    return result;
  }

  const PROJECT_ROLES = [
    { id:'r1', name:'Тимлид',       description:'Технический руководитель проекта' },
    { id:'r2', name:'Разработчик',  description:'Разработка функциональности'      },
    { id:'r3', name:'Аналитик',     description:'Анализ данных и требований'       },
    { id:'r4', name:'QA-инженер',   description:'Тестирование и контроль качества' },
    { id:'r5', name:'Дизайнер',     description:'UX/UI проектирование'             },
    { id:'r6', name:'DevOps',       description:'Инфраструктура и CI/CD'           },
    { id:'r7', name:'PM',           description:'Управление проектом'              },
  ];

  const ASSIGNMENT_STATUSES = [
    { id:'as1', code:'active',    name:'Активен',      description:'Сотрудник активно работает на проекте' },
    { id:'as2', code:'paused',    name:'Приостановлен',description:'Временно не задействован'              },
    { id:'as3', code:'completed', name:'Завершён',      description:'Участие завершено'                    },
  ];

  const ASSIGNMENTS = [
    { id:'a_e1_p1', empId:'e1', project:{ id:'p1', name:'Omnichannel платформа', start_date:'2025-10-01', end_date:'2026-08-30' }, project_role:PROJECT_ROLES[1], start_date:'2025-10-01', end_date:'2026-08-30', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e1_p2', empId:'e1', project:{ id:'p2', name:'Программа лояльности',   start_date:'2026-01-15', end_date:'2026-06-15' }, project_role:PROJECT_ROLES[1], start_date:'2026-01-15', end_date:'2026-06-15', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e1_p4', empId:'e1', project:{ id:'p4', name:'Мобильное приложение',   start_date:'2026-02-01', end_date:'2026-05-28' }, project_role:PROJECT_ROLES[1], start_date:'2026-02-01', end_date:'2026-05-28', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e2_p1', empId:'e2', project:{ id:'p1', name:'Omnichannel платформа',  start_date:'2025-10-01', end_date:'2026-08-30' }, project_role:PROJECT_ROLES[0], start_date:'2025-10-01', end_date:'2026-08-30', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e2_p2', empId:'e2', project:{ id:'p2', name:'Программа лояльности',   start_date:'2026-01-15', end_date:'2026-06-15' }, project_role:PROJECT_ROLES[6], start_date:'2026-01-15', end_date:'2026-06-15', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e2_p4', empId:'e2', project:{ id:'p4', name:'Мобильное приложение',   start_date:'2026-02-01', end_date:'2026-05-28' }, project_role:PROJECT_ROLES[0], start_date:'2026-02-01', end_date:'2026-05-28', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e2_p6', empId:'e2', project:{ id:'p6', name:'Внедрение CRM',          start_date:'2026-03-01', end_date:'2026-10-20' }, project_role:PROJECT_ROLES[6], start_date:'2026-03-01', end_date:'2026-10-20', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e3_p1', empId:'e3', project:{ id:'p1', name:'Omnichannel платформа',  start_date:'2025-11-01', end_date:'2026-08-30' }, project_role:PROJECT_ROLES[1], start_date:'2025-11-01', end_date:'2026-08-30', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e3_p3', empId:'e3', project:{ id:'p3', name:'Хранилище данных DWH',   start_date:'2026-02-01', end_date:'2026-11-01' }, project_role:PROJECT_ROLES[1], start_date:'2026-02-01', end_date:'2026-11-01', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e4_p2', empId:'e4', project:{ id:'p2', name:'Программа лояльности',   start_date:'2026-01-20', end_date:'2026-06-15' }, project_role:PROJECT_ROLES[3], start_date:'2026-01-20', end_date:'2026-06-15', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e4_p4', empId:'e4', project:{ id:'p4', name:'Мобильное приложение',   start_date:'2026-02-01', end_date:'2026-05-28' }, project_role:PROJECT_ROLES[3], start_date:'2026-02-01', end_date:'2026-05-28', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e5_p3', empId:'e5', project:{ id:'p3', name:'Хранилище данных DWH',   start_date:'2026-01-10', end_date:'2026-11-01' }, project_role:PROJECT_ROLES[0], start_date:'2026-01-10', end_date:'2026-11-01', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e5_p5', empId:'e5', project:{ id:'p5', name:'Миграция в облако',      start_date:'2026-03-01', end_date:'2026-09-10' }, project_role:PROJECT_ROLES[2], start_date:'2026-03-01', end_date:'2026-09-10', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e6_p1', empId:'e6', project:{ id:'p1', name:'Omnichannel платформа',  start_date:'2026-01-01', end_date:'2026-08-30' }, project_role:PROJECT_ROLES[4], start_date:'2026-01-01', end_date:'2026-08-30', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e6_p6', empId:'e6', project:{ id:'p6', name:'Внедрение CRM',          start_date:'2026-03-01', end_date:'2026-10-20' }, project_role:PROJECT_ROLES[4], start_date:'2026-03-01', end_date:'2026-10-20', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e7_p5', empId:'e7', project:{ id:'p5', name:'Миграция в облако',      start_date:'2026-03-01', end_date:'2026-09-10' }, project_role:PROJECT_ROLES[5], start_date:'2026-03-01', end_date:'2026-09-10', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e7_p3', empId:'e7', project:{ id:'p3', name:'Хранилище данных DWH',   start_date:'2026-04-01', end_date:'2026-11-01' }, project_role:PROJECT_ROLES[5], start_date:'2026-04-01', end_date:'2026-11-01', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e8_p2', empId:'e8', project:{ id:'p2', name:'Программа лояльности',   start_date:'2026-02-01', end_date:'2026-06-15' }, project_role:PROJECT_ROLES[1], start_date:'2026-02-01', end_date:'2026-06-15', assignment_status:ASSIGNMENT_STATUSES[0] },
    { id:'a_e8_p6', empId:'e8', project:{ id:'p6', name:'Внедрение CRM',          start_date:'2026-03-01', end_date:'2026-10-20' }, project_role:PROJECT_ROLES[1], start_date:'2026-03-01', end_date:'2026-10-20', assignment_status:ASSIGNMENT_STATUSES[0] },
  ];

  const STATUS_CATALOG = [
    { id:'s1', name:'active',   label:'Активен',     description:'Сотрудник работает в штатном режиме', color:'var(--green)',  bg:'var(--green-soft)'  },
    { id:'s2', name:'vacation', label:'В отпуске',    description:'Плановый или внеплановый отпуск',     color:'var(--violet)', bg:'var(--violet-soft)' },
    { id:'s3', name:'trip',     label:'Командировка', description:'Рабочая поездка',                    color:'var(--amber)',  bg:'var(--amber-soft)'  },
    { id:'s4', name:'sick',     label:'Больничный',   description:'Временная нетрудоспособность',        color:'var(--red)',    bg:'var(--red-soft)'    },
  ];

  const EMPLOYEES = [
    { id:'e1', firstName:'Анна',    lastName:'Соколова',  role:'employee', position:'Senior Frontend',   grade:'M3', dept:'Веб-разработка',  email:'a.sokolova@company.ru',       phone:'+7 (916) 210-33-41', address:'Москва, ул. Ленина, 12',        birthday:'1993-07-14', imageUrl:null, hire:'2021-03-01', capacity:168, logged:152, util:0.90, projects:['p1','p2','p4'], skills:['React','TypeScript','Дизайн-системы','Node.js'],       managerId:'e2',  status:'s1' },
    { id:'e2', firstName:'Дмитрий', lastName:'Котов',     role:'manager',  position:'Тимлид / PM',       grade:'M4', dept:'Веб-разработка',  email:'d.kotov@company.ru',           phone:'+7 (916) 450-88-12', address:'Москва, Садовая ул., 5',        birthday:'1989-03-22', imageUrl:null, hire:'2019-06-15', capacity:168, logged:140, util:0.83, projects:['p1','p2','p4','p6'], skills:['Управление','Архитектура','React','Планирование'],    managerId:null,  status:'s1' },
    { id:'e3', firstName:'Игорь',   lastName:'Лебедев',   role:'employee', position:'Backend Developer', grade:'M2', dept:'Бэкенд',          email:'i.lebedev@company.ru',         phone:'+7 (916) 311-07-55', address:'Москва, пр. Мира, 88',          birthday:'1996-11-30', imageUrl:null, hire:'2022-09-01', capacity:168, logged:171, util:1.02, projects:['p1','p3'], skills:['Go','PostgreSQL','Kafka','Docker'],                      managerId:'e2',  status:'s1' },
    { id:'e4', firstName:'Мария',   lastName:'Орлова',    role:'employee', position:'QA Engineer',       grade:'M2', dept:'Тестирование',    email:'m.orlova@company.ru',          phone:'+7 (916) 782-14-90', address:'Москва, ул. Тверская, 3',       birthday:'1997-05-08', imageUrl:null, hire:'2023-01-20', capacity:168, logged:120, util:0.71, projects:['p2','p4'], skills:['Автотесты','Playwright','API-тестирование'],            managerId:'e2',  status:'s1' },
    { id:'e5', firstName:'Павел',   lastName:'Зайцев',    role:'manager',  position:'Data Lead',         grade:'M4', dept:'Аналитика',       email:'p.zaytsev@company.ru',         phone:'+7 (916) 920-44-17', address:'СПб, Невский пр., 60',          birthday:'1988-09-17', imageUrl:null, hire:'2020-11-10', capacity:168, logged:158, util:0.94, projects:['p3','p5'], skills:['Python','DWH','Airflow','SQL'],                          managerId:null,  status:'s1' },
    { id:'e6', firstName:'Елена',   lastName:'Власова',   role:'employee', position:'UX/UI Designer',    grade:'M3', dept:'Дизайн',          email:'e.vlasova@company.ru',         phone:'+7 (916) 543-29-88', address:'Москва, ул. Арбат, 15',         birthday:'1994-02-19', imageUrl:null, hire:'2022-04-05', capacity:168, logged:96,  util:0.57, projects:['p1','p6'], skills:['Figma','Прототипы','Исследования'],                      managerId:'e2',  status:'s2' },
    { id:'e7', firstName:'Роман',   lastName:'Гусев',     role:'employee', position:'DevOps Engineer',   grade:'M3', dept:'Инфраструктура',  email:'r.gusev@company.ru',           phone:'+7 (916) 667-51-34', address:'Москва, ул. Профсоюзная, 42',   birthday:'1992-12-03', imageUrl:null, hire:'2021-08-12', capacity:168, logged:164, util:0.98, projects:['p5','p3'], skills:['Kubernetes','Terraform','CI/CD','AWS'],                  managerId:'e5',  status:'s3' },
    { id:'e8', firstName:'Ольга',   lastName:'Никитина',  role:'employee', position:'Middle Frontend',   grade:'M2', dept:'Веб-разработка',  email:'o.nikitina@company.ru',        phone:'+7 (916) 134-77-22', address:'Москва, ул. Новая, 9',          birthday:'1999-08-25', imageUrl:null, hire:'2023-07-01', capacity:168, logged:138, util:0.82, projects:['p2','p6'], skills:['React','CSS','Vue'],                                     managerId:'e2',  status:'s1' },
  ].map(e=>({ ...e, name: e.firstName+' '+e.lastName }));

  // Tasks catalog
  const TASKS_DB = [
    { id:'t1_1', projectId:'p1', name:'Разработка фич',       empId:'e1' },
    { id:'t1_2', projectId:'p1', name:'Код-ревью',             empId:'e1' },
    { id:'t1_3', projectId:'p1', name:'Планирование спринта',  empId:'e1' },
    { id:'t2_1', projectId:'p2', name:'История начислений',    empId:'e1' },
    { id:'t2_2', projectId:'p2', name:'Поддержка и консультации', empId:'e1' },
    { id:'t4_1', projectId:'p4', name:'Багфиксы релиза',       empId:'e1' },
  ];

  // timesheet of current user (Анна e1) — rows keyed by ISO date
  function genTimesheetRows(){
    const rows = [
      { id:'t1', projectId:'p1', task:'Разработка фич',           hours:{} },
      { id:'t2', projectId:'p1', task:'Код-ревью',                hours:{} },
      { id:'t3', projectId:'p2', task:'Поддержка и консультации', hours:{} },
      { id:'t4', projectId:'p4', task:'Багфиксы релиза',          hours:{} },
    ];
    const today = 22;
    const mayDays = buildDays(YEAR, MONTH);
    const pat = [ [4,2,3,0],[5,1,2,0],[3,2,2,2],[2,2,3,2],[4,1,1,1] ];
    mayDays.forEach(day=>{
      if(!day.working || day.d>today) return;
      const p = pat[day.d % pat.length].slice();
      const sum = p[0]+p[1]+p[2]+p[3];
      if(sum>day.cap) p[0]-=(sum-day.cap);
      const k = iso(YEAR, MONTH, day.d);
      if(p[0]>0) rows[0].hours[k] = p[0];
      if(p[1]>0) rows[1].hours[k] = p[1];
      if(p[2]>0) rows[2].hours[k] = p[2];
      if(p[3]>0) rows[3].hours[k] = p[3];
    });
    // история янв–апр для годового разреза
    const histPat = [ [4,2,1,0],[3,2,2,1],[4,1,1,1],[2,2,2,2],[5,1,0,0] ];
    for(let m=0; m<MONTH; m++){
      buildDays(YEAR,m).filter(d=>d.working).forEach((day,i)=>{
        const base = histPat[(m+i) % histPat.length];
        const k = iso(YEAR, m, day.d);
        if(base[0]) rows[0].hours[k] = base[0];
        if(base[1]) rows[1].hours[k] = base[1];
        if(i%2===0 && base[2]) rows[2].hours[k] = base[2];
        if(i%3===0 && base[3]) rows[3].hours[k] = base[3];
      });
    }
    return rows;
  }

  // generic timesheet for ANY employee (manager review)
  function genTimesheetRowsFor(empId){
    const emp = EMPLOYEES.find(e=>e.id===empId);
    if(!emp) return [];
    const TASK_NAMES = ['Разработка','Код-ревью','Митинги и синки','Тестирование','Документация','Поддержка','Аналитика'];
    const rows=[]; let tid=1;
    const seed = empId.charCodeAt(1) || 5;
    (emp.projects||[]).forEach((pid,pi)=>{
      const nTasks = 1 + ((seed+pi)%2);
      for(let t=0;t<nTasks;t++) rows.push({ id:'g'+(tid++), projectId:pid, task:TASK_NAMES[(pi*2+t+seed)%TASK_NAMES.length], hours:{} });
    });
    if(!rows.length) return rows;
    const today = 22;
    buildDays(YEAR,MONTH).forEach(day=>{
      if(!day.working || day.d>today) return;
      let cap = day.cap;
      rows.forEach((r,ri)=>{
        if(cap<=0) return;
        const v = Math.min(((seed+ri*3+day.d)%4), cap);
        if(v>0){ r.hours[iso(YEAR,MONTH,day.d)] = v; cap-=v; }
      });
    });
    for(let m=0;m<MONTH;m++){
      buildDays(YEAR,m).filter(d=>d.working).forEach((day,di)=>{
        if(di%2!==0) return;
        rows.forEach((r,ri)=>{ const v=((seed+ri+m+di)%3)+2; if(v>0) r.hours[iso(YEAR,m,day.d)]=v; });
      });
    }
    if(rows.length && ['e3','e5','e7'].includes(empId)){
      rows[0].hours[iso(YEAR,MONTH,19)] = 10;
      rows[0].hours[iso(YEAR,MONTH,16)] = 5;
    }
    return rows;
  }

  const APPROVALS = [
    { id:'a1', empId:'e1', period:'Май 2026', hours:152, status:'pending',  submitted:'2026-05-22' },
    { id:'a2', empId:'e3', period:'Май 2026', hours:171, status:'pending',  submitted:'2026-05-22' },
    { id:'a3', empId:'e6', period:'Май 2026', hours:96,  status:'pending',  submitted:'2026-05-21' },
    { id:'a4', empId:'e8', period:'Май 2026', hours:138, status:'approved', submitted:'2026-05-20' },
    { id:'a5', empId:'e4', period:'Май 2026', hours:120, status:'rejected', submitted:'2026-05-19' },
  ];

  const WEEKLY_TREND = [38,40,36,42,39,41,37,40];

  const SKILLS_CATALOG = [
    'React','Vue','Angular','TypeScript','JavaScript','Next.js','CSS','HTML','Vite','Webpack',
    'Figma','Дизайн-системы','Storybook','GraphQL','REST API',
    'Go','Node.js','Python','Java','C#','.NET','FastAPI','Django','Spring',
    'PostgreSQL','MySQL','MongoDB','Redis','Elasticsearch',
    'DWH','Airflow','dbt','SQL','PySpark','Tableau','Power BI','Looker',
    'Kubernetes','Docker','Terraform','Ansible','CI/CD','GitHub Actions','AWS','GCP','Azure',
    'Prometheus','Grafana','Linux',
    'Автотесты','Playwright','Cypress','Selenium','Postman','API-тестирование','Нагрузочное тестирование',
    'Управление командой','Agile','Scrum','Kanban','Jira','Confluence','Планирование','Архитектура',
    'Техлидерство','Прототипы','UX-исследования','Менторинг','Исследования','Документация',
  ];

  const PASSWORD_RESETS = [
    { id:'pr1', empId:'e4', name:'Мария Орлова', status:'pending', requestedAt:'2026-05-22T08:14:00' },
  ];

  /* ── CASBIN: роли ── */
  const CASBIN_ROLES = [
    { id:'role_admin',    name:'admin',    label:'Администратор', description:'Полный доступ, управление пользователями, ролями и политиками', inherits:['manager'] },
    { id:'role_manager',  name:'manager',  label:'Менеджер',      description:'Управление командой, согласование табелей и отсутствий, отчёты', inherits:['employee'] },
    { id:'role_employee', name:'employee', label:'Сотрудник',     description:'Базовый доступ: таймшит, документы, отсутствия, чат', inherits:[] },
  ];

  /* ── CASBIN: p-правила (subject, object, action, effect) ── */
  const CASBIN_POLICIES = [
    { id:'cp1',  sub:'employee', obj:'/timesheet',    act:'read',    eft:'allow' },
    { id:'cp2',  sub:'employee', obj:'/timesheet',    act:'write',   eft:'allow' },
    { id:'cp3',  sub:'employee', obj:'/docs',         act:'read',    eft:'allow' },
    { id:'cp4',  sub:'employee', obj:'/docs',         act:'write',   eft:'allow' },
    { id:'cp5',  sub:'employee', obj:'/chat',         act:'read',    eft:'allow' },
    { id:'cp6',  sub:'employee', obj:'/chat',         act:'write',   eft:'allow' },
    { id:'cp7',  sub:'employee', obj:'/absences',     act:'read',    eft:'allow' },
    { id:'cp8',  sub:'employee', obj:'/absences',     act:'write',   eft:'allow' },
    { id:'cp9',  sub:'employee', obj:'/settings',     act:'read',    eft:'allow' },
    { id:'cp10', sub:'employee', obj:'/settings',     act:'write',   eft:'allow' },
    { id:'cp11', sub:'manager',  obj:'/manager',      act:'read',    eft:'allow' },
    { id:'cp12', sub:'manager',  obj:'/manager',      act:'write',   eft:'allow' },
    { id:'cp13', sub:'manager',  obj:'/reports',      act:'read',    eft:'allow' },
    { id:'cp14', sub:'manager',  obj:'/timesheet',    act:'approve', eft:'allow' },
    { id:'cp15', sub:'manager',  obj:'/absences',     act:'approve', eft:'allow' },
    { id:'cp16', sub:'admin',    obj:'/admin',        act:'read',    eft:'allow' },
    { id:'cp17', sub:'admin',    obj:'/admin',        act:'write',   eft:'allow' },
    { id:'cp18', sub:'admin',    obj:'/api/users',    act:'read',    eft:'allow' },
    { id:'cp19', sub:'admin',    obj:'/api/users',    act:'write',   eft:'allow' },
    { id:'cp20', sub:'admin',    obj:'/api/users',    act:'delete',  eft:'allow' },
    { id:'cp21', sub:'admin',    obj:'/api/roles',    act:'read',    eft:'allow' },
    { id:'cp22', sub:'admin',    obj:'/api/roles',    act:'write',   eft:'allow' },
    { id:'cp23', sub:'admin',    obj:'/api/policies', act:'read',    eft:'allow' },
    { id:'cp24', sub:'admin',    obj:'/api/policies', act:'write',   eft:'allow' },
    { id:'cp25', sub:'admin',    obj:'/api/policies', act:'delete',  eft:'allow' },
    { id:'cp26', sub:'admin',    obj:'/api/audit',    act:'read',    eft:'allow' },
  ];

  /* ── CASBIN: g-правила (user → role) ── */
  const CASBIN_ASSIGNMENTS = [
    { id:'ca1', userId:'e1', role:'employee' },
    { id:'ca2', userId:'e2', role:'manager'  },
    { id:'ca3', userId:'e2', role:'admin'    },
    { id:'ca4', userId:'e3', role:'employee' },
    { id:'ca5', userId:'e4', role:'employee' },
    { id:'ca6', userId:'e5', role:'manager'  },
    { id:'ca7', userId:'e6', role:'employee' },
    { id:'ca8', userId:'e7', role:'employee' },
    { id:'ca9', userId:'e8', role:'employee' },
  ];

  /* ── Журнал аудита ── */
  const AUDIT_LOG = [
    { id:'al1',  ts:'2026-05-22T14:32:11', userId:'e1', sub:'employee', obj:'/timesheet',    act:'write',   res:'allow', ip:'10.0.1.42' },
    { id:'al2',  ts:'2026-05-22T14:28:05', userId:'e2', sub:'admin',    obj:'/api/users',    act:'read',    res:'allow', ip:'10.0.0.5'  },
    { id:'al3',  ts:'2026-05-22T14:15:44', userId:'e3', sub:'employee', obj:'/admin',        act:'read',    res:'deny',  ip:'10.0.1.18' },
    { id:'al4',  ts:'2026-05-22T13:55:20', userId:'e4', sub:'employee', obj:'/reports',      act:'read',    res:'deny',  ip:'10.0.1.37' },
    { id:'al5',  ts:'2026-05-22T13:40:08', userId:'e5', sub:'manager',  obj:'/manager',      act:'write',   res:'allow', ip:'10.0.0.12' },
    { id:'al6',  ts:'2026-05-22T13:22:34', userId:'e2', sub:'admin',    obj:'/api/policies', act:'write',   res:'allow', ip:'10.0.0.5'  },
    { id:'al7',  ts:'2026-05-22T12:58:17', userId:'e6', sub:'employee', obj:'/docs',         act:'read',    res:'allow', ip:'10.0.1.21' },
    { id:'al8',  ts:'2026-05-22T12:41:09', userId:'e7', sub:'employee', obj:'/absences',     act:'write',   res:'allow', ip:'10.0.1.55' },
    { id:'al9',  ts:'2026-05-22T12:19:43', userId:'e1', sub:'employee', obj:'/manager',      act:'read',    res:'deny',  ip:'10.0.1.42' },
    { id:'al10', ts:'2026-05-22T11:58:02', userId:'e3', sub:'employee', obj:'/timesheet',    act:'write',   res:'allow', ip:'10.0.1.18' },
    { id:'al11', ts:'2026-05-22T11:44:27', userId:'e2', sub:'admin',    obj:'/admin',        act:'read',    res:'allow', ip:'10.0.0.5'  },
    { id:'al12', ts:'2026-05-22T11:30:14', userId:'e8', sub:'employee', obj:'/chat',         act:'write',   res:'allow', ip:'10.0.1.63' },
    { id:'al13', ts:'2026-05-22T10:55:38', userId:'e4', sub:'employee', obj:'/timesheet',    act:'write',   res:'allow', ip:'10.0.1.37' },
    { id:'al14', ts:'2026-05-22T10:33:11', userId:'e5', sub:'manager',  obj:'/reports',      act:'read',    res:'allow', ip:'10.0.0.12' },
    { id:'al15', ts:'2026-05-22T10:02:45', userId:'e3', sub:'employee', obj:'/api/users',    act:'read',    res:'deny',  ip:'10.0.1.18' },
  ];

  const NOTIFICATIONS = [
    { id:'n1', type:'approval', title:'Табель ожидает согласования', text:'Игорь Лебедев отправил табель за май — 171 ч (переработка)', time:'10 мин назад', today:true, read:false, target:'manager' },
    { id:'n2', type:'doc', title:'Документ ждёт вашей подписи', text:'Договор оказания услуг №OMNI-114', time:'1 ч назад', today:true, read:false, target:'docs' },
    { id:'n3', type:'chat', title:'Новое сообщение', text:'Дмитрий Котов: Демо для РТ-Банка в пятницу, держим темп.', time:'2 ч назад', today:true, read:false, target:'chat' },
    { id:'n4', type:'deadline', title:'Приближается дедлайн', text:'Проект MOBILE — срок 28 мая (через 6 дней)', time:'5 ч назад', today:true, read:true, target:'manager' },
    { id:'n5', type:'mention', title:'Упоминание в канале', text:'OMNI · команда: нужно ревью от @Анна', time:'Вчера', today:false, read:true, target:'chat' },
    { id:'n6', type:'doc', title:'Документ подписан', text:'Счёт на оплату №2026-0481 — подписан руководителем', time:'Вчера', today:false, read:true, target:'docs' },
    { id:'n7', type:'approval', title:'Табель утверждён', text:'Ваш табель за апрель утверждён', time:'2 дня назад', today:false, read:true, target:'timesheet' },
    { id:'n8', type:'password', title:'Запрос временного пароля', text:'Мария Орлова запросила временный пароль', time:'2 ч назад', today:true, read:false, target:'manager' },
  ];

  const DAYS = buildDays(YEAR, MONTH);
  window.DB = {
    MONTHS, WD, YEAR, MONTH, HOLIDAYS, SHORT_DAYS,
    daysInMonth, buildDays, dayInfo, iso,
    PROJECTS, EMPLOYEES, APPROVALS, WEEKLY_TREND, NOTIFICATIONS, SKILLS_CATALOG,
    PASSWORD_RESETS, STATUS_CATALOG, PROJECT_ROLES, ASSIGNMENT_STATUSES, ASSIGNMENTS,
    ABSENCE_TYPES, ABSENCE_STATUSES, ABSENCES, buildAbsentDays,
    CASBIN_ROLES, CASBIN_POLICIES, CASBIN_ASSIGNMENTS, AUDIT_LOG,
    genTimesheetRows, genTimesheetRowsFor,
    days: DAYS,
    workdays: DAYS.filter(d=>d.working).length,
    norm: DAYS.reduce((a,d)=>a+d.cap,0),
    emp: id => EMPLOYEES.find(e=>e.id===id),
    proj: id => PROJECTS.find(p=>p.id===id),
    empAssignments: empId => ASSIGNMENTS.filter(a=>a.empId===empId),
    projAssignment: (empId,projId) => ASSIGNMENTS.find(a=>a.empId===empId&&a.project.id===projId),
    currentUserId: 'e1',
  };
})();
