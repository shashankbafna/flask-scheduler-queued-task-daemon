from flask import Flask, request, jsonify, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler
from queue import Queue
import threading
import uuid
import time
import psutil
from datetime import datetime, timedelta

app = Flask(__name__)
scheduler = BackgroundScheduler()
scheduler.start()

task_queue = Queue()
task_status = {}
task_estimate = {}
condition = threading.Condition()

CPU_THRESHOLD = 40  # CPU usage threshold
RAM_THRESHOLD = 40  # RAM usage threshold

def can_process_task():
    cpu_usage = psutil.cpu_percent(interval=1)
    ram_usage = psutil.virtual_memory().percent
    print(f"cpu:{cpu_usage}, mem:{ram_usage}")
    return cpu_usage <= CPU_THRESHOLD and ram_usage <= RAM_THRESHOLD

def estimate_start_time():
    # Placeholder logic to estimate start time
    # In a real scenario, you might use more sophisticated prediction based on historical data
    cpu_usage = psutil.cpu_percent(interval=1)
    ram_usage = psutil.virtual_memory().percent
    if cpu_usage <= CPU_THRESHOLD and ram_usage <= RAM_THRESHOLD:
        return datetime.now()
    return datetime.now() + timedelta(minutes=5)  # Arbitrary estimate

def write_name_to_file():
    while True:
        print(task_queue)
        with condition:
            condition.wait_for(lambda: not task_queue.empty())

            task_id, name = task_queue.get()
            if can_process_task():
                try:
                    with open('names.txt', 'a') as f:
                        f.write(f"{name}\n")
                    task_status[task_id] = 'completed'
                except Exception as e:
                    task_status[task_id] = f'failed: {str(e)}'
                finally:
                    task_queue.task_done()
            else:
                print(f"task_id:{task_id}, name:{name}")
                # Requeue the task if resources are not sufficient
                task_queue.put((task_id, name))
                task_status[task_id] = f'queued: waiting for system resources, estimated start time {estimate_start_time()}'
            
            time.sleep(5)  # Wait for 5 seconds before notifying next task
            condition.notify_all()

threading.Thread(target=write_name_to_file, daemon=True).start()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form['name']
        task_id = str(uuid.uuid4())
        task_queue.put((task_id, name))
        task_status[task_id] = 'queued'
        with condition:
            condition.notify_all()
        return jsonify({"executionId": task_id})
    return render_template_string("""
        <form method="post">
            Name: <input type="text" name="name">
            <input type="submit" value="Submit">
        </form>
    """)

@app.route('/status/<task_id>', methods=['GET'])
def status(task_id):
    status = task_status.get(task_id, 'not found')
    return jsonify({"executionId": task_id, "status": status})

@app.route('/statuses', methods=['GET'])
def statuses():
    # Ensure to return the latest status
    for task_id in list(task_status.keys()):
        if task_status[task_id].startswith('queued'):
            task_status[task_id] = f'queued: waiting for system resources, estimated start time {estimate_start_time()}'
    return jsonify(task_status)

if __name__ == '__main__':
    app.run(debug=True)
