import json
import time
import psycopg2
from urllib import request
import urllib.error
from datetime import datetime
import io
import re
import random  # Подключаем модуль для работы со случайными числами
from ftplib import FTP

# Подключение к базе данных PostgreSQL
def connect_to_db():
    try:
        conn = psycopg2.connect(
            user='',
            host='',
            database='',
            password='',
            port=5432
        )
        print("[LOG] Подключение к базе данных установлено.")
        return conn
    except Exception as e:
        print(f"[ERROR] Ошибка подключения к базе данных: {e}")
        return None

# Функция для выбора строки с Image_url=NULL
def get_news_without_image(conn):
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, title, date_time FROM original_news WHERE image_url IS NULL LIMIT 1;")
            row = cursor.fetchone()
            if row:
                return {"id": row[0], "title": row[1], "date_time": row[2]}
            else:
                print("[LOG] Нет записей с пустым image_url.")
                return None
    except Exception as e:
        print(f"[ERROR] Ошибка при выборке из базы данных: {e}")
        return None

# Функция для обновления image_url
def update_image_url(conn, news_id, image_url):
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE original_news SET image_url = %s WHERE id = %s;", (image_url, news_id))
            conn.commit()
            print(f"[LOG] image_url обновлен для записи с ID: {news_id}.")
    except Exception as e:
        print(f"[ERROR] Ошибка при обновлении image_url: {e}")

# Функция для обновления error_message
def update_error_message(conn, news_id, error_message):
    try:
        with conn.cursor() as cursor:
            cursor.execute("UPDATE original_news SET error_message = %s WHERE id = %s;", (error_message, news_id))
            conn.commit()
            print(f"[LOG] error_message обновлен для записи с ID: {news_id}.")
    except Exception as e:
        print(f"[ERROR] Ошибка при обновлении error_message: {e}")

# Функция отправки промпта
def queue_prompt(prompt_workflow):
    print("[LOG] Отправка запроса на генерацию...")
    p = {"prompt": prompt_workflow}
    data = json.dumps(p).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    req = request.Request("http://localhost:8888/prompt", data=data, headers=headers)
    try:
        response = request.urlopen(req)
        print("[LOG] Запрос на генерацию отправлен успешно.")
        return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print("[ERROR] Ошибка при отправке запроса на генерацию.")
        print("Код ошибки: ", e.code)
        print("Сообщение: ", e.read().decode())
        return None

# Функция для проверки статуса генерации
def get_generation_status(prompt_id):
    print(f"[LOG] Проверка статуса генерации для ID: {prompt_id}")
    try:
        url = f"http://localhost:8888/history/{prompt_id}"
        response = request.urlopen(url)
        print("[LOG] Статус генерации получен успешно.")
        return json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        print("[ERROR] Ошибка при получении статуса.")
        print("Код ошибки: ", e.code)
        print("Сообщение: ", e.read().decode())
        return None

# Функция для создания безопасного имени файла
def create_safe_filename(title):
    title = re.sub(r'[^\w\s]', '', title)  # Убираем все спецсимволы
    return title.replace(' ', '_')  # Заменяем пробелы на _

# Функция для создания пути на FTP с проверкой и созданием вложенных директорий
def create_directory_if_not_exists(ftp, path):
    # Разбиваем путь на отдельные директории
    directories = path.split('/')
    current_path = ""
    for directory in directories:
        if directory:  # Пропускаем пустые части
            current_path += f"/{directory}"
            try:
                ftp.cwd(current_path)
                print(f"[LOG] Директория {current_path} уже существует на FTP.")
            except Exception as e:
                print(f"[LOG] Директория {current_path} не существует. Пытаюсь создать...")
                try:
                    ftp.mkd(current_path)
                    print(f"[LOG] Директория {current_path} успешно создана.")
                except Exception as e:
                    print(f"[ERROR] Ошибка при создании директории {current_path}: {e}")
                    return False  # Возвращаем False в случае ошибки
    return True

# Функция загрузки изображения на FTP
def upload_image_to_ftp(ftp_host, ftp_user, ftp_password, image_url, remote_path):
    print("[LOG] Подключение к FTP серверу...")
    try:
        # Подключение к FTP
        ftp = FTP(ftp_host)
        ftp.login(user=ftp_user, passwd=ftp_password)

        # Проверка и создание основной директории и поддиректорий, если их нет
        base_path, filename = remote_path.rsplit('/', 1)
        if not create_directory_if_not_exists(ftp, base_path):
            raise Exception(f"Не удалось создать директорию {base_path} на FTP сервере")

        # Скачивание изображения напрямую в поток и загрузка на FTP
        response = request.urlopen(image_url)
        image_data = response.read()
        with io.BytesIO(image_data) as f:
            ftp.storbinary(f'STOR {remote_path}', f)
        print(f"[LOG] Изображение {filename} успешно загружено на FTP в {remote_path}.")

        ftp.quit()
    except Exception as e:
        print(f"[ERROR] Ошибка при загрузке изображения на FTP: {e}")
        raise e  # Пробрасываем исключение выше для обработки

# Основной процесс
conn = connect_to_db()
if conn:
    news = get_news_without_image(conn)
    if news:
        print(f"[LOG] Обработка записи с ID: {news['id']}, заголовок: {news['title']}")

        # Список стилей
        styles = [
            "Style Realism.", "Style Surrealism.", "Style Abstract.", "Style Pop Art.", "Style Manga.",
            "Style Fantasy.", "Style Sci-Fi.", "Style Pixel Art.", "Style Minimalism.", "Style Cyberpunk.",
            "Style Steampunk.", "Style Cartoon.", "Style Watercolor.", "Style Concept Art."
        ]

        # Случайный выбор стиля
        chosen_style = random.choice(styles)
        print(f"[LOG] Выбран стиль: {chosen_style}")

        # Обновление prompt_workflow["6"]["inputs"]["text"] с добавлением стиля перед заголовком
        prompt_workflow = json.load(open('/home/xabre/generate_img/workflow_api.json'))
        prompt_workflow["6"]["inputs"]["text"] = f"{chosen_style} {news['title']}"
        print(f"[LOG] В prompt_workflow добавлен текст: {prompt_workflow['6']['inputs']['text']}")

        # Создание имени файла и директории
        date_time = news['date_time']
        # Используем формат год/месяц
        date_folder = f"{date_time.year}/{date_time.month:02d}"
        safe_title = create_safe_filename(news['title'])
        filename = f"{safe_title}.jpg"

        try:
            # Шаг 1: Отправка запроса на генерацию
            result = queue_prompt(prompt_workflow)
            if result:
                prompt_id = result.get('prompt_id')
                if prompt_id:
                    print(f"[LOG] Промпт отправлен, ID: {prompt_id}")

                    # Шаг 2: Проверка статуса генерации каждые 10 секунд до 5 минут
                    max_wait_time = 300  # Максимальное время ожидания в секундах (5 минут)
                    interval = 5  # Интервал времени между запросами статуса в секундах
                    total_wait_time = 0
                    generation_success = False  # Флаг успешного завершения генерации

                    while total_wait_time < max_wait_time:
                        print(f"[LOG] Ожидание {interval} секунд перед следующей проверкой статуса...")
                        time.sleep(interval)
                        total_wait_time += interval

                        # Шаг 3: Проверка статуса генерации
                        try:
                            status_data = get_generation_status(prompt_id)
                            if status_data and prompt_id in status_data:
                                task_data = status_data[prompt_id]
                                status_info = task_data.get("status", {})
                                print(f"[LOG] Текущий статус: {status_info}")

                                # Шаг 4: Проверка успешности генерации
                                if status_info.get("status_str") == "success" and status_info.get("completed", False):
                                    outputs = task_data.get("outputs", {})
                                    if outputs:
                                        for node_id, output in outputs.items():
                                            images = output.get("images", [])
                                            if images:
                                                for image_info in images:
                                                    image_filename = image_info.get("filename", "")
                                                    subfolder = image_info.get("subfolder", "")
                                                    # Шаг 5: Загрузка изображения на FTP
                                                    image_url = f"http://localhost:8888/view?filename={image_filename}&type=output&subfolder={subfolder}"
                                                    print(f"[LOG] URL для загрузки изображения: {image_url}")
                                                    
                                                    # Определение пути для загрузки на FTP
                                                    remote_path = f"/ftp/images/{date_folder}/{filename}"
                                                    try:
                                                        upload_image_to_ftp('localhost', 'user', 'password', image_url, remote_path)
                                                        # Запись пути в image_url в БД
                                                        image_save_path = f"/images/{date_folder}/{filename}"
                                                        update_image_url(conn, news['id'], image_save_path)
                                                        print(f"[LOG] Путь к изображению записан в БД: {image_save_path}")
                                                        generation_success = True  # Устанавливаем флаг успешного завершения
                                                        break
                                                    except Exception as e:
                                                        error_message = f"Ошибка при загрузке изображения: {e}"
                                                        print(f"[ERROR] {error_message}")
                                                        break
                        except Exception as e:
                            print(f"[ERROR] Ошибка при проверке статуса: {e}")

                        if generation_success:
                            break

                    # Если после всех попыток генерация не была успешной
                    if not generation_success:
                        print("[ERROR] Время ожидания истекло, задача не завершена успешно.")
                        update_error_message(conn, news['id'], "Время ожидания истекло, задача не завершена успешно.")
                else:
                    print("[ERROR] ID задачи не получен.")
                    update_error_message(conn, news['id'], "ID задачи не получен.")
            else:
                print("[ERROR] Ошибка при отправке запроса.")
                update_error_message(conn, news['id'], "Ошибка при отправке запроса.")
        except Exception as e:
            error_message = f"Общая ошибка в процессе выполнения: {e}"
            update_error_message(conn, news['id'], error_message)
            print(f"[ERROR] {error_message}")
    else:
        print("[LOG] Нет записей для обработки.")
    conn.close()
else:
    print("[ERROR] Подключение к базе данных не удалось.")
