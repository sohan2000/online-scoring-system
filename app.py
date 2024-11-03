from flask import Flask, redirect, url_for, request, render_template_string, Response, jsonify, make_response
from threading import Thread
import time
import uuid
import boto3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Initialize DynamoDB
dynamodb = boto3.resource(
    'dynamodb',
    region_name='us-west-1',  
    aws_access_key_id='AKIAXQIQARFMAYHZZ2AW',  
    aws_secret_access_key='Q3XQdX98KWq/MQkpwmtu/ELXUIKku1IAxf1zerbj'  
)
score_table = dynamodb.Table('PerformersScores')
timer_table = dynamodb.Table('TimerStatus')  # Table for shared timer status

polling_active = False
status_updates = []  
judge_entry_allowed = False 
current_performer = 1  
judge_roles = {}  

def update_login_count():
   
    response = timer_table.update_item(
        Key={'status_id': 'current_status'},
        UpdateExpression="SET login_count = if_not_exists(login_count, :start) + :inc",
        ExpressionAttributeValues={':start': 0, ':inc': 1},
        ReturnValues="UPDATED_NEW"
    )
    return response['Attributes']['login_count']

def check_login_count():
    """Poll DynamoDB every 2 seconds until login_count reaches 2."""
    global polling_active
    while polling_active:
        response = timer_table.get_item(Key={'status_id': 'current_status'})
        login_count = response['Item'].get('login_count', 0)
        print(f"Current login count: {login_count}")
        if login_count >= 2:
            Thread(target=start_performance_timer).start()
            break
        time.sleep(2)
    polling_active = False

def start_performance_timer():
    #Start timers for performers and judges, and control score entry window.
    global status_updates, judge_entry_allowed, current_performer
    status_updates.append("All users have logged in. Starting performance timer.")
    for performer in range(4):
        current_performer = performer + 1
        status_updates.append(f"Performer {current_performer} is performing for 10 seconds.")
        time.sleep(10)
        
        
        judge_entry_allowed = True
        status_updates.append(f"Judges have 5 seconds to enter scores for Performer {current_performer}.")
        time.sleep(5)
        judge_entry_allowed = False
        status_updates.append(f"Score entry closed for Performer {current_performer}.")

    status_updates.append("Performance session complete.")

@app.route('/')
def index():
    #Login form
    return render_template_string("""
        <form action="{{ url_for('login') }}" method="post">
            <label>Username:</label>
            <input type="text" name="username">
            <button type="submit">Login</button>
        </form>
        <br>
        <div id="current-performer">Waiting for current performer...</div>
        <label>Enter Score:</label>
        <input type="number" id="score" min="0" max="10">
        <button onclick="submitScore()">Submit Score</button>
        <br>
        <div id="status-updates">Waiting for updates...</div>
        <script>
            // Connect to the SSE endpoint for real-time updates
            const eventSource = new EventSource("{{ url_for('sse_status') }}");
            eventSource.onmessage = function(event) {
                const data = event.data;
                if (data.startsWith("Performer")) {
                    document.getElementById("current-performer").innerText = data;
                }
                document.getElementById("status-updates").innerHTML += data + "<br>";
            };

            // Submit score without page reload
            function submitScore() {
                const score = document.getElementById("score").value;
                fetch("{{ url_for('submit_score') }}", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ score: score })
                }).then(response => response.json()).then(data => {
                    alert(data.message);
                }).catch(error => console.error("Error submitting score:", error));
            }
        </script>
    """)

@app.route('/login', methods=['POST'])
def login():
    global polling_active
    
    # Assign judge role as "judge1" or "judge2" based on the current count
    if "judge1" not in judge_roles.values():
        judge_role = "judge1"
    elif "judge2" not in judge_roles.values():
        judge_role = "judge2"
    else:
        return "Only two judges are allowed.", 403 
    
    # Assign the role to judge
    judge_id = str(uuid.uuid4())
    judge_roles[judge_id] = judge_role  
    
    # For client-side identification
    response = make_response(redirect(url_for('index')))
    response.set_cookie('judge_id', judge_id)
    print(f"Assigned {judge_role} to judge with ID {judge_id}")
    
    # Update login count and start polling if this is the first login
    login_count = update_login_count()
    if not polling_active:
        polling_active = True
        Thread(target=check_login_count).start()
    
    return response

@app.route('/submit_score', methods=['POST'])
def submit_score():
    """Endpoint for judges to submit their scores."""
    global judge_entry_allowed, current_performer
    if not judge_entry_allowed:
        return jsonify({"message": "Score submission not allowed at this time."}), 403
    
    data = request.get_json()
    score = int(data['score'])
    judge_id = request.cookies.get('judge_id') 
    judge_role = judge_roles.get(judge_id) 
    
    if judge_role not in ['judge1', 'judge2']:
        return jsonify({"message": "Invalid judge role."}), 403
    
    
    score_column = f"{judge_role}_score"  
    
    # Store the score in DynamoDB with the specific judge column
    score_table.put_item(
        Item={
            'performer_id': f"performer_{current_performer}",  
            score_column: score, 
            'timestamp': int(time.time())
        }
    )
    return jsonify({"message": f"Score of {score} submitted by {judge_role} for Performer {current_performer}!"}), 200

@app.route('/sse_status')
def sse_status():
    """Send server-sent events with performance updates."""
    def event_stream():
        last_message_index = 0
        while True:
            if len(status_updates) > last_message_index:
               
                new_messages = status_updates[last_message_index:]
                last_message_index = len(status_updates)
                for message in new_messages:
                    yield f"data: {message}\n\n"
            time.sleep(1)
    return Response(event_stream(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, threaded=True)
