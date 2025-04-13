import json
import time
from urllib import request
import urllib.error
from ftplib import FTP
from datetime import datetime
import io

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

# Функция для создания пути на FTP
def create_directory_if_not_exists(ftp, path):
    try:
        # Пытаемся зайти в директорию
        ftp.cwd(path)
        print(f"[LOG] Директория {path} уже существует на FTP.")
    except Exception as e:
        # Если директория не существует, пытаемся ее создать
        print(f"[LOG] Директория {path} не существует. Пытаюсь создать...")
        try:
            ftp.mkd(path)
            print(f"[LOG] Директория {path} успешно создана.")
        except Exception as e:
            print(f"[ERROR] Ошибка при создании директории {path}: {e}")

# Функция загрузки изображения напрямую на FTP
def upload_image_to_ftp(ftp_host, ftp_user, ftp_password, image_url, remote_filename):
    print("[LOG] Подключение к FTP серверу...")
    try:
        # Подключение к FTP
        ftp = FTP(ftp_host)
        ftp.login(user=ftp_user, passwd=ftp_password)

        # Определение текущей даты для создания папки
        now = datetime.now()
        year_folder = f"{now.year}"
        month_folder = f"{now.month:02d}"

        # Основной путь для загрузки
        base_path = "/ftp/images"

        # Проверка и создание основной папки images, если ее нет
        create_directory_if_not_exists(ftp, base_path)

        # Проверка и создание папки года, если ее нет
        create_directory_if_not_exists(ftp, f"{base_path}/{year_folder}")

        # Проверка и создание папки месяца, если ее нет
        create_directory_if_not_exists(ftp, f"{base_path}/{year_folder}/{month_folder}")

        # Определение полного пути загрузки
        remote_path = f"{base_path}/{year_folder}/{month_folder}/{remote_filename}"

        # Скачивание изображения напрямую в поток и загрузка на FTP
        response = request.urlopen(image_url)
        image_data = response.read()
        with io.BytesIO(image_data) as f:
            ftp.storbinary(f'STOR {remote_path}', f)
        print(f"[LOG] Изображение {remote_filename} успешно загружено на FTP в {remote_path}.")

        ftp.quit()
    except Exception as e:
        print(f"[ERROR] Ошибка при загрузке изображения на FTP: {e}")

# Чтение workflow
print("[LOG] Чтение файла workflow_api.json...")
prompt_workflow = json.load(open('workflow_api.json'))
print("[LOG] Файл workflow_api.json успешно прочитан.")

# Настройки изображения
prompt_workflow["5"]["inputs"]["width"] = 1024
prompt_workflow["5"]["inputs"]["height"] = 512
prompt_workflow["5"]["inputs"]["batch_size"] = 1
prompt_workflow["6"]["inputs"]["text"] = "black and white cat of british breed"

print("[LOG] Настройки изображения установлены: ширина = 1024, высота = 512, batch_size = 1")

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

        while total_wait_time < max_wait_time:
            print(f"[LOG] Ожидание {interval} секунд перед следующей проверкой статуса...")
            time.sleep(interval)
            total_wait_time += interval

            # Шаг 3: Проверка статуса генерации
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
                                    # Шаг 5: Загрузка изображения напрямую на FTP
                                    image_url = f"http://localhost:8888/view?filename={image_filename}&type=output&subfolder={subfolder}"
                                    print(f"[LOG] URL для загрузки изображения: {image_url}")
                                    remote_filename = f"{image_filename}"
                                    upload_image_to_ftp('localhost', 'user', 'password', image_url, remote_filename)
                                    exit(0)  # Завершение после успешного сохранения изображения и загрузки на FTP
            else:
                print(f"[ERROR] Не удалось получить данные для prompt_id {prompt_id}")

        print("[ERROR] Время ожидания истекло, задача не завершена успешно.")
    else:
        print("[ERROR] ID задачи не получен.")
else:
    print("[ERROR] Ошибка при отправке запроса.")
