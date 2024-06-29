import os
import uuid
import json
from datetime import datetime
from keyword_template import KeyWordTemplate
from flask import Flask, render_template, request, current_app, send_file,redirect, url_for,jsonify, session, Blueprint, flash
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from chat_robot import ChatRobot

login_manager = LoginManager()
app = Flask(__name__)

# In order to use session in flask you need to set the secret key in your application settings. secret key is a random key used to encrypt your cookies and save send them to the browser.
app.config['SECRET_KEY'] = uuid.uuid4().hex
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.getcwd() + '/med.db'  # 数据库URI，根据实际情况修改
db = SQLAlchemy(app)


class User(UserMixin, db.Model): # a mixin is a special kind of multiple inheritance that provides limited functionality and polymorphic resonance for a child class.
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))

class SurveyResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    json_data = db.Column(db.Text, nullable=False)  # 使用 Text 类型存储 JSON 字符串
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SurveyResult user_id={self.user_id}, json_data="{self.json_data}">'

    # 获取关联的用户对象
    @property
    def user(self):
        return User.query.get(self.user_id)
    
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

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

    user = User.query.filter_by(email=email).first() # if this returns a user, then the email already exists in database

    if user: # if a user is found, we want to redirect back to signup page so user can try again
        flash('Email address already exists')
        return redirect(url_for('auth.signup'))

    # create a new user with the form data. Hash the password so the plaintext version isn't saved.
    new_user = User(email=email, name=name, password=generate_password_hash(password, method='pbkdf2:sha256'))

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
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login')) # if the user doesn't exist or password is wrong, reload the page

    # if the above check passes, then we know the user has the right credentials
    login_user(user, remember=remember) # save session
    return redirect(url_for('profile'))

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

app.register_blueprint(auth)

'''
# blueprint for non-auth parts of app
main = Blueprint('main', __name__)

app.register_blueprint(main)
'''

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', name=current_user.name)


CORS(app)# Cross-Origin Resource Sharing
ans = 'I dont understand. \nPlease contact a doctor.'

keyword = KeyWordTemplate()
handler = ChatRobot()


@app.route('/question', methods=['POST'])
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

@app.route("/survey", methods=['POST'])
def submit_survey():
    # 假设 data 是从前端接收到的包含问卷数据的字典
    data = request.json
    user_id = session.get('user_id')  # 获取当前登录用户的ID

    # 将问卷数据转换为JSON字符串
    json_data = json.dumps(data)

    # 创建新的 SurveyResult 实例
    result = SurveyResult(user_id=user_id, json_data=json_data)

    # 添加到数据库会话
    db.session.add(result)
    db.session.commit()

    return jsonify({"result": "Survey submitted successfully."}), 200


@app.route('/view-survey-results', methods=['GET'])
def view_survey_results():
    # 查询数据库中的所有问卷结果
    survey_results = SurveyResult.query.all()
    # 将查询结果传递给模板
    return render_template('view_survey_results.html', survey_results=survey_results)


@app.route("/", methods=['GET', 'POST'])
def index():
    # return current_app.send_static_file("templates/index.html")
    return render_template('index.html') #  send_file("templates/index.html")


@app.route("/constitution", methods=['GET', 'POST'])
@login_required
def constitution():
    return send_file("templates/constitution.html")

if __name__ == '__main__':

    # create_all() creates foreign key constraints between tables usually inline with the table definition itself, and for this reason it also generates the tables in order of their dependency. 
    with app.app_context():
        db.create_all()
        
    app.run(host='localhost',port=5000,debug=True)
