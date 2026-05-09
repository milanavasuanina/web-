import datetime
from flask import Flask, render_template, request, redirect, url_for, make_response
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, IntegerField
from wtforms.validators import DataRequired, EqualTo, Length, ValidationError
import sqlalchemy
import sqlalchemy.orm as orm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'

SqlAlchemyBase = orm.declarative_base()
__factory = None

def global_init(db_file):
    global __factory
    if __factory:
        return
    conn_str = f'sqlite:///{db_file}?check_same_thread=False'
    engine = sqlalchemy.create_engine(conn_str, echo=False)
    __factory = orm.sessionmaker(bind=engine)
    SqlAlchemyBase.metadata.create_all(engine)

def create_session():
    global __factory
    return __factory()

class User(SqlAlchemyBase):
    __tablename__ = 'users'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    email = sqlalchemy.Column(sqlalchemy.String, index=True, unique=True, nullable=True)
    password = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    created_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)

class Goal(SqlAlchemyBase):
    __tablename__ = 'goals'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    points = sqlalchemy.Column(sqlalchemy.Integer, default=0)
    is_completed = sqlalchemy.Column(sqlalchemy.Boolean, default=False)
    created_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)
    completed_date = sqlalchemy.Column(sqlalchemy.DateTime, nullable=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('users.id'))

class RegisterForm(FlaskForm):
    name = StringField('Имя', validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField('Email', validators=[DataRequired(), Length(max=100)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=4)])
    confirm = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

    def validate_email(self, field):
        if '@' not in field.data or '.' not in field.data.split('@')[-1]:
            raise ValidationError('Введите корректный email')
        sess = create_session()
        user = sess.query(User).filter(User.email == field.data).first()
        sess.close()
        if user:
            raise ValidationError('Email уже используется')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class GoalForm(FlaskForm):
    title = StringField('Название цели', validators=[DataRequired()])
    points = IntegerField('Баллы', default=0)
    submit = SubmitField('Сохранить')

def get_current_user():
    user_id = request.cookies.get('user_id')
    if not user_id:
        return None
    sess = create_session()
    user = sess.query(User).filter(User.id == int(user_id)).first()
    sess.close()
    return user

def get_user_total_points(user_id):
    sess = create_session()
    total = sess.query(sqlalchemy.func.sum(Goal.points)).filter(Goal.user_id == user_id, Goal.is_completed == True).scalar()
    sess.close()
    return total or 0

@app.route('/')
def index():
    user = get_current_user()
    return render_template('index.html', user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User()
        user.name = form.name.data
        user.email = form.email.data
        user.password = form.password.data
        sess = create_session()
        sess.add(user)
        sess.commit()
        sess.close()
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        sess = create_session()
        user = sess.query(User).filter(User.email == form.email.data).first()
        sess.close()
        if user and user.password == form.password.data:
            resp = make_response(redirect(url_for('profile')))
            resp.set_cookie('user_id', str(user.id), max_age=3600)
            return resp
    return render_template('login.html', form=form)

@app.route('/profile')
def profile():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    points = get_user_total_points(user.id)
    sess = create_session()
    completed_count = sess.query(Goal).filter(Goal.user_id == user.id, Goal.is_completed == True).count()
    sess.close()
    return render_template('profile.html', user=user, points=points, completed_count=completed_count)

@app.route('/logout')
def logout():
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('user_id', '', expires=0)
    return resp

@app.route('/goals')
def list_goals():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    sess = create_session()
    my_goals = sess.query(Goal).filter(Goal.user_id == user.id).all()
    sess.close()
    return render_template('goals.html', my_goals=my_goals, user=user)

@app.route('/goals/add', methods=['GET', 'POST'])
def add_goal():
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    form = GoalForm()
    if form.validate_on_submit():
        goal = Goal(title=form.title.data, points=form.points.data, user_id=user.id)
        sess = create_session()
        sess.add(goal)
        sess.commit()
        sess.close()
        return redirect(url_for('list_goals'))
    return render_template('goal_form.html', form=form, action='Добавить')

@app.route('/goals/edit/<int:goal_id>', methods=['GET', 'POST'])
def edit_goal(goal_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    sess = create_session()
    goal = sess.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if not goal:
        sess.close()
        return redirect(url_for('list_goals'))
    form = GoalForm(obj=goal)
    if form.validate_on_submit():
        goal.title = form.title.data
        goal.points = form.points.data
        sess.commit()
        sess.close()
        return redirect(url_for('list_goals'))
    sess.close()
    return render_template('goal_form.html', form=form, action='Редактировать')

@app.route('/goals/complete/<int:goal_id>')
def complete_goal(goal_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    sess = create_session()
    goal = sess.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if goal and not goal.is_completed:
        goal.is_completed = True
        goal.completed_date = datetime.datetime.now()
        sess.commit()
    sess.close()
    return redirect(url_for('list_goals'))

@app.route('/goals/delete/<int:goal_id>')
def delete_goal(goal_id):
    user = get_current_user()
    if not user:
        return redirect(url_for('login'))
    sess = create_session()
    goal = sess.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if goal:
        sess.delete(goal)
        sess.commit()
    sess.close()
    return redirect(url_for('list_goals'))

def main():
    global_init("db/blogs.db")
    app.run(port=8080, host='127.0.0.1', debug=True)

if __name__ == '__main__':
    main()
