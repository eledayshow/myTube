import os
import shutil
import subprocess
from pathlib import Path
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from databaser import Databaser

app = FastAPI()

# Путь к ffmpeg
FFMPEG_PATH = r"C:\ЕБАНОЕ ГОВНО КОТОРОЕ ВЕЗДЕ НУЖНО СУКА БЛЯТЬ КАК Я ЭТО НЕ НАВИЖУ СУКА\bin\ffmpeg.exe"

# Секретный ключ для сессий
SECRET_KEY = "your-secret-key-change-this-in-production"
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

db = Databaser()

# Создаем необходимые папки
Path("static/videos").mkdir(parents=True, exist_ok=True)
Path("static/previews").mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


def get_current_user(request: Request):
    """Получить текущего пользователя из сессии"""
    user_id = request.session.get("user_id")
    if user_id:
        return db.get_user_by_id(user_id)
    return None


def convert_to_webm(input_path: str, output_path: str):
    """Конвертация видео в webm через ffmpeg"""
    try:
        cmd = [
            FFMPEG_PATH,
            '-i', input_path,
            '-c:v', 'libvpx-vp9',
            '-crf', '30',
            '-b:v', '1M',
            '-c:a', 'libopus',
            '-y',
            output_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True
        else:
            print(f"FFmpeg error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("FFmpeg не найден, пропускаем конвертацию")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


def generate_thumbnail(video_path: str, thumbnail_path: str):
    """Генерация превью из видео"""
    try:
        cmd = [
            FFMPEG_PATH,
            '-i', video_path,
            '-ss', '00:00:01',
            '-vframes', '1',
            '-vf', 'scale=320:-1',
            '-y',
            thumbnail_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return True
        else:
            print(f"FFmpeg error: {result.stderr}")
            return False
    except FileNotFoundError:
        print("FFmpeg не найден, пропускаем создание превью")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


@app.get("/", response_class=HTMLResponse)
async def root(request: Request, search: str = None):
    videos = db.get_videos(search)
    user = get_current_user(request)
    return templates.TemplateResponse("index.html", {"request": request, "videos": videos, "user": user, "search": search or ""})


@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register")
async def register(request: Request, username: str = Form(...), password: str = Form(...)):
    if len(username) < 3:
        return JSONResponse({"error": "Имя пользователя должно быть не менее 3 символов"}, status_code=400)
    
    user_id = db.create_user(username, password)
    
    if user_id is None:
        return JSONResponse({"error": "Пользователь с таким именем уже существует"}, status_code=400)
    
    request.session["user_id"] = user_id
    return JSONResponse({"status": "ok", "redirect": "/"})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    user = get_current_user(request)
    if user:
        return RedirectResponse(url="/", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = db.get_user_by_username(username)
    
    if not user or not db.verify_password(password, user["password"]):
        return JSONResponse({"error": "Неверное имя пользователя или пароль"}, status_code=400)
    
    request.session["user_id"] = user["id"]
    return JSONResponse({"status": "ok", "redirect": "/"})


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@app.get("/upload", response_class=HTMLResponse)
async def upload_page(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("upload.html", {"request": request, "user": user})


@app.post("/upload")
async def upload_video(
    request: Request,
    video: UploadFile = File(...),
    name: str = Form(...),
    desc: str = Form(...)
):
    """Загрузка видео"""
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Необходима авторизация"}, status_code=401)
    
    try:
        # Проверка типа файла
        allowed_extensions = {'.mp4', '.webm', '.avi', '.mov', '.mkv'}
        file_extension = Path(video.filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            return JSONResponse({"error": "Неподдерживаемый формат. Используйте: mp4, webm, avi, mov, mkv"}, status_code=400)
        
        # Используем имя пользователя как имя автора
        author_name = user["username"]
        
        # Добавляем запись в БД
        video_id = db.add_video(name, desc, author_name, user["id"])
        
        # Сохраняем видео напрямую без конвертации
        video_path = f"static/videos/{video_id}{file_extension}"
        with open(video_path, "wb") as buffer:
            shutil.copyfileobj(video.file, buffer)
        
        # Пытаемся сгенерировать превью в фоне (не блокируем ответ)
        thumbnail_path = f"static/previews/{video_id}.png"
        try:
            generate_thumbnail(video_path, thumbnail_path)
        except Exception as e:
            print(f"Не удалось создать превью: {e}")
        
        return JSONResponse(content={"status": "ok", "video_id": video_id})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/studio", response_class=HTMLResponse)
async def studio(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    videos = db.get_user_videos(user["id"])
    stats = db.get_user_stats(user["id"])
    
    return templates.TemplateResponse("studio.html", {
        "request": request,
        "user": user,
        "videos": videos,
        "stats": stats
    })


@app.get("/{video_id}", response_class=HTMLResponse)
async def video_page(request: Request, video_id: int):
    video = db.get_video(video_id)
    if video is None:
        return HTMLResponse(content="Видео не найдено", status_code=404)
    
    # Увеличиваем счетчик просмотров
    db.increment_view_count(video_id)
    
    # Определяем формат видео
    video_format = None
    video_dir = Path("static/videos")
    for file in video_dir.glob(f"{video_id}.*"):
        if not file.name.startswith("temp_"):
            video_format = file.suffix[1:]
            break
    
    video["video_format"] = video_format
    user = get_current_user(request)
    
    # Получаем реакцию пользователя на это видео
    user_reaction = None
    if user:
        user_reaction = db.get_user_reaction(user["id"], video_id)
    
    # Получаем комментарии
    comments = db.get_comments(video_id)
    
    return templates.TemplateResponse("video_page.html", {
        "request": request, 
        "video": video, 
        "user": user,
        "user_reaction": user_reaction,
        "comments": comments
    })


@app.post("/{video_id}/like")
async def like_video(request: Request, video_id: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Необходима авторизация"}, status_code=401)
    
    db.like_video(video_id, user["id"])
    return JSONResponse(content={"status": "ok"})


@app.post("/{video_id}/dislike")
async def dislike_video(request: Request, video_id: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Необходима авторизация"}, status_code=401)
    
    db.dislike_video(video_id, user["id"])
    return JSONResponse(content={"status": "ok"})


@app.post("/{video_id}/comment")
async def add_comment(request: Request, video_id: int, text: str = Form(...)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Необходима авторизация"}, status_code=401)
    
    if not text.strip():
        return JSONResponse({"error": "Комментарий не может быть пустым"}, status_code=400)
    
    comment_id = db.add_comment(user["id"], video_id, text)
    return JSONResponse({"status": "ok", "comment_id": comment_id})


@app.delete("/comment/{comment_id}")
async def delete_comment(request: Request, comment_id: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Необходима авторизация"}, status_code=401)
    
    success = db.delete_comment(comment_id, user["id"])
    if not success:
        return JSONResponse({"error": "Комментарий не найден или вы не можете его удалить"}, status_code=403)
    
    return JSONResponse({"status": "ok"})


@app.get("/user/{user_id}", response_class=HTMLResponse)
async def user_profile(request: Request, user_id: int):
    profile_user = db.get_user_by_id(user_id)
    if not profile_user:
        return HTMLResponse(content="Пользователь не найден", status_code=404)
    
    current_user = get_current_user(request)
    videos = db.get_user_videos(user_id)
    stats = db.get_user_stats(user_id)
    
    is_subscribed = False
    if current_user and current_user["id"] != user_id:
        is_subscribed = db.is_subscribed(current_user["id"], user_id)
    
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "profile_user": profile_user,
        "user": current_user,
        "videos": videos,
        "stats": stats,
        "is_subscribed": is_subscribed,
        "is_own_profile": current_user and current_user["id"] == user_id
    })


@app.post("/user/{user_id}/subscribe")
async def subscribe(request: Request, user_id: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Необходима авторизация"}, status_code=401)
    
    if user["id"] == user_id:
        return JSONResponse({"error": "Нельзя подписаться на себя"}, status_code=400)
    
    db.subscribe(user["id"], user_id)
    return JSONResponse({"status": "ok"})


@app.post("/user/{user_id}/unsubscribe")
async def unsubscribe(request: Request, user_id: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Необходима авторизация"}, status_code=401)
    
    db.unsubscribe(user["id"], user_id)
    return JSONResponse({"status": "ok"})


@app.delete("/video/{video_id}")
async def delete_video(request: Request, video_id: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Необходима авторизация"}, status_code=401)
    
    success = db.delete_video(video_id, user["id"])
    if not success:
        return JSONResponse({"error": "Видео не найдено или вы не можете его удалить"}, status_code=403)
    
    # Удаляем файлы видео и превью
    import os
    video_dir = Path("static/videos")
    for file in video_dir.glob(f"{video_id}.*"):
        try:
            os.remove(file)
        except:
            pass
    
    preview_path = f"static/previews/{video_id}.png"
    if os.path.exists(preview_path):
        try:
            os.remove(preview_path)
        except:
            pass
    
    return JSONResponse({"status": "ok"})


@app.post("/video/{video_id}/edit")
async def edit_video(request: Request, video_id: int, name: str = Form(...), desc: str = Form(...)):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "Необходима авторизация"}, status_code=401)
    
    success = db.update_video(video_id, user["id"], name, desc)
    if not success:
        return JSONResponse({"error": "Видео не найдено или вы не можете его редактировать"}, status_code=403)
    
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)