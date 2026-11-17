import hashlib
import hmac
import os
from pathlib import Path
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.exception_handlers import http_exception_handler
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from db import get_db, lifespan

app = FastAPI(lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=os.getenv('SESSION_SECRET', 'local-demo-change-this-key'), session_cookie='submission_review_session', same_site='lax')
templates = Jinja2Templates(directory=str(Path(__file__).parent / 'templates'))


@app.middleware('http')
async def prevent_stale_pages(request: Request, call_next):
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    return response


@app.exception_handler(HTTPException)
async def show_http_error(request: Request, exc: HTTPException):
    if exc.status_code == 403:
        return templates.TemplateResponse(
            request=request, name='forbidden.html',
            context={'user': request.session.get('user')}, status_code=403,
        )
    return await http_exception_handler(request, exc)

def hash_password(password, salt=None):
    salt = salt or os.urandom(16).hex()
    digest = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 200000).hex()
    return f'{salt}${digest}'


def verify_password(password, stored):
    try:
        salt, _ = stored.split('$', 1)
        return hmac.compare_digest(hash_password(password, salt), stored)
    except (ValueError, TypeError):
        return False


def redirect(url):
    return RedirectResponse(url, status_code=303)


def require_role(request, role):
    user = request.session.get('user')
    if not user:
        return None
    if user['role'] != role:
        raise HTTPException(status_code=403, detail='沒有權限')
    return user


def page(request, name, **context):
    return templates.TemplateResponse(request=request, name=name, context=context)


@app.get('/')
async def home(request: Request):
    user = request.session.get('user')
    return redirect('/' + user['role'] if user else '/login')


@app.get('/login')
async def login_page(request: Request):
    return page(request, 'login.html')


@app.post('/login')
async def login(request: Request, username: str = Form(...), password: str = Form(...), db=Depends(get_db)):
    cursor = await db.execute('SELECT * FROM users WHERE username = %s', (username,))
    user = await cursor.fetchone()
    if not user or not verify_password(password, user['password_hash']):
        return templates.TemplateResponse(request=request, name='login.html', context={'error': '帳號或密碼錯誤'}, status_code=401)
    request.session.clear()
    request.session['user'] = {'id': user['id'], 'name': user['name'], 'role': user['role']}
    return redirect('/' + user['role'])


@app.post('/logout')
async def logout(request: Request):
    request.session.clear()
    return redirect('/login')


@app.get('/author')
async def author_list(request: Request, db=Depends(get_db)):
    user = require_role(request, 'author')
    if not user: return redirect('/login')
    cursor = await db.execute('SELECT * FROM submissions WHERE author_id = %s ORDER BY id DESC', (user['id'],))
    return page(request, 'author.html', user=user, submissions=await cursor.fetchall())


@app.get('/author/new')
async def new_form(request: Request):
    if not require_role(request, 'author'): return redirect('/login')
    return page(request, 'form.html', submission=None)


@app.post('/author/new')
async def create_submission(request: Request, category: str = Form(...), title: str = Form(...), content: str = Form(...), db=Depends(get_db)):
    user = require_role(request, 'author')
    if not user: return redirect('/login')
    if not all(value.strip() for value in (category, title, content)): raise HTTPException(400, '請填寫所有欄位')
    await db.execute('INSERT INTO submissions (author_id, category, title, content, status) VALUES (%s, %s, %s, %s, %s)', (user['id'], category.strip(), title.strip(), content.strip(), '編輯中'))
    await db.commit()
    return redirect('/author')


@app.get('/author/{submission_id}/edit')
async def edit_form(submission_id: int, request: Request, db=Depends(get_db)):
    user = require_role(request, 'author')
    if not user: return redirect('/login')
    cursor = await db.execute('SELECT * FROM submissions WHERE id = %s AND author_id = %s AND status = %s', (submission_id, user['id'], '編輯中'))
    submission = await cursor.fetchone()
    if not submission: raise HTTPException(404, '找不到可編輯的稿件')
    return page(request, 'form.html', submission=submission)


@app.post('/author/{submission_id}/edit')
async def edit_submission(submission_id: int, request: Request, category: str = Form(...), title: str = Form(...), content: str = Form(...), db=Depends(get_db)):
    user = require_role(request, 'author')
    if not user: return redirect('/login')
    if not all(value.strip() for value in (category, title, content)): raise HTTPException(400, '請填寫所有欄位')
    cursor = await db.execute('UPDATE submissions SET category = %s, title = %s, content = %s WHERE id = %s AND author_id = %s AND status = %s', (category.strip(), title.strip(), content.strip(), submission_id, user['id'], '編輯中'))
    if not cursor.rowcount: raise HTTPException(404, '找不到可編輯的稿件')
    await db.commit()
    return redirect('/author')


@app.post('/author/{submission_id}/delete')
async def delete_submission(submission_id: int, request: Request, db=Depends(get_db)):
    user = require_role(request, 'author')
    if not user: return redirect('/login')
    cursor = await db.execute('DELETE FROM submissions WHERE id = %s AND author_id = %s AND status = %s', (submission_id, user['id'], '編輯中'))
    if not cursor.rowcount: raise HTTPException(404, '找不到可刪除的稿件')
    await db.commit()
    return redirect('/author')


@app.post('/author/{submission_id}/submit')
async def submit_submission(submission_id: int, request: Request, db=Depends(get_db)):
    user = require_role(request, 'author')
    if not user: return redirect('/login')
    cursor = await db.execute('UPDATE submissions SET status = %s WHERE id = %s AND author_id = %s AND status = %s', ('審查中', submission_id, user['id'], '編輯中'))
    if not cursor.rowcount: raise HTTPException(404, '找不到可送出的稿件')
    await db.commit()
    return redirect('/author')


@app.get('/editor')
async def editor_list(request: Request, db=Depends(get_db)):
    user = require_role(request, 'editor')
    if not user: return redirect('/login')
    cursor = await db.execute('SELECT submissions.*, users.name AS author_name FROM submissions JOIN users ON users.id = submissions.author_id WHERE submissions.status = %s ORDER BY submissions.id DESC', ('審查中',))
    return page(request, 'editor.html', user=user, submissions=await cursor.fetchall())


@app.get('/editor/{submission_id}')
async def editor_detail(submission_id: int, request: Request, db=Depends(get_db)):
    if not require_role(request, 'editor'): return redirect('/login')
    cursor = await db.execute('SELECT submissions.*, users.name AS author_name FROM submissions JOIN users ON users.id = submissions.author_id WHERE submissions.id = %s AND submissions.status = %s', (submission_id, '審查中'))
    submission = await cursor.fetchone()
    if not submission: raise HTTPException(404, '找不到待審稿件')
    return page(request, 'detail.html', submission=submission)


@app.post('/editor/{submission_id}/{decision}')
async def review(submission_id: int, decision: str, request: Request, db=Depends(get_db)):
    if not require_role(request, 'editor'): return redirect('/login')
    if decision not in ('approve', 'return'): raise HTTPException(404, '無此操作')
    status = '已通過' if decision == 'approve' else '編輯中'
    cursor = await db.execute('UPDATE submissions SET status = %s WHERE id = %s AND status = %s', (status, submission_id, '審查中'))
    if not cursor.rowcount: raise HTTPException(404, '找不到待審稿件')
    await db.commit()
    return redirect('/editor')
