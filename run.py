import os
import uuid
import json
import time
from datetime import datetime
from keyword_template import KeyWordTemplate
from flask import g, Flask, render_template, request, current_app, send_file, redirect, url_for, jsonify, session, Blueprint, flash, abort, make_response
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from flask_babel import Babel, gettext, ngettext
from chat_robot import ChatRobot


login_manager = LoginManager()
app = Flask(__name__)  # , url_prefix='/<lang_code>')

# In order to use session in flask you need to set the secret key in your application settings. secret key is a random key used to encrypt your cookies and save send them to the browser.
app.config['SECRET_KEY'] = uuid.uuid4().hex
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + \
    os.getcwd() + '/med.db'  # 数据库URI，根据实际情况修改
db = SQLAlchemy(app)

app.config['LANGUAGES'] = {
    'en': 'English',
    'zh': 'Chinese',
    'ja': 'Japanese'
}

babel = Babel(app)


@app.route('/language/<language>')
def set_language(language=None):
    response = make_response(redirect(request.referrer or '/'))
    response.set_cookie('lang', language)
    return response

# @babel.localeselector


def get_locale():
    return request.cookies.get('lang', 'en')


babel.init_app(app, locale_selector=get_locale)


login_manager.login_view = 'auth.login'
login_manager.init_app(app)


# a mixin is a special kind of multiple inheritance that provides limited functionality and polymorphic resonance for a child class.
class User(UserMixin, db.Model):
    __tablename__ = 'user'
    # primary keys are required by SQLAlchemy
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))


class SurveyResult(db.Model):
    __tablename__ = 'survey_result' 
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    user_email = db.Column(db.String(100), db.ForeignKey('user.email'), nullable=True)
    json_data = db.Column(db.Text, nullable=False)  # 使用 Text 类型存储 JSON 字符串
    results = db.Column(db.Text, nullable=False)  # 新增字段存储结果
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SurveyResult user_email={self.user_email}, json_data="{self.json_data}">'

    # 获取关联的用户对象
    @property
    def user(self):
        return User.query.get(self.user_email)


@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    return User.query.get(int(user_id))


# blueprint for auth routes in our app
auth = Blueprint('auth', __name__)


@auth.route('/signup')
def signup():
    return render_template('signup.html')


@auth.route('/signup', methods=['POST'])
def signup_post():
    # code to validate and add user to database goes here
    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')

    # if this returns a user, then the email already exists in database
    user = User.query.filter_by(email=email).first()

    if user:  # if a user is found, we want to redirect back to signup page so user can try again
        flash('Email address already exists')
        return redirect(url_for('auth.signup'))

    # create a new user with the form data. Hash the password so the plaintext version isn't saved.
    new_user = User(email=email, name=name, password=generate_password_hash(
        password, method='pbkdf2:sha256'))

    # add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('auth.login'))


@auth.route('/login')
def login():
    return render_template('login.html')


@auth.route('/login', methods=['POST'])
def login_post():
    # login code goes here
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(email=email).first()

    # check if the user actually exists
    # take the user-supplied password, hash it, and compare it to the hashed password in the database
    if not user or not check_password_hash(user.password, password):
        flash(gettext('Please check your login details and try again.'))
        # if the user doesn't exist or password is wrong, reload the page
        return redirect(url_for('auth.login'))

    # if the above check passes, then we know the user has the right credentials
    login_user(user, remember=remember)  # save session
    return redirect(url_for('index'))


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


app.register_blueprint(auth)


@app.route("/")
@login_required
def index():
    # g.lang_code = request.accept_languages.best_match(['en', 'zh', 'ja'])
    # send_file("templates/index.html")
    try:
        user_data = SurveyResult.query.filter_by(user_email=current_user.email).all()
        for entry in user_data:
            entry.questionnaire_data = json.loads(entry.json_data)  # 解析 JSON 数据
    except Exception as e:
        print(f"Error reading data: {e}")
        user_data = []
    return render_template('index.html', name=current_user.name, data=user_data)


@app.route("/chat")
@login_required
def chat():
    return send_file("templates/chat.html")


@app.route("/scale", methods=['GET', 'POST'])
@login_required
def scale():
    if request.method == 'POST':
        data = request.json.get('questionnaireData')
        user_id = current_user.id
        json_data = json.dumps(data)

        result = SurveyResult(
            user_id=user_id, 
            user_email=current_user.email, 
            json_data=json_data,
            results=json.dumps(data.get('results')),
            created_at=datetime.utcnow()
            )

        db.session.add(result)
        db.session.commit()

        flash('Survey submitted successfully.')
        return jsonify(success=True)
    record_id = request.args.get('id')
    record = None
    if record_id:
        record = SurveyResult.query.get(record_id)
    return render_template("scale.html", record=record)


CORS(app)  # Cross-Origin Resource Sharing
ans = 'I dont understand. \nPlease contact a doctor.'

keyword = KeyWordTemplate()
handler = ChatRobot()


@app.route('/question', methods=['POST'])
@login_required
def controller():
    data = request.get_data()
    json_data = json.loads(data.decode("utf-8"))
    question = json_data.get('question')

    print('\n')
    print(question)
    return robot(question)


def robot(question):
    answer = handler.chat_main(question)
    if ans == answer:
        answer = keyword.getTempalte(question)
    if answer == None:
        answer = ans
    ans_dict = dict()
    ans_dict['answer'] = answer

    ans_json = json.dumps(ans_dict)
    print(answer)
    print('\n')
    return ans_json


# 体质类型及其对应的问题数量
constitution_questions = {
    '阳虚质': 7,
    '阴虚质': 8,
    '气虚质': 8,
    '痰湿质': 8,
    '湿热质': 7,
    '血瘀质': 7,
    '特禀质': 7,
    '气郁质': 7,
    '平和质': 8,
}

data_file = 'survey_data.json'


@app.route("/survey", methods=['POST'])
@login_required
def submit_survey():
    data = request.json
    timestamp_str = data.get('timestamp')
    # 将字符串转换为 datetime 对象
    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M')
    new_record = SurveyResult(
        user_id = current_user.id,
        # 'id': generate_unique_id(),  # 每次生成新的id
        user_email = data.get('userEmail'),
        json_data = json.dumps(data.get('questionnaireData')),
        results = json.dumps(data.get('results')),
        created_at = timestamp
    )
    print(new_record)
    try:
        db.session.add(new_record)
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        print(f"Error saving data: {e}")
        db.session.rollback()
        return jsonify(success=False), 500


@app.route('/view-survey-results', methods=['GET'])
def view_survey_results():
    # data = request.json.get('questionnaireData')
    # user_id = current_user.id
    # json_data = json.dumps(data)
    # result = SurveyResult(user_id=user_id, json_data=json_data)
    # 查询数据库中的所有问卷结果
    survey_results = SurveyResult.query.all()
    # 将查询结果传递给模板
    return render_template('view_survey_results.html', survey_results=survey_results)


@app.route('/get_survey_data', methods=['GET'])
@login_required
def get_survey_data():
    record_id = request.args.get('id')
    record = SurveyResult.query.get(record_id)
    if record:
        data = {
            'id': record.id,
            'user_email': record.user_email,
            'questionnaire_data': json.loads(record.json_data),
            'results': json.loads(record.results),
            'created_at': record.created_at
        }
        print(data)
        return jsonify(data)
    else:
        return jsonify({'error': 'Record not found'}), 404


def generate_unique_id():
    return str(int(time.time() * 1000))  # 时间戳生成唯一ID


if __name__ == '__main__':

    # create_all() creates foreign key constraints between tables usually inline with the table definition itself, and for this reason it also generates the tables in order of their dependency.
    with app.app_context():
        db.create_all()
        # 添加一个初始用户进行测试
        if not User.query.filter_by(email='test@example.com').first():
            new_user = User(email='test@example.com', name='Test User', password=generate_password_hash('password', method='pbkdf2:sha256'))
            db.session.add(new_user)
            db.session.commit()

    app.run(host='localhost', port=5001, debug=True)
