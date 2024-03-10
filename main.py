# coding=gbk
from chat_robot import ChatRobot
from keyword_template import KeyWordTemplate
from flask import Flask
from flask_cors import CORS
from flask import request
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

if __name__ == '__main__':
    app.run(host='localhost',port=5000,debug=True)




