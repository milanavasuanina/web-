from flask import Flask, request, redirect, url_for, make_response
from werkzeug.security import generate_password_hash, check_password_hash
import sqlalchemy
import sqlalchemy.orm as orm
from sqlalchemy.orm import Session
import datetime
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'

# Настройка базы данных
SqlAlchemyBase = orm.declarative_base()
__factory = None

def global_init(db_file):
    global __factory
    if __factory:
        return
    
    conn_str = f'sqlite:///{db_file}?check_same_thread=False'
    print(f"Подключение к базе данных: {conn_str}")
    
    engine = sqlalchemy.create_engine(conn_str, echo=False)
    __factory = orm.sessionmaker(bind=engine)
    
    # Создаём таблицы (если их нет)
    SqlAlchemyBase.metadata.create_all(engine)
    print("Таблицы созданы/проверены")

def create_session():
    global __factory
    return __factory()

# Модель пользователя
class User(SqlAlchemyBase):
    __tablename__ = 'users'
    
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    about = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    email = sqlalchemy.Column(sqlalchemy.String, index=True, unique=True, nullable=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    created_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)

@app.route('/')
def index():
    return '''
    <!doctype html>
    <html>
    <head>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <title>Трекер достижений</title>
    </head>
    <body>
        <div class="container mt-5 text-center">
            <h1>🏆 Трекер достижений</h1>
            <p>Ставьте цели, достигайте их и получайте баллы!</p>
            <div class="mt-4">
                <a href="/register" class="btn btn-primary me-2">Регистрация</a>
                <a href="/login" class="btn btn-success">Вход</a>
            </div>
        </div>
    </body>
    </html>
    '''

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        password_confirm = request.form.get('password_confirm')
        
        if password != password_confirm:
            return "Пароли не совпадают! <a href='/register'>Назад</a>"
        
        db_sess = create_session()
        
        user_exists = db_sess.query(User).filter(User.email == email).first()
        if user_exists:
            db_sess.close()
            return "Пользователь с таким email уже существует! <a href='/register'>Назад</a>"
        
        user = User()
        user.name = name
        user.email = email
        user.hashed_password = generate_password_hash(password)
        
        db_sess.add(user)
        db_sess.commit()
        db_sess.close()
        
        return redirect(url_for('login'))
    
    return '''
    <!doctype html>
    <html lang="ru">
    <head>
        <meta charset="utf-8">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <title>Регистрация</title>
    </head>
    <body>
        <div class="container mt-5">
            <h1 class="text-center">Регистрация</h1>
            <form method="post" class="mt-4">
                <div class="mb-3">
                    <label class="form-label">Имя</label>
                    <input type="text" class="form-control" name="name" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Email</label>
                    <input type="email" class="form-control" name="email" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Пароль</label>
                    <input type="password" class="form-control" name="password" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Подтвердите пароль</label>
                    <input type="password" class="form-control" name="password_confirm" required>
                </div>
                <button type="submit" class="btn btn-primary">Зарегистрироваться</button>
                <a href="/login" class="btn btn-link">Уже есть аккаунт? Войдите</a>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        db_sess = create_session()
        user = db_sess.query(User).filter(User.email == email).first()
        
        if user and check_password_hash(user.hashed_password, password):
            resp = make_response(redirect(url_for('profile')))
            resp.set_cookie('user_id', str(user.id), max_age=3600)
            db_sess.close()
            return resp
        else:
            db_sess.close()
            return "Неверный email или пароль! <a href='/login'>Назад</a>"
    
    return '''
    <!doctype html>
    <html lang="ru">
    <head>
        <meta charset="utf-8">
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <title>Вход</title>
    </head>
    <body>
        <div class="container mt-5">
            <h1 class="text-center">Вход</h1>
            <form method="post" class="mt-4">
                <div class="mb-3">
                    <label class="form-label">Email</label>
                    <input type="email" class="form-control" name="email" required>
                </div>
                <div class="mb-3">
                    <label class="form-label">Пароль</label>
                    <input type="password" class="form-control" name="password" required>
                </div>
                <button type="submit" class="btn btn-primary">Войти</button>
                <a href="/register" class="btn btn-link">Нет аккаунта? Зарегистрируйтесь</a>
            </form>
        </div>
    </body>
    </html>
    '''

@app.route('/profile')
def profile():
    user_id = request.cookies.get('user_id')
    if not user_id:
        return redirect(url_for('login'))
    
    db_sess = create_session()
    user = db_sess.query(User).filter(User.id == int(user_id)).first()
    db_sess.close()
    
    if not user:
        return redirect(url_for('login'))
    
    return f'''
    <!doctype html>
    <html>
    <head>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.0.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <title>Профиль</title>
    </head>
    <body>
        <div class="container mt-5">
            <h1>Профиль пользователя</h1>
            <p><strong>Имя:</strong> {user.name}</p>
            <p><strong>Email:</strong> {user.email}</p>
            <p><strong>Дата регистрации:</strong> {user.created_date}</p>
            <p><strong>Баллы:</strong> 0</p>
            <a href="/logout" class="btn btn-danger">Выйти</a>
        </div>
    </body>
    </html>
    '''

@app.route('/logout')
def logout():
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('user_id', '', expires=0)
    return resp

def main():
    global_init("db/blogs.db")
    app.run(port=8080, host='127.0.0.1', debug=True)

if __name__ == '__main__':
    main()