/* ============ API-КЛИЕНТ: живой бэкенд (порты 8001–8009) ============ */
(function(){
  const HOST = location.hostname || 'localhost';
  const SERVICE_PORTS = {
    auth: 8001,
    profile: 8002,
    management: 8003,
    timesheet: 8004,
    reporting: 8005,
    absence: 8006,
    document: 8007,
    notification: 8008,
    chat: 8009,
  };
  const TOKEN_KEY = 'ts_access_token';

  function baseUrl(service){ return `http://${HOST}:${SERVICE_PORTS[service]}`; }

  function getToken(){ return localStorage.getItem(TOKEN_KEY); }
  function setToken(token){ localStorage.setItem(TOKEN_KEY, token); }
  function clearToken(){ localStorage.removeItem(TOKEN_KEY); }

  // Читаем клеймы JWT на клиенте (без проверки подписи — она дело бэка)
  function parseToken(token){
    try{
      const b64 = token.split('.')[1].replace(/-/g,'+').replace(/_/g,'/');
      const json = decodeURIComponent(atob(b64).split('').map(c=>'%'+('00'+c.charCodeAt(0).toString(16)).slice(-2)).join(''));
      return JSON.parse(json);
    }catch{ return null; }
  }

  function session(){
    const token = getToken();
    if(!token) return null;
    const p = parseToken(token);
    if(!p || (p.exp && p.exp*1000 < Date.now())) return null;
    return { userId:p.sub, email:p.email, roles:p.roles||[], permissions:p.permissions||[] };
  }

  // Маппинг ролей бэка на раскладку навигации прототипа
  function uiRole(){
    const s = session();
    if(!s) return 'employee';
    if(s.roles.includes('Администратор')) return 'admin';
    if(s.roles.includes('Менеджер')) return 'manager';
    return 'employee';
  }

  class ApiError extends Error{
    constructor(status, detail){ super(detail); this.name='ApiError'; this.status=status; this.detail=detail; }
  }

  function detailToMessage(status, data){
    // slowapi (rate limit) отвечает {"error": "..."} вместо {"detail": "..."}
    if(status === 429) return 'Слишком много попыток. Подождите минуту и попробуйте снова.';
    const d = data && data.detail;
    if(typeof d === 'string') return d;
    if(Array.isArray(d)) return d.map(e=>e.msg||JSON.stringify(e)).join('; ');
    if(data && typeof data.error === 'string') return data.error;
    return `Ошибка запроса (${status})`;
  }

  async function tryRefresh(){
    try{
      const res = await fetch(baseUrl('auth')+'/auth/refresh', { method:'POST', credentials:'include' });
      if(!res.ok) return false;
      const data = await res.json();
      setToken(data.access_token);
      return true;
    }catch{ return false; }
  }

  async function request(service, path, opts={}){
    const { method='GET', body, headers={}, raw=false, _retried=false } = opts;
    const init = { method, headers:{ ...headers }, credentials:'include' };
    if(body instanceof FormData){
      init.body = body;
    } else if(body !== undefined){
      init.headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(body);
    }
    const token = getToken();
    if(token) init.headers['Authorization'] = 'Bearer '+token;

    let res;
    try{ res = await fetch(baseUrl(service)+path, init); }
    catch{ throw new ApiError(0, 'Сервис недоступен. Проверьте, что бэкенд запущен.'); }

    if(res.status === 401 && token && !_retried){
      if(await tryRefresh()) return request(service, path, { ...opts, _retried:true });
      clearToken();
      window.dispatchEvent(new Event('ts:logout'));
      throw new ApiError(401, 'Сессия истекла, войдите заново');
    }
    if(!res.ok){
      let data = null;
      try{ data = await res.json(); }catch{}
      throw new ApiError(res.status, detailToMessage(res.status, data));
    }
    if(raw) return res;
    if(res.status === 204) return null;
    return res.json();
  }

  const API = {
    request, session, uiRole, getToken, clearToken, ApiError,
    auth: {
      async login(identity, password){
        const body = identity.includes('@') ? { email:identity, password } : { number:identity, password };
        const data = await request('auth', '/auth/login', { method:'POST', body });
        setToken(data.access_token);
        return data;
      },
      async logout(){
        try{ await request('auth', '/auth/logout', { method:'POST' }); }catch{}
        clearToken();
      },
      requestPasswordReset(identifier){
        return request('auth', '/auth/password/reset-requests/', { method:'POST', body:{ identifier } });
      },
      getResetRequests(status){
        const q = status ? `?status=${encodeURIComponent(status)}` : '';
        return request('auth', `/auth/password/reset-requests/${q}`);
      },
      resolveResetRequest(id){
        return request('auth', `/auth/password/reset-requests/${id}/resolve`, { method:'POST' });
      },
      register(body){ return request('auth', '/auth/register', { method:'POST', body }); },
      changePassword(currentPassword, newPassword){
        return request('auth', '/auth/password/change', { method:'POST', body:{ current_password:currentPassword, new_password:newPassword } });
      },
      getSessions(){ return request('auth', '/auth/sessions/'); },
      revokeSession(id){ return request('auth', `/auth/sessions/${id}`, { method:'DELETE' }); },
      revokeAllSessions(){ return request('auth', '/auth/sessions/', { method:'DELETE' }); },
      getPermissions(){ return request('auth', '/admin/permissions'); },
      getRolesWithPermissions(){ return request('auth', '/admin/roles'); },
      setRolePermissions(roleId, codes){
        return request('auth', `/admin/roles/${roleId}/permissions`, { method:'PUT', body:{ permission_codes: codes } });
      },
    },
    profile: {
      getEmployee(id){ return request('profile', `/employees/${id}`); },
      updateEmployee(id, body){ return request('profile', `/employees/${id}`, { method:'PATCH', body }); },
      getDepartments(){ return request('profile', '/departments/'); },
      getGrades(){ return request('profile', '/grades/'); },
      getSkills(){ return request('profile', '/skills'); },
      updateSkills(id, skillIds){ return request('profile', `/employees/${id}/skills`, { method:'PUT', body:{ skill_ids: skillIds } }); },
    },
    timesheet: {
      getSummary(id, params){
        const q = params ? '?' + new URLSearchParams(params) : '';
        return request('timesheet', `/employees/${id}/summary${q}`);
      },
      getEntryTypes(){ return request('timesheet', '/entry-types/'); },
      getCalendar(year){ return request('timesheet', `/production-calendar/${year}`); },
      getPeriods(employeeId){ return request('timesheet', `/periods/?employee_id=${employeeId}&limit=100`); },
      getEntries(periodId){ return request('timesheet', `/periods/${periodId}/entries/`); },
      createEntry(periodId, body){ return request('timesheet', `/periods/${periodId}/entries/`, { method:'POST', body }); },
      updateEntry(periodId, entryId, body){ return request('timesheet', `/periods/${periodId}/entries/${entryId}`, { method:'PATCH', body }); },
      deleteEntry(periodId, entryId){ return request('timesheet', `/periods/${periodId}/entries/${entryId}`, { method:'DELETE' }); },
      getAllPeriods(){ return request('timesheet', '/periods/?limit=100'); },
      getOvertimeApprovals(all){ return request('timesheet', `/overtime-approvals/${all?'?all_statuses=true':''}`); },
      resolveOvertime(id, action, comment){
        return request('timesheet', `/overtime-approvals/${id}/${action}`, { method:'POST', body:{ comment: comment||null } });
      },
      submitPeriod(periodId){ return request('timesheet', `/periods/${periodId}/submit`, { method:'POST' }); },
      approvePeriod(periodId){ return request('timesheet', `/periods/${periodId}/approve`, { method:'POST' }); },
      rejectPeriod(periodId, comment){ return request('timesheet', `/periods/${periodId}/reject`, { method:'POST', body:{ comment } }); },
    },
    management: {
      getEmployees(){ return request('management', '/employees/?limit=100'); },
      getRoles(){ return request('management', '/roles/'); },
      createRole(body){ return request('management', '/roles/', { method:'POST', body }); },
      updateRole(id, body){ return request('management', `/roles/${id}`, { method:'PATCH', body }); },
      deleteRole(id){ return request('management', `/roles/${id}`, { method:'DELETE' }); },
      getEmployeeStatuses(){ return request('management', '/employee-statuses/'); },
      setRoles(empId, roleIds){ return request('management', `/employees/${empId}/roles`, { method:'PATCH', body:{ role_ids: roleIds } }); },
      setStatus(empId, statusId){ return request('management', `/employees/${empId}/status`, { method:'PATCH', body:{ status_id: statusId } }); },
      setLead(empId, leadId){ return request('management', `/employees/${empId}/lead`, { method:'PATCH', body:{ lead_id: leadId } }); },
      getProjects(){ return request('management', '/projects/'); },
      createProject(body){ return request('management', '/projects/', { method:'POST', body }); },
      updateProject(id, body){ return request('management', `/projects/${id}`, { method:'PATCH', body }); },
      getProjectRoles(){ return request('management', '/project-roles/'); },
      getProjectStatuses(){ return request('management', '/project-statuses/'); },
      getAssignmentStatuses(){ return request('management', '/assignment-statuses/'); },
      createAssignment(empId, body){ return request('management', `/employees/${empId}/assignments`, { method:'POST', body }); },
      updateAssignment(empId, assignmentId, body){ return request('management', `/employees/${empId}/assignments/${assignmentId}`, { method:'PATCH', body }); },
      deleteAssignment(empId, assignmentId){ return request('management', `/employees/${empId}/assignments/${assignmentId}`, { method:'DELETE' }); },
    },
    reporting: {
      getProjectsReport(period){ return request('reporting', `/reports/projects?period=${period}`); },
      getUtilization(period){ return request('reporting', `/reports/utilization?period=${period}`); },
    },
    document: {
      getAll(filter, search){
        const p = new URLSearchParams({ filter: filter||'all' });
        if(search) p.set('search', search);
        return request('document', `/documents/?${p}`);
      },
      create(formData){ return request('document', '/documents/', { method:'POST', body: formData }); },
      sign(id){ return request('document', `/documents/${id}/sign`, { method:'POST' }); },
      reject(id, comment){ return request('document', `/documents/${id}/reject`, { method:'POST', body:{ comment } }); },
      getTypes(){ return request('document', '/document-types/'); },
      getTemplates(){ return request('document', '/document-templates/'); },
      uploadTemplate(formData){ return request('document', '/document-templates/', { method:'POST', body: formData }); },
      deleteTemplate(id){ return request('document', `/document-templates/${id}`, { method:'DELETE' }); },
      // Скачивание с токеном: blob → временная ссылка; расширение берём из Content-Disposition
      async download(path, baseName){
        const res = await request('document', path, { raw:true });
        const cd = res.headers.get('Content-Disposition') || '';
        const m = cd.match(/filename="?([^";]+)"?/);
        const serverName = m ? m[1] : '';
        const dot = serverName.lastIndexOf('.');
        const filename = (baseName || serverName || 'file') + (dot > -1 ? serverName.slice(dot) : '');
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = Object.assign(document.createElement('a'), { href:url, download:filename });
        document.body.appendChild(a); a.click(); a.remove();
        setTimeout(()=>URL.revokeObjectURL(url), 5000);
      },
      downloadFile(id, baseName){ return this.download(`/documents/${id}/file`, baseName); },
      downloadTemplate(id, baseName){ return this.download(`/document-templates/${id}/file`, baseName); },
    },
    chat: {
      getChannels(){ return request('chat', '/chat/channels'); },
      createDm(employeeId){ return request('chat', `/chat/dms/${employeeId}`, { method:'POST' }); },
      getMembers(channelId){ return request('chat', `/chat/channels/${channelId}/members`); },
      getMessages(channelId, before){
        const q = before ? `?before=${encodeURIComponent(before)}` : '';
        return request('chat', `/chat/channels/${channelId}/messages${q}`);
      },
      sendMessage(channelId, body){ return request('chat', `/chat/channels/${channelId}/messages`, { method:'POST', body }); },
      updateMessage(id, text){ return request('chat', `/chat/messages/${id}`, { method:'PATCH', body:{ text } }); },
      deleteMessage(id){ return request('chat', `/chat/messages/${id}`, { method:'DELETE' }); },
      togglePin(channelId){ return request('chat', `/chat/channels/${channelId}/pin`, { method:'POST' }); },
      toggleMute(channelId){ return request('chat', `/chat/channels/${channelId}/mute`, { method:'POST' }); },
      // WebSocket с авто-реконнектом; handlers: {onMessage, onTyping, onRead, onStatus}
      connect(handlers={}){
        let ws=null, closed=false, attempt=0;
        const open=()=>{
          const token=getToken();
          if(closed||!token) return;
          ws=new WebSocket(`ws://${HOST}:${SERVICE_PORTS.chat}/ws/chat?token=${encodeURIComponent(token)}`);
          ws.onopen=()=>{ attempt=0; handlers.onStatus&&handlers.onStatus('online'); };
          ws.onmessage=(e)=>{
            let data; try{ data=JSON.parse(e.data); }catch{ return; }
            if(data.event==='message') handlers.onMessage&&handlers.onMessage(data);
            else if(data.event==='typing') handlers.onTyping&&handlers.onTyping(data);
            else if(data.event==='read') handlers.onRead&&handlers.onRead(data);
          };
          ws.onclose=()=>{
            handlers.onStatus&&handlers.onStatus('offline');
            if(!closed) setTimeout(open, Math.min(1000*2**attempt++, 15000));
          };
          ws.onerror=()=>{ try{ ws.close(); }catch{} };
        };
        open();
        return {
          send(payload){ if(ws&&ws.readyState===1) ws.send(JSON.stringify(payload)); },
          close(){ closed=true; try{ ws&&ws.close(); }catch{} },
        };
      },
    },
    notification: {
      getAll(unreadOnly){ return request('notification', `/notifications/${unreadOnly?'?unread_only=true':''}`); },
      markRead(id){ return request('notification', `/notifications/${id}/read`, { method:'POST' }); },
      markAllRead(){ return request('notification', '/notifications/read-all', { method:'POST' }); },
      getPreferences(){ return request('notification', '/notifications/preferences'); },
      updatePreferences(body){ return request('notification', '/notifications/preferences', { method:'PATCH', body }); },
    },
    absence: {
      getAbsences(params){
        const q = params ? '?' + new URLSearchParams(params) : '';
        return request('absence', `/absences/${q}`);
      },
      getTypes(){ return request('absence', '/absence-types/'); },
      createAbsence(body){ return request('absence', '/absences/', { method:'POST', body }); },
      submitAbsence(id){ return request('absence', `/absences/${id}/submit`, { method:'POST' }); },
      withdrawAbsence(id){ return request('absence', `/absences/${id}`, { method:'DELETE' }); },
      getVacationBalance(employeeId){ return request('absence', `/employees/${employeeId}/vacation-balance`); },
      approveAbsence(id, comment){ return request('absence', `/absences/${id}/approve`, { method:'POST', body:{ comment: comment||null } }); },
      rejectAbsence(id, comment){ return request('absence', `/absences/${id}/reject`, { method:'POST', body:{ comment } }); },
    },
  };

  window.API = API;
})();
