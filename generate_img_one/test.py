import json
import time
from urllib import request
import urllib.error

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

# Функция для загрузки изображения
def download_image(image_url, filename):
    print(f"[LOG] Скачивание изображения с URL: {image_url}")
    try:
        response = request.urlopen(image_url)
        with open(filename, 'wb') as f:
            f.write(response.read())
        print(f"[LOG] Изображение сохранено как {filename}")
    except urllib.error.HTTPError as e:
        print("[ERROR] Ошибка при скачивании изображения.")
        print("Код ошибки: ", e.code)
        print("Сообщение: ", e.read().decode())
    except Exception as ex:
        print(f"[ERROR] Произошла ошибка: {ex}")

# Чтение workflow
print("[LOG] Чтение файла workflow_api.json...")
prompt_workflow = json.load(open('workflow_api.json'))
print("[LOG] Файл workflow_api.json успешно прочитан.")

# Настройки изображения
prompt_workflow["5"]["inputs"]["width"] = 512
prompt_workflow["5"]["inputs"]["height"] = 640
prompt_workflow["5"]["inputs"]["batch_size"] = 1
print("[LOG] Настройки изображения установлены: ширина = 512, высота = 640, batch_size = 1")

# Шаг 1: Отправка запроса на генерацию
result = queue_prompt(prompt_workflow)
if result:
    prompt_id = result.get('prompt_id')
    if prompt_id:
        print(f"[LOG] Промпт отправлен, ID: {prompt_id}")
        
        # Шаг 2: Проверка статуса генерации каждые 10 секунд до 5 минут
        max_wait_time = 300  # Максимальное время ожидания в секундах (5 минут)
        interval = 10  # Интервал времени между запросами статуса в секундах
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
                                    # Шаг 5: Скачивание изображения
                                    image_url = f"http://localhost:8888/view?filename={image_filename}&type=output&subfolder={subfolder}"
                                    print(f"[LOG] URL для загрузки изображения: {image_url}")
                                    filename = f"{image_filename}"
                                    download_image(image_url, filename)
                                    exit(0)  # Завершение после успешного сохранения изображения
            else:
                print(f"[ERROR] Не удалось получить данные для prompt_id {prompt_id}")
        
        print("[ERROR] Время ожидания истекло, задача не завершена успешно.")
    else:
        print("[ERROR] ID задачи не получен.")
else:
    print("[ERROR] Ошибка при отправке запроса.")
