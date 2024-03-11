# About medbot

A medical KG chatbot based on neo4j  
This project is based on github.com/Groot-lin/MedicalChatbots. 

# Modules

* build_medicalgraph.py: 构建neo4j数据库
* question_analysis.py : 问题语义分析
* get_cql.py : 根据问题获取对应cql语句
* get_answer.py : 查询数据库并结合生成答案


# Install

1. pip install pyahocorasick flask_cors

2. 打开build_medicalgraph.py文件

修改信息包括neo4j数据库的ip地址,端口号,用户名和密码

运行最下面的main函数(数据量较大,可能会运行几十分钟)

3. neo4j.bat console

4. python run.py

5. 修改static目录下的index.html的第67行和95行,ip和端口改成与main.py中的一致

6. 在浏览器中打开 localhost:5000

# TODO

/constitution  
https://www.wjx.cn/m/3526126.aspx