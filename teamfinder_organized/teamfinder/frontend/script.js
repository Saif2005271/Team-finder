// TeamFinder — Frontend JS
// Handles navigation, rendering, API calls, chat, exams, and profile management

// app state
const state = {
  currentPage: 'home',
  loggedIn: false,
  user: null,
  chatHistory: []
};

// API client — same origin as FastAPI backend
const API_BASE = '';

async function apiCall(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const opts = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers
    },
    ...options
  };

  const token = localStorage.getItem('token');
  if (token) {
    opts.headers['Authorization'] = `Bearer ${token}`;
  }

  const res = await fetch(url, opts);

  if (res.status === 401 || res.status === 403) {
    if (state.loggedIn) {
      toast('Session expired. Please sign in again.', 'error');
      doLogout();
      showPage('login');
    }
    throw new Error('Unauthorized');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || 'Request failed');
  }

  return res.json();
}

function updateNavAuth() {
  const btn = document.getElementById('loginNavBtn');
  if (state.loggedIn) {
    btn.textContent = 'Sign Out';
    btn.onclick = doLogout;
  } else {
    btn.textContent = 'Sign In';
    btn.onclick = () => showPage('login');
  }
}

// demo data — mirrors the Python backend seed data
const DEMO_MATCHES = [
  { id:'u1', name:'Sara Al-Ahmad',   major:'Computer Science',     score:0.91, skills:['Python','Machine Learning','SQL','Statistics'],    hours:20, bio:'Final-year CS student, mostly into data work.' },
  { id:'u2', name:'Omar Khalil',     major:'Software Engineering', score:0.78, skills:['React','TypeScript','Node.js','CSS'],               hours:15, bio:'Full-stack dev, spend most of my time in the React side of things.' },
  { id:'u3', name:'Lina Nasser',     major:'Data Science',         score:0.85, skills:['Python','SQL','Statistics','R'],                   hours:25, bio:'Data analyst, looking to move into BI.' },
  { id:'u4', name:'Rami Hourani',    major:'Cybersecurity',        score:0.62, skills:['Python','Linux','Network Security'],               hours:10, bio:'Into CTFs and a bit of security research on the side.' },
  { id:'u5', name:'Dina Haddad',     major:'Computer Science',     score:0.74, skills:['Java','Spring Boot','SQL','Docker'],               hours:18, bio:'Backend dev, currently learning more about microservices.' },
  { id:'u6', name:'Sami Barakat',    major:'Data Science',         score:0.69, skills:['Python','Tableau','Statistics','Power BI'],        hours:22, bio:'Mostly working on data visualisation projects.' },
];

const DEMO_PROJECTS = [
  { id:'p1', title:'University Event Scheduler',   desc:'Web app for organising and RSVPing to events on campus.',          skills:['React','Node.js','SQL'],                    source:'student' },
  { id:'p2', title:'Campus Food Waste Monitor',    desc:'ML model that predicts cafeteria food surplus to cut down waste.', skills:['Python','Machine Learning','Statistics'],   source:'student' },
  { id:'p3', title:'Awesome Machine Learning',     desc:'Curated GitHub list of ML frameworks, datasets and tutorials.',    skills:['Python','TensorFlow','PyTorch'],            source:'github'  },
  { id:'p4', title:'Titanic Survival Prediction',  desc:'The classic Kaggle competition — predicting passenger survival.',  skills:['Python','Pandas','Statistics'],             source:'kaggle'  },
  { id:'p5', title:'Secure Web CTF Challenge',     desc:'Web exploitation challenge from CTFtime, mostly SQLi and XSS.',    skills:['Python','SQL','Penetration Testing'],       source:'ctftime' },
  { id:'p6', title:'Real-Time Chat App',           desc:'Chat app with rooms and auth, built on top of Socket.io.',         skills:['Node.js','React','TypeScript'],             source:'student' },
];

// avatar colors based on user id
const AVATAR_COLORS = [
  'linear-gradient(135deg,#ef4258,#b8b3d4)',
  'linear-gradient(135deg,#14b8a6,#059669)',
  'linear-gradient(135deg,#f59e0b,#ef4444)',
  'linear-gradient(135deg,#ec4899,#8b5cf6)',
  'linear-gradient(135deg,#06b6d4,#3b82f6)',
  'linear-gradient(135deg,#84cc16,#14b8a6)',
];
const avatarColor = (id) => AVATAR_COLORS[id.charCodeAt(id.length - 1) % AVATAR_COLORS.length];

// navigation
const PUBLIC_PAGES = new Set(['login', 'register', 'about']);

function showPage(name) {
  // redirect to login if not authenticated
  if (!PUBLIC_PAGES.has(name) && !state.loggedIn) {
    if (state.currentPage !== 'login') {
      toast('You need to sign in first.', 'error');
    }
    name = 'login';
  }

  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  const target = document.getElementById('page-' + name);
  if (target) target.classList.add('active');

  // hide nav on auth pages, show on the rest
  if (name === 'login' || name === 'register') {
    document.body.classList.add('auth-active');
  } else {
    document.body.classList.remove('auth-active');
  }

  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  state.currentPage = name;

  if (name === 'match')    renderMatchesFromAPI();
  if (name === 'projects') renderProjectsFromAPI('all');
  if (name === 'profile')  renderProfileFromAPI();
  if (name === 'home')     startCounters();
}

// animated counters on homepage
function animateCounter(id, target, suffix = '') {
  const el = document.getElementById(id);
  let val = 0;
  const step = Math.ceil(target / 50);
  const timer = setInterval(() => {
    val = Math.min(val + step, target);
    el.textContent = val.toLocaleString() + suffix;
    if (val >= target) clearInterval(timer);
  }, 30);
}

function startCounters() {
  animateCounter('counter1', 1240);
  animateCounter('counter2', 8730);
  animateCounter('counter3',  312);
  animateCounter('counter4',  487);
}

// match rendering
function renderMatches() {
  const majorFilter = document.getElementById('filterMajor')?.value || '';
  const scoreFilter = parseInt(document.getElementById('filterScore')?.value || '0');
  const skillFilter = document.getElementById('filterSkill')?.value || '';
  const grid = document.getElementById('matchGrid');

  const filtered = DEMO_MATCHES.filter(m => {
    if (majorFilter && m.major !== majorFilter) return false;
    if (m.score * 100 < scoreFilter) return false;
    if (skillFilter && !m.skills.includes(skillFilter)) return false;
    return true;
  });

  grid.innerHTML = filtered.length === 0
    ? '<p style="color:var(--muted);padding:2rem">No matches with these filters.</p>'
    : filtered.map(m => matchCard(m)).join('');
}

function matchCard(m) {
  const pct     = Math.round(m.score * 100);
  const circ    = 2 * Math.PI * 20; // radius = 20
  const offset  = circ - (pct / 100) * circ;
  const color   = pct > 80 ? '#22c55e' : pct > 60 ? '#ef4258' : '#f59e0b';
  const initials = m.name.split(' ').map(n => n[0]).join('');
  const tags    = m.skills.slice(0, 3).map(s => `<span class="tag">${s}</span>`).join('');

  return `
  <div class="match-card" onclick="toast('Opening ${m.name}\\'s profile. Try connecting through a shared project!','success')">
    <div class="match-header">
      <div class="avatar" style="background:${avatarColor(m.id)}">${initials}</div>
      <div class="match-info">
        <h3>${m.name}</h3>
        <p>${m.major}</p>
      </div>
      <div class="score-ring">
        <svg width="52" height="52" viewBox="0 0 52 52">
          <circle class="track" cx="26" cy="26" r="20"/>
          <circle class="fill" cx="26" cy="26" r="20"
            stroke="${color}"
            stroke-dasharray="${circ}"
            stroke-dashoffset="${offset}"/>
        </svg>
        <div class="score-text" style="color:${color}">${pct}%</div>
      </div>
    </div>
    <div class="skill-tags">
      ${tags}
      ${m.skills.length > 3 ? `<span class="tag teal">+${m.skills.length - 3}</span>` : ''}
    </div>
    <p style="font-size:.82rem; color:var(--muted); margin-bottom:.5rem">${m.bio}</p>
    <div class="match-footer">
      <span class="avail-badge"><span class="dot"></span>${m.hours}h/week available</span>
      <button class="btn btn-outline" style="padding:.35rem .85rem; font-size:.8rem"
              onclick="event.stopPropagation(); toast('Request sent to ${m.name}!','success')">Connect</button>
    </div>
  </div>`;
}

// projects
let currentProjectFilter = 'all';

function filterProjects(source, btn) {
  currentProjectFilter = source;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  renderProjects(source);
}

function renderProjects(source) {
  const grid = document.getElementById('projectGrid');
  const list = source === 'all' ? DEMO_PROJECTS : DEMO_PROJECTS.filter(p => p.source === source);

  const sourceLabel = { student:'Student', github:'GitHub', kaggle:'Kaggle', ctftime:'CTFtime' };
  const sourceCls   = { student:'source-student', github:'source-github', kaggle:'source-kaggle', ctftime:'source-ctftime' };

  grid.innerHTML = list.map(p => `
    <div class="project-card">
      <span class="project-source ${sourceCls[p.source]}">${sourceLabel[p.source]}</span>
      <h3>${p.title}</h3>
      <p>${p.desc}</p>
      <div class="skill-tags">${p.skills.map(s => `<span class="tag">${s}</span>`).join('')}</div>
      <div class="project-footer">
        <button class="btn btn-outline" style="padding:.4rem .9rem; font-size:.8rem"
                onclick="toast('Joined project: ${p.title}','success')">Join Project</button>
      </div>
    </div>`).join('');
}

// profile rendering
let DEMO_SKILLS = { Python:5, 'Machine Learning':4, SQL:3, React:2, Statistics:4 };

function renderProfile() {
  const userName        = localStorage.getItem('user_name')        || 'Guest User';
  const userMajor       = localStorage.getItem('user_major')       || 'Not Set';
  const userBio         = localStorage.getItem('user_bio')         || '';
  const userGithub      = localStorage.getItem('user_github')      || '';
  const userCourses     = localStorage.getItem('user_courses')     || '';
  const userAvailability = localStorage.getItem('user_availability') || '20';

  document.getElementById('profileNameDisplay').textContent  = userName;
  document.getElementById('profileMajorDisplay').textContent = userMajor;
  document.getElementById('profileAvatarBig').textContent    = userName.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();

  document.getElementById('pName').value    = userName;
  document.getElementById('pMajor').value   = userMajor;
  document.getElementById('pBio').value     = userBio;
  document.getElementById('pGithub').value  = userGithub;
  document.getElementById('pCourses').value = userCourses;
  document.getElementById('availDisplay').textContent = userAvailability;

  const rangeInput = document.querySelector('input[type="range"]');
  if (rangeInput) rangeInput.value = userAvailability;
  document.getElementById('pAvail').textContent = userAvailability + 'h';

  const list = document.getElementById('profileSkillList');
  list.innerHTML = Object.entries(DEMO_SKILLS).map(([skill, level]) => `
    <div class="skill-item">
      <span class="skill-name">${skill}</span>
      <div class="skill-bar"><div class="skill-fill" style="width:${level / 5 * 100}%"></div></div>
      <span class="skill-level">${level}/5</span>
    </div>`).join('');

  document.getElementById('pSkillCount').textContent = Object.keys(DEMO_SKILLS).length;
}

async function saveProfile() {
  const name         = document.getElementById('pName').value.trim();
  const major        = document.getElementById('pMajor').value;
  const bio          = document.getElementById('pBio').value.trim();
  const github       = document.getElementById('pGithub').value.trim();
  const courses      = document.getElementById('pCourses').value.trim();
  const availability = parseInt(document.querySelector('input[type="range"]').value || '15', 10);

  if (!name) { toast('Please enter your name first.', 'error'); return; }

  localStorage.setItem('user_name',         name);
  localStorage.setItem('user_major',        major);
  localStorage.setItem('user_bio',          bio);
  localStorage.setItem('user_github',       github);
  localStorage.setItem('user_courses',      courses);
  localStorage.setItem('user_availability', String(availability));

  document.getElementById('profileNameDisplay').textContent  = name;
  document.getElementById('profileMajorDisplay').textContent = major;
  document.getElementById('profileAvatarBig').textContent    = name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase();
  document.getElementById('pAvail').textContent = availability + 'h';

  const payload = {
    major,
    courses: courses.split(',').map(s => s.trim()).filter(Boolean),
    skills: DEMO_SKILLS,
    availability_hours: availability,
    bio: bio || null,
    github_url: github || null,
  };

  try {
    await apiCall('/api/profile', { method: 'POST', body: JSON.stringify(payload) });
    toast('✅ Profile saved!', 'success');
  } catch (e) {
    toast(`Saved on your device, but the server didn't accept the update: ${e.message}`, 'error');
  }
}

// advisor chat
const ADVISOR_RESPONSES = {
  'match':   'Match scores come from **cosine similarity** between your skill vector and the other student\'s. The more skills you share at similar levels, the higher the score. If you want better matches, work on your weakest skills first.',
  'skill':   'Check the Profile page. Your lowest-rated skill is usually a good place to start. Retake the exam for it once you\'ve practiced, or pick a project from the Projects board that uses it.',
  'guide':   'The Projects board pulls real projects from **GitHub, Kaggle, HuggingFace and CTFtime**. Use the skill filter to find ones that fit your current level.',
  'exam':    'Skill exams are short multiple-choice tests with 5 questions each. Your score gives you a level:\n• 0–20% → Level 0\n• 21–60% → Level 1–2\n• 61–85% → Level 3–4\n• 86–100% → Level 5\nVerified skills count for more in the matching.',
  'default': 'I can help you with **building your skills**, understanding your **match scores**, or finding a project to join. Try one of the buttons below.'
};

function getAdvisorReply(msg) {
  const m = msg.toLowerCase();
  if (m.includes('match')  || m.includes('score')   || m.includes('similar'))  return ADVISOR_RESPONSES.match;
  if (m.includes('skill')  || m.includes('learn')   || m.includes('improve'))  return ADVISOR_RESPONSES.skill;
  if (m.includes('guide')  || m.includes('project') || m.includes('kaggle'))   return ADVISOR_RESPONSES.guide;
  if (m.includes('exam')   || m.includes('test')    || m.includes('verify'))   return ADVISOR_RESPONSES.exam;
  return ADVISOR_RESPONSES.default;
}

function addMessage(role, text) {
  const area   = document.getElementById('chatMessages');
  const div    = document.createElement('div');
  div.className = 'msg ' + role;
  const avatar  = role === 'ai'
    ? '<div class="msg-avatar">Adv</div>'
    : '<div class="msg-avatar" style="background:var(--border)">Me</div>';
  div.innerHTML = `${avatar}<div class="msg-bubble">${text.replace(/\*\*(.*?)\*\*/g,'<strong>$1</strong>').replace(/\n/g,'<br/>')}</div>`;
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
}

function showTyping() {
  const area = document.getElementById('chatMessages');
  const div  = document.createElement('div');
  div.className = 'msg ai';
  div.id = 'typingIndicator';
  div.innerHTML = `<div class="msg-avatar">Adv</div>
    <div class="msg-bubble">
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>`;
  area.appendChild(div);
  area.scrollTop = area.scrollHeight;
}

function removeTyping() {
  document.getElementById('typingIndicator')?.remove();
}

function sendChatLocal() {
  const input = document.getElementById('chatInput');
  const msg   = input.value.trim();
  if (!msg) return;
  input.value = '';
  addMessage('user', msg);
  showTyping();
  setTimeout(() => {
    removeTyping();
    addMessage('ai', getAdvisorReply(msg));
  }, 900 + Math.random() * 600);
}

function sendSuggestion(btn) {
  document.getElementById('chatInput').value = btn.textContent;
  sendChat();
}

// skill exam
let currentExamSkill     = 'Python';
let currentExamQuestions = [];
let currentExamAnswers   = {};

async function openExam(skill = 'Python') {
  currentExamSkill   = skill;
  currentExamAnswers = {};

  const container = document.getElementById('examQuestions');
  document.getElementById('examTitle').textContent = `${skill} Skill Exam`;
  container.innerHTML = '<p style="color:var(--muted)">Loading exam…</p>';
  document.getElementById('examModal').classList.add('open');

  try {
    const data = await apiCall(`/api/skills/exam/${encodeURIComponent(skill)}`);
    currentExamQuestions = data.questions || [];

    if (!currentExamQuestions.length) {
      container.innerHTML = '<p style="color:var(--muted)">There\'s no exam for this skill yet.</p>';
      return;
    }

    container.innerHTML = currentExamQuestions.map((q, i) => {
      const options = q.options || {};
      const letters = Object.keys(options);
      return `
        <div class="question-block">
          <p>${i + 1}. ${q.question}</p>
          <div class="options">
            ${letters.map(letter => `
              <button class="option-btn" data-qid="${q.id}" data-letter="${letter}"
                      onclick="selectOption(this,'${q.id}','${letter}')">${letter}. ${options[letter]}</button>
            `).join('')}
          </div>
        </div>`;
    }).join('');

  } catch (e) {
    container.innerHTML = `<p style="color:var(--muted)">Couldn't load the exam: ${e.message}</p>`;
  }
}

function selectOption(btn, qId, letter) {
  document.querySelectorAll(`[data-qid="${qId}"]`).forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
  currentExamAnswers[qId] = letter;
}

function closeExam() {
  document.getElementById('examModal').classList.remove('open');
}

async function submitExam() {
  if (!currentExamQuestions.length) { closeExam(); return; }

  const answered = Object.keys(currentExamAnswers).length;
  if (answered < currentExamQuestions.length) {
    toast(`Please answer all ${currentExamQuestions.length} questions before submitting.`, 'error');
    return;
  }

  try {
    const result = await apiCall('/api/skills/exam', {
      method: 'POST',
      body: JSON.stringify({ skill_name: currentExamSkill, answers: currentExamAnswers })
    });
    closeExam();
    toast(`✅ ${result.message}`, 'success');
    renderProfileFromAPI();
  } catch (e) {
    toast(`Exam submission failed: ${e.message}`, 'error');
  }
}

// auth
async function doLogin() {
  const email = document.getElementById('loginEmail').value.trim();
  const pass  = document.getElementById('loginPass').value;
  const err   = document.getElementById('loginError');
  err.textContent = '';

  if (!email || !pass) { err.textContent = 'Please fill in both fields.'; return; }

  try {
    const data = await apiCall('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password: pass })
    });
    localStorage.setItem('token',     data.access_token);
    localStorage.setItem('user_id',   data.user_id);
    localStorage.setItem('email',     data.email);
    localStorage.setItem('user_name', data.email.split('@')[0]);
    state.loggedIn = true;
    state.user = data;
    updateNavAuth();
    toast('Welcome back! 👋', 'success');
    showPage('home');
  } catch (e) {
    err.textContent = e.message;
  }
}

async function doRegister() {
  const name  = document.getElementById('regName').value.trim();
  const email = document.getElementById('regEmail').value.trim();
  const pass  = document.getElementById('regPass').value;
  const err   = document.getElementById('regError');
  const suc   = document.getElementById('regSuccess');
  err.textContent = ''; suc.textContent = '';

  if (!name || !email || !pass) { err.textContent = 'Please fill in all the fields.'; return; }
  if (pass.length < 8)          { err.textContent = 'Your password needs to be at least 8 characters.'; return; }

  const validDomains = ['ju.edu.jo', 'yahoo.com', 'gmail.com'];
  const domain = email.split('@')[1];
  if (!validDomains.includes(domain)) { err.textContent = 'Please use your university email.'; return; }

  try {
    const data = await apiCall('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password: pass, full_name: name })
    });
    localStorage.setItem('token',     data.access_token);
    localStorage.setItem('user_id',   data.user_id);
    localStorage.setItem('email',     data.email);
    localStorage.setItem('user_name', name);
    state.loggedIn = true;
    state.user = data;
    suc.textContent = 'Account created! Redirecting…';
    updateNavAuth();
    setTimeout(() => showPage('profile'), 1000);
  } catch (e) {
    err.textContent = e.message;
  }
}

function doLogout() {
  const keys = ['token','user_id','email','user_name','user_major','user_bio','user_github','user_courses','user_availability'];
  keys.forEach(k => localStorage.removeItem(k));
  state.loggedIn = false;
  state.user = null;
  updateNavAuth();
  toast('Signed out.', 'success');
  showPage('home');
}

// toast
function toast(msg, type = 'success') {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = `toast ${type} show`;
  setTimeout(() => el.classList.remove('show'), 3200);
}

// API-powered render functions — fall back to demo data if not logged in

async function renderMatchesFromAPI() {
  const grid = document.getElementById('matchGrid');
  if (!state.loggedIn) { renderMatches(); return; }

  grid.innerHTML = '<p style="color:var(--muted);padding:2rem">Loading matches…</p>';
  try {
    const data = await apiCall('/api/match', { method: 'POST', body: JSON.stringify({ top_n: 20 }) });
    const matches = data.matches || [];
    if (!matches.length) {
      grid.innerHTML = '<p style="color:var(--muted);padding:2rem">No matches yet. Try completing your profile first.</p>';
      return;
    }
    grid.innerHTML = matches.map(m => `
      <div class="match-card">
        <div class="match-header">
          <div class="match-avatar" style="background:${avatarColor(m.user_id)}">${(m.full_name||'?')[0]}</div>
          <div>
            <div class="match-name">${m.full_name || 'Unknown'}</div>
            <div class="match-major">${m.major || ''}</div>
          </div>
          <div class="match-score">${Math.round((m.score || 0) * 100)}%</div>
        </div>
        <p style="font-size:.85rem; color:var(--muted); margin:.75rem 0">${m.bio || ''}</p>
        <div class="skill-tags">${(m.shared_skills || []).map(s => `<span class="skill-tag">${s}</span>`).join('')}</div>
        <div style="font-size:.8rem; color:var(--muted); margin-top:.75rem">⏱ ${m.availability_hours || 0}h/week available</div>
      </div>`).join('');
  } catch (e) {
    renderMatches(); // fall back to demo data
  }
}

async function renderProjectsFromAPI(filter) {
  const grid = document.getElementById('projectGrid');
  if (!state.loggedIn) { renderProjects(filter); return; }

  grid.innerHTML = '<p style="color:var(--muted);padding:2rem">Loading projects…</p>';
  try {
    const src  = filter === 'all' ? '' : `?source=${filter}`;
    const data = await apiCall(`/api/projects${src}`);
    const projects = data.projects || [];

    if (!projects.length) {
      grid.innerHTML = '<p style="color:var(--muted);padding:2rem">No projects found.</p>';
      return;
    }

    const srcColors = { student:'var(--accent)', github:'#333', kaggle:'#20beff', ctftime:'var(--gold)' };
    grid.innerHTML = projects.map(p => `
      <div class="project-card">
        <div class="project-source" style="background:${srcColors[p.source]||'var(--accent)'}20; color:${srcColors[p.source]||'var(--accent)'}; border:1px solid ${srcColors[p.source]||'var(--accent)'}40; padding:.2rem .7rem; border-radius:999px; font-size:.75rem; font-weight:600; width:fit-content; margin-bottom:.75rem">${p.source}</div>
        <h3 style="font-family:'Syne',sans-serif; font-size:1rem; font-weight:700; margin-bottom:.4rem">${p.title}</h3>
        <p style="font-size:.85rem; color:var(--muted); margin-bottom:.75rem">${p.description}</p>
        <div class="skill-tags">${(p.skills_required || []).map(s => `<span class="skill-tag">${s}</span>`).join('')}</div>
      </div>`).join('');
  } catch (e) {
    renderProjects(filter);
  }
}

async function renderProfileFromAPI() {
  if (!state.loggedIn) { renderProfile(); return; }
  const userId = localStorage.getItem('user_id');
  if (!userId)  { renderProfile(); return; }

  try {
    const profile = await apiCall('/api/profile/me');
    if (profile.major)              { const el = document.getElementById('pMajor');   if (el) el.value = profile.major; }
    if (profile.availability_hours) { const el = document.getElementById('pAvail');   if (el) el.value = profile.availability_hours; }
    if (profile.bio)                { const el = document.getElementById('pBio');     if (el) el.value = profile.bio; }
    if (profile.github_url)         { const el = document.getElementById('pGithub');  if (el) el.value = profile.github_url; }
    if (profile.courses)            { const el = document.getElementById('pCourses'); if (el) el.value = profile.courses.join(', '); }
    if (profile.skills) {
      DEMO_SKILLS = profile.skills;
    }
    renderProfile();
  } catch (e) {
    renderProfile();
  }
}

async function sendChat() {
  const input = document.getElementById('chatInput');
  const msg   = input.value.trim();
  if (!msg) return;
  input.value = '';
  addMessage('user', msg);
  state.chatHistory.push({ role: 'user', content: msg });

  const typingId = 'typing-' + Date.now();
  const chatMessages = document.getElementById('chatMessages');
  const div = document.createElement('div');
  div.className = 'msg ai';
  div.id = typingId;
  div.innerHTML = '<div class="msg-avatar">Adv</div><div class="msg-bubble"><div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div></div>';
  chatMessages.appendChild(div);
  chatMessages.scrollTop = chatMessages.scrollHeight;

  try {
    const data = await apiCall('/api/advisor/chat', {
      method: 'POST',
      body: JSON.stringify({ message: msg, conversation_history: state.chatHistory.slice(-6) })
    });
    document.getElementById(typingId)?.remove();
    const reply = data.reply || 'I couldn\'t process that right now.';
    addMessage('ai', reply);
    state.chatHistory.push({ role: 'assistant', content: reply });
  } catch (e) {
    document.getElementById(typingId)?.remove();
    const fallback = getAdvisorReply(msg);
    addMessage('ai', fallback);
    state.chatHistory.push({ role: 'assistant', content: fallback });
  }
}

// init — restore session from localStorage if token exists
async function init() {
  const token = localStorage.getItem('token');
  if (token) {
    try {
      const me = await apiCall('/api/auth/me');
      state.loggedIn = true;
      state.user = me;
      localStorage.setItem('user_name', me.full_name || me.email.split('@')[0]);
      localStorage.setItem('email',     me.email);
      localStorage.setItem('user_id',   me.email);
      updateNavAuth();
      showPage('home');
      return;
    } catch (e) {
      // token is stale, clear it and show login
      localStorage.removeItem('token');
    }
  }
  updateNavAuth();
  showPage('login');
}

init();