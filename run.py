# -*- coding: utf-8 -*-
from chat_robot import ChatRobot
from keyword_template import KeyWordTemplate
from flask import Flask, render_template, request, current_app, send_file,redirect, url_for,jsonify
from flask_cors import CORS
import json
app = Flask(__name__)

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
    # 接收数据
    print(request.json)
    data = request.json

    if not data:  # 检查数据是否为空
        return jsonify({"error": "No data received."}), 400

    results = {}

    # 处理数据
    for constitution, scores in data.items():
        if constitution not in constitution_questions:
            return jsonify({"error": "Invalid constitution type."}), 400  # 无效的体质类型
        questions_count = constitution_questions[constitution]
        original_score = sum(scores)  # 计算原始分
        # 计算转化分
        transformed_score = ((original_score - questions_count) / (questions_count * 4)) * 100
        results[constitution] = transformed_score

    # 检查结果字典是否为空
    if not results:
        return jsonify({"error": "No results to determine constitution."}), 400

    # 根据转化分判定体质类型
    final_result, status_code = determine_constitution(results)
    return jsonify({"result": final_result}), status_code

def determine_constitution(results):
    # 如果results字典为空，返回默认结果
    if not results:
        return "平和质", 200  # 假设默认判定为平和质

    # 首先找出转化分最高的体质类型
    max_transformed_score = max(results.values())
    max_constitution = max(results, key=results.get)

    # 检查是否为平和质
    if max_constitution == '平和质' and max_transformed_score >= 60:
        # 如果平和质转化分≥60分，且其他体质转化分均<40分，则判定为平和质
        if all(score < 40 for score in results.values() if results.get(results) != '平和质'):
            return '平和质', 200
        else:
            # 否则，选择转化分第二高的体质类型
            second_max_constitution = max(results, key=results.get, default='平和质')
            return second_max_constitution, 200
    else:
        # 如果不是平和质，直接返回转化分最高的体质类型
        return max_constitution, 200


@app.route("/", methods=['GET', 'POST'])
def index():
    # return current_app.send_static_file("templates/index.html")
    return send_file("templates/index.html")


@app.route("/constitution", methods=['GET', 'POST'])
def constitution():
    return send_file("templates/constitution.html")

if __name__ == '__main__':
    app.run(host='localhost',port=5000,debug=True)




