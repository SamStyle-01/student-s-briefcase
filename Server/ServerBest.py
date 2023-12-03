from flask import Flask, request, jsonify, send_file
import sqlite3
import os
import zipfile
from joblib import load as load_it
from io import BytesIO
from bcrypt import hashpw

app = Flask(__name__)
salt = load_it("salt")

conn = sqlite3.connect("Users.db", check_same_thread=False)
cursor = conn.cursor()
active_users = set()


def get_all_files(directory):
    all_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            all_files.append(file_path)
    return all_files


@app.route('/download_all_files', methods=['GET'])
def download_all_files():
    # Получение списка всех файлов в директории и её поддиректориях
    directory_path = "for_download"
    files_list = get_all_files(directory_path)

    # Проверка, что директория не пуста
    if not files_list:
        return "Directory is empty", 404

    # Создание временного буфера для хранения ZIP-архива
    zip_buffer = BytesIO()

    # Создание ZIP-архива
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        for file_path in files_list:
            # arcname - позволяет добавить поддиректории в ZIP-архив
            zip_file.write(file_path, arcname=os.path.relpath(file_path, directory_path))

    # Перемещение указателя буфера в начало
    zip_buffer.seek(0)

    # Отправка ZIP-архива в ответ на запрос
    return send_file(zip_buffer, download_name='all_files.zip', as_attachment=True)


@app.route('/subs_proj', methods=['POST'])
def add_project():
    data = request.json
    name = data.get('name')
    username = data.get("username")

    if not name:
        return jsonify({'status': 'error'}), 400

    cursor.execute("SELECT * FROM Users WHERE UserName = ?;", (username,))
    one = cursor.fetchone()[3]
    if one == '':
        one = name
    else:
        one = one.split(" | ")
        one += [name]
        one = " | ".join(list(set(one)))

    cursor.execute("UPDATE Users SET Projects = ? WHERE UserName = ?;", (one, username))
    cursor.connection.commit()

    return jsonify({'status': 'OK'})


@app.route('/add_proj', methods=['POST'])
def upload():
    # Получаем текстовые данные
    name = request.form.get('name')
    text = request.form.get('text')
    username = request.form.get('username')
    category = request.form.get('category')

    # Получаем файл
    image_file = request.files.get('file')

    conn2 = sqlite3.connect("for_download/database_server.db", check_same_thread=False)
    cursor2 = conn2.cursor()
    cursor2.execute('SELECT MAX("Index") FROM Projects;')

    index = cursor2.fetchone()[0] + 1
    if image_file:
        cursor2.execute('INSERT INTO Projects ("Index", Name, Description, Photo, Category, Owner) '
                        'VALUES (?, ?, ?, ?, ?, ?);', (index, name, text, str(index) + ".jpg", category,
                                                       username))
    else:
        cursor2.execute('INSERT INTO Projects ("Index", Name, Description, Photo, Category, Owner) '
                        'VALUES (?, ?, ?, ?, ?, ?);', (index, name, text, "", category,
                                                       username))
    conn2.commit()
    cursor2.close()
    conn2.close()

    if image_file:
        image_file.save(f'for_download/Proj_pictures/{index}.jpg')

    # Возвращаем ответ
    return jsonify({'status': 'OK'})


@app.route('/delete_proj', methods=['POST'])
def delete_proj():
    name = request.form.get('name')
    owner = request.form.get('username')
    print(name, owner)

    conn2 = sqlite3.connect("for_download\\database_server.db", check_same_thread=False)
    cursor2 = conn2.cursor()
    cursor2.execute("SELECT Photo FROM Projects WHERE Owner = ? AND Name = ?;", (owner, name))

    file = cursor2.fetchone()
    print(file)
    if file[0]:
        os.remove("for_download/Proj_pictures/" + file[0])

    cursor2.execute('DELETE FROM Projects WHERE Owner = ? AND Name = ?;', (owner, name))
    cursor2.connection.commit()
    cursor2.close()
    conn2.close()

    return jsonify({"status": "OK"})


@app.route('/auth', methods=['GET'])
def auth():
    username = request.args.get('username')
    password = hashpw(request.args.get('password').encode("utf-8"), salt)
    cursor.execute("SELECT * FROM Users WHERE UserName = ? AND Password = ?;", (username, password))
    user = cursor.fetchone()
    if user:
        active_users.add(user[0])
        return jsonify({"status": "OK"})
    else:
        return jsonify({"status": "Error"})


@app.route('/get_user_projs', methods=['GET'])
def get_projs():
    username = request.form.get('username')

    conn2 = sqlite3.connect("for_download/database_server.db", check_same_thread=False)
    cursor2 = conn2.cursor()
    cursor2.execute('SELECT Name FROM Projects WHERE Owner = ?;', (username,))

    result = cursor2.fetchall()
    conn2.commit()
    cursor2.close()
    conn2.close()

    return jsonify({"status": "OK", "result": result})


if __name__ == '__main__':
    app.run(debug=True)
