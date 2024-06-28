import os
from chat_robot import ChatRobot
from keyword_template import KeyWordTemplate
from flask import Flask, render_template, request, current_app, send_file,redirect, url_for,jsonify
from flask_cors import CORS
import json
import sqlite3
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from flask import session  # 确保导入了 session
from flask import flash
from datetime import datetime
app = Flask(__name__)

# app.config['SECRET_KEY'] = '123456'  # 设置一个安全密钥用于保护会话
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.getcwd() + '/med.db'  # 数据库URI，根据实际情况修改
db = SQLAlchemy(app)

class user(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120))
    password = db.Column(db.String(80))

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

'''
@app.route("/")
def index1():
    return render_template("index1.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        uname = request.form["uname"]
        passw = request.form["passw"]
        
        login = user.query.filter_by(username=uname, password=passw).first()
        if login is not None:
            session['user_id'] = login.id  # 将 user_id 存储在 session 中
            return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        uname = request.form['uname']
        mail = request.form['mail']
        passw = request.form['passw']

        register = user(username = uname, email = mail, password = passw)
        db.session.add(register)
        db.session.commit()

        return redirect(url_for("login"))
    return render_template("register.html")
'''

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
    return send_file("templates/index.html")


@app.route("/constitution", methods=['GET', 'POST'])
def constitution():
    return send_file("templates/constitution.html")

if __name__ == '__main__':

    # create_all() creates foreign key constraints between tables usually inline with the table definition itself, and for this reason it also generates the tables in order of their dependency. 
    with app.app_context():
        db.create_all()
        
    app.run(host='localhost',port=5000,debug=True)
