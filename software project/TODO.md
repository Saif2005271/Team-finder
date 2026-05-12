# Team-Finder Frontend-Backend Integration TODO

## Plan
Wire the frontend (`index.html`) to the FastAPI backend (`app.py`) to fix the 403 Forbidden errors and make the app fully functional end-to-end.

---

## Steps

- [ ] **Step 1**: Add `API_BASE`, `apiCall()` helper, and auth state management to `index.html`
- [ ] **Step 2**: Wire `doRegister()` → `POST /api/auth/register`
- [ ] **Step 3**: Wire `doLogin()` → `POST /api/auth/login`
- [ ] **Step 4**: Wire `doLogout()` to clear `localStorage` token and reset UI
- [ ] **Step 5**: Wire `saveProfile()` → `POST /api/profile`
- [ ] **Step 6**: Wire `renderProfile()` → `GET /api/profile/{user_id}` on load
- [ ] **Step 7**: Wire `renderMatches()` → `POST /api/match`
- [ ] **Step 8**: Wire `renderProjects()` → `GET /api/projects`
- [ ] **Step 9**: Wire `sendChat()` → `POST /api/ai/chat`
- [ ] **Step 10**: Wire exam `openExam()` → `GET /api/skills/exam/{skill}` and `submitExam()` → `POST /api/skills/exam`
- [ ] **Step 11**: Add `init()` on page load to validate token and fetch current user/profile
- [ ] **Step 12**: Update `app.py` to serve `index.html` at root `/` so everything runs on one port
- [ ] **Step 13**: Restart server and test full flow

