from flask import Flask, request, jsonify, render_template_string
from apscheduler.schedulers.background import BackgroundScheduler
from queue import Queue
import threading
import uuid
import time

app = Flask(__name__)
scheduler = BackgroundScheduler()
scheduler.start()

task_queue = Queue()
task_status = {}

def write_name_to_file():
    while True:
        if not task_queue.empty():
            task_id, name = task_queue.get()
            try:
                with open('names.txt', 'a') as f:
                    f.write(f"{name}\n")
                task_status[task_id] = 'completed'
            except Exception as e:
                task_status[task_id] = f'failed: {str(e)}'
            finally:
                task_queue.task_done()
        else:
            time.sleep(1)

threading.Thread(target=write_name_to_file, daemon=True).start()

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        name = request.form['name']
        task_id = str(uuid.uuid4())
        task_queue.put((task_id, name))
        task_status[task_id] = 'queued'
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
    return jsonify(task_status)

if __name__ == '__main__':
    app.run(debug=True)
