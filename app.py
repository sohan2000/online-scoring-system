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
    aws_access_key_id='your_access_key', # Add your access key here
    aws_secret_access_key='your_secret_key' # Add your secret key here
)
score_table = dynamodb.Table('PerformersScores')
timer_table = dynamodb.Table('TimerStatus')
judge_table = dynamodb.Table('judge_credentials')
performance_status = dynamodb.Table('performance_status')

polling_active = False
status_updates = []  
judge_entry_allowed = False 
current_performer = 1  
judge_roles = {}  

def reset_all_login():
    try:
        response = timer_table.update_item(
            Key={'status_id': 'current_status'},
            UpdateExpression="SET login_count = :zero",
            ExpressionAttributeValues={':zero': 0},
            ReturnValues="UPDATED_NEW"
        )
        print("Login count reset to zero!")
        print("Updated attributes:", response['Attributes'])

        # Scan judge_credentials table to get all judges
        response = judge_table.scan()
        judges = response.get('Items', [])
        for judge in judges:
            judge_email = judge['judge_email']
            judge_table.update_item(
                Key={'judge_email': judge_email},
                UpdateExpression="SET logged_in = :false",
                ExpressionAttributeValues={':false': False}
            )
        print("All judges' logged_in status reset to false!")
    except Exception as e:
        print(f"Error resetting login count or logged_in status: {e}")

def delete_all_PerformersScores_records():
    try:
        response = score_table.scan()
        items = response.get('Items', [])
        for item in items:
            score_table.delete_item(
                Key={'performer_id': item['performer_id']}
            )
        print("All records deleted successfully!")
    except Exception as e:
        print(f"Error deleting records: {e}")

def reset_event_status():
    try:
        response = performance_status.scan()
        performers = response.get('Items', [])
        for performer in performers:
            performer_id = performer['performer_id']
            performance_status.update_item(
                Key={'performer_id': performer_id},
                UpdateExpression="SET event_status = :status",
                ExpressionAttributeValues={':status': 'Event Not Started'}
            )
        print("All performers' event_status reset to 'Event Not Started'.")
    except Exception as e:
        print(f"Error resetting event status: {e}")

def update_login_count():
    response = timer_table.update_item(
        Key={'status_id': 'current_status'},
        UpdateExpression="SET login_count = if_not_exists(login_count, :start) + :inc",
        ExpressionAttributeValues={':start': 0, ':inc': 1},
        ReturnValues="UPDATED_NEW"
    )
    return response['Attributes']['login_count']

def check_login_count():
    """Poll DynamoDB every 2 seconds until login_count reaches 3!"""
    global polling_active
    while polling_active:
        response = timer_table.get_item(Key={'status_id': 'current_status'})
        login_count = response['Item'].get('login_count', 0)
        print(f"Current login count: {login_count}")
        # Start performance when all three users (judge1, judge2, admin) have logged in
        if login_count >= 3:
            Thread(target=start_performance_timer).start()
            break
        time.sleep(2)
    polling_active = False

def start_performance_timer():
    #Start timers for performers and judges, and control score entry window.
    global status_updates, judge_entry_allowed, current_performer
    status_updates.append("All users have logged in. Starting performance timer!")
    update_performance_status(1, "Event Not Started")
    for performer in range(5):
        current_performer = performer + 1
        update_performance_status(current_performer, "Event In Progress")
        status_updates.append(f"Performer {current_performer} is performing for 10 seconds!")
        time.sleep(10)
        
        judge_entry_allowed = True
        update_performance_status(current_performer, "Event Ended")
        status_updates.append(f"Judges have 30 seconds to enter scores for Performer {current_performer}!")
        time.sleep(30)
        judge_entry_allowed = False
        status_updates.append(f"Score entry closed for Performer {current_performer}!")

    status_updates.append("Performance session complete!")
    status_updates.append("Head to Performance dashboard!")

def update_performance_status(performer_id, event_status):
    # Perform the update operation
    response = performance_status.update_item(
        Key={'performer_id': f'performer_{performer_id}'},  # Use the correct performer_id
        UpdateExpression="SET event_status = :status",  # Update event_status
        ExpressionAttributeValues={':status': event_status},  # New value for event_status
        ReturnValues="UPDATED_NEW"  # Return the updated values
    )
    
    # Print the updated attributes
    print(f"Updated performer {performer_id} with status: {event_status}")
    print("Updated attributes:", response['Attributes'])

@app.route('/')
def index():
    return render_template_string("""
    <!DOCTYPE html>
    <html class="dark">
    <head>
        <script src="https://cdn.tailwindcss.com"></script>
        <script>
            tailwind.config = {
                darkMode: 'class',
                theme: {
                    extend: {
                        colors: {
                            dracula: {
                                bg: '#282a36',
                                current: '#44475a',
                                foreground: '#f8f8f2',
                                purple: '#bd93f9',
                                orange: '#ffb86c'
                            }
                        }
                    }
                }
            }
        </script>
    </head>
    <body class="bg-dracula-bg text-dracula-foreground min-h-screen flex items-center justify-center">
        <div class="bg-dracula-current p-8 rounded-lg shadow-lg w-96">
            <h1 class="text-2xl font-bold text-dracula-purple mb-6 text-center">Login</h1>
            <form action="{{ url_for('login') }}" method="post" class="space-y-4">
                <div>
                    <label class="block text-dracula-pink mb-2">Email</label>
                    <input type="email" name="email" required 
                           class="w-full p-2 rounded bg-dracula-bg border border-dracula-purple 
                                  focus:outline-none focus:ring-2 focus:ring-dracula-purple">
                </div>
                <div>
                    <label class="block text-dracula-pink mb-2">Password</label>
                    <input type="password" name="password" required 
                           class="w-full p-2 rounded bg-dracula-bg border border-dracula-purple 
                                  focus:outline-none focus:ring-2 focus:ring-dracula-purple">
                </div>
                <button type="submit" 
                        class="w-full bg-dracula-purple text-dracula-foreground py-2 px-4 rounded 
                               hover:bg-opacity-90 transition duration-200">
                    Login
                </button>
            </form>
        </div>
    </body>
    </html>
    """)

@app.route('/admin')
def admin_page():
    return render_template_string("""
    <!DOCTYPE html>
    <html class="dark">
    <head>
        <script src="https://cdn.tailwindcss.com"></script>
        <script>
            tailwind.config = {
                darkMode: 'class',
                theme: {
                    extend: {
                        colors: {
                            dracula: {
                                bg: '#282a36',
                                current: '#44475a',
                                selection: '#44475a',
                                foreground: '#f8f8f2',
                                comment: '#6272a4',
                                cyan: '#8be9fd',
                                green: '#50fa7b',
                                orange: '#ffb86c',
                                pink: '#ff79c6',
                                purple: '#bd93f9',
                                red: '#ff5555',
                                yellow: '#f1fa8c'
                            }
                        }
                    }
                }
            }
        </script>
    </head>
    <body class="bg-dracula-bg text-dracula-foreground min-h-screen">
        <div class="flex h-screen">
            <!-- Left Half: Events -->
            <div class="w-1/2 p-6 border-r border-dracula-current">
                <h2 class="text-dracula-pink text-xl font-semibold mb-4">Events Happening</h2>
                <div id="status-updates" class="bg-dracula-current rounded-lg p-4 h-[calc(100vh-10rem)] overflow-y-auto">
                </div>
            </div>

            <!-- Right Half: Tables -->
            <div class="w-1/2 p-6 flex flex-col space-y-6">
                <!-- Performers Scores Table -->
                <div class="flex-1">
                    <h2 class="text-dracula-pink text-xl font-semibold mb-4">Performers Scores</h2>
                    <div class="overflow-x-auto bg-dracula-current rounded-lg">
                        <table class="w-full">
                            <thead class="bg-dracula-selection">
                                <tr>
                                    <th class="px-4 py-2 text-left text-dracula-purple">Performer ID</th>
                                    <th class="px-4 py-2 text-left text-dracula-purple">Judge 1</th>
                                    <th class="px-4 py-2 text-left text-dracula-purple">Judge 2</th>
                                    <th class="px-4 py-2 text-left text-dracula-purple">Admin</th>
                                </tr>
                            </thead>
                            <tbody id="scores-table" class="divide-y divide-dracula-selection">
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Performance Status Table -->
                <div class="flex-1">
                    <h2 class="text-dracula-pink text-xl font-semibold mb-4">Performance Status</h2>
                    <div class="overflow-x-auto bg-dracula-current rounded-lg">
                        <table class="w-full">
                            <thead class="bg-dracula-selection">
                                <tr>
                                    <th class="px-4 py-2 text-left text-dracula-purple">Performer ID</th>
                                    <th class="px-4 py-2 text-left text-dracula-purple">Status</th>
                                    <th class="px-4 py-2 text-left text-dracula-purple">Actions</th>
                                </tr>
                            </thead>
                            <tbody id="performance-status-table" class="divide-y divide-dracula-selection">
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const eventSource = new EventSource("{{ url_for('sse_status') }}");
            eventSource.onmessage = function(event) {
                const data = event.data;
                const statusUpdatesDiv = document.getElementById("status-updates");
                const newUpdate = document.createElement('div');
                newUpdate.className = 'mb-2 p-2 rounded bg-dracula-selection text-dracula-foreground';
                newUpdate.textContent = data;
                statusUpdatesDiv.appendChild(newUpdate);
                statusUpdatesDiv.scrollTop = statusUpdatesDiv.scrollHeight;
            };

            function fetchScores() {
                fetch("{{ url_for('get_scores') }}")
                    .then(response => response.json())
                    .then(data => {
                        const scoresTable = document.getElementById("scores-table");
                        scoresTable.innerHTML = "";
                        data.forEach(row => {
                            const tr = document.createElement('tr');
                            tr.className = 'hover:bg-dracula-selection';
                            tr.innerHTML = `
                                <td class="px-4 py-2">${row.performer_id}</td>
                                <td class="px-4 py-2">${row.judge1_score || '-'}</td>
                                <td class="px-4 py-2">${row.judge2_score || '-'}</td>
                                <td class="px-4 py-2">${row.admin_score || '-'}</td>
                            `;
                            scoresTable.appendChild(tr);
                        });
                    })
                    .catch(error => console.error("Error fetching scores:", error));
            }

            function getStatusClass(status) {
                const statusClasses = {
                    'waiting': 'bg-dracula-comment text-dracula-foreground',
                    'start': 'bg-dracula-green text-dracula-bg',
                    'end': 'bg-dracula-purple text-dracula-foreground'
                };
                return statusClasses[status] || 'bg-dracula-comment text-dracula-foreground';
            }

            function updatePerformerStatus(performerId, status) {
                fetch('/update_performance_status', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        performer_id: performerId,
                        event_status: status
                    })
                })
                .then(() => {
                    fetchPerformanceStatus(); // Refresh the table after update
                })
                .catch(error => console.error('Error updating status:', error));
            }

            function fetchPerformanceStatus() {
                fetch("{{ url_for('get_performance_status') }}")
                    .then(response => response.json())
                    .then(data => {
                        const statusTable = document.getElementById("performance-status-table");
                        statusTable.innerHTML = "";
                        data.forEach(row => {
                            const performerId = row.performer_id.split('_')[1]; // Extract numeric ID
                            const tr = document.createElement('tr');
                            tr.className = 'hover:bg-dracula-selection';
                            tr.innerHTML = `
                                <td class="px-4 py-2">${performerId}</td>
                                <td class="px-4 py-2">
                                    <span class="px-2 py-1 rounded text-sm ${getStatusClass(row.event_status)}">
                                        ${row.event_status}
                                    </span>
                                </td>
                                <td class="px-4 py-2 space-x-2">
                                    <button onclick="updatePerformerStatus(${performerId}, 'start')"
                                            class="px-3 py-1 rounded bg-dracula-green text-dracula-bg text-sm hover:opacity-90">
                                        Start
                                    </button>
                                    <button onclick="updatePerformerStatus(${performerId}, 'end')"
                                            class="px-3 py-1 rounded bg-dracula-purple text-dracula-bg text-sm hover:opacity-90">
                                        End
                                    </button>
                                </td>
                            `;
                            statusTable.appendChild(tr);
                        });
                    })
                    .catch(error => console.error("Error fetching performance status:", error));
            }

            // Initial fetch and set intervals
            setInterval(fetchScores, 5000);
            setInterval(fetchPerformanceStatus, 5000);
            fetchScores();
            fetchPerformanceStatus();
        </script>
    </body>
    </html>
    """)

@app.route('/get_scores')
def get_scores():
    try:
        response = score_table.scan()
        items = response.get('Items', [])
        sorted_items = sorted(items, key=lambda x: x['performer_id'])
        return jsonify(sorted_items)
    except Exception as e:
        print(f"Error fetching scores: {e}")
        return jsonify({"error": "Unable to fetch scores"}), 500

@app.route('/get_performance_status')
def get_performance_status():
    # Query your DynamoDB table for all performance statuses
    response = performance_status.scan()
    return jsonify(sorted(response.get('Items', []), key=lambda x: x['performer_id']))

@app.route('/login', methods=['POST'])
def login():
    global polling_active
    # Get form data
    email = request.form.get('email')
    password = request.form.get('password')
    
    # Validate judge credentials
    is_valid, error_message = validate_judge(email, password)
    if not is_valid:
        return f"Login failed: {error_message}", 403
    
    # Assign judge role based on current login count
    if "judge1" not in judge_roles.values():
        judge_role = "judge1"
    elif "judge2" not in judge_roles.values():
        judge_role = "judge2"
    elif "admin" not in judge_roles.values():
        judge_role = "admin"
    else:
        return "Only three users (judge1, judge2, admin) are allowed!", 403
    
    # Assign the role to the judge/admin
    judge_id = str(uuid.uuid4())
    judge_roles[judge_id] = judge_role
    
    # For client-side identification (cookie)
    response = make_response(redirect(url_for('scoring')))
    response.set_cookie('judge_id', judge_id)
    
    print(f"Assigned {judge_role} to user with ID {judge_id}")
    
    # Update login count and start polling if this is the first login
    login_count = update_login_count()
    
    if not polling_active:
        polling_active = True
        Thread(target=check_login_count).start()
    
    return response

def validate_judge(email, password):
    """Validate judge credentials from DynamoDB!"""
    response = judge_table.get_item(Key={'judge_email': email})
    
    # Check if email exists in the table
    if 'Item' not in response:
        return False, "Judge not found!"
    
    # Validate password and domain
    judge = response['Item']
    if judge['password'] != password:
        return False, "Incorrect password!"
    
    if '@sjsu.edu' not in email:
        return False, "Invalid email domain. Must be @sjsu.edu!"
    
    # Update logged_in status in DynamoDB
    judge_table.update_item(
        Key={'judge_email': email},
        UpdateExpression="SET logged_in = :val",
        ExpressionAttributeValues={':val': True}
    )
    
    return True, None

@app.route('/scoring')
def scoring():
    """Scoring page accessible only after login!"""
    judge_id = request.cookies.get('judge_id')
    
    if not judge_id or judge_id not in judge_roles:
        return redirect(url_for('index'))
    
    return render_template_string("""
    <!DOCTYPE html>
    <html class="dark">
    <head>
        <script src="https://cdn.tailwindcss.com"></script>
        <script>
            tailwind.config = {
                darkMode: 'class',
                theme: {
                    extend: {
                        colors: {
                            dracula: {
                                bg: '#282a36',
                                current: '#44475a',
                                selection: '#44475a',
                                foreground: '#f8f8f2',
                                comment: '#6272a4',
                                cyan: '#8be9fd',
                                green: '#50fa7b',
                                orange: '#ffb86c',
                                orange: '#ffb86c',
                                purple: '#bd93f9',
                                red: '#ff5555',
                                yellow: '#f1fa8c'
                            }
                        }
                    }
                }
            }
        </script>
    </head>
    <body class="bg-dracula-bg text-dracula-foreground min-h-screen">
        <div class="container mx-auto px-4 py-8">
            <!-- Header -->
            <div class="mb-8">
                <h1 class="text-3xl font-bold text-dracula-purple mb-2">Scoring Panel</h1>
                <p class="text-dracula-comment">Judge ID: {{ judge_id }}</p>
            </div>

            <!-- Current Performer Card -->
            <div class="bg-dracula-current rounded-lg p-6 mb-8 shadow-lg">
                <h2 class="text-xl font-semibold text-dracula-pink mb-4">Current Performer</h2>
                <div id="current-performer" 
                     class="text-2xl font-bold text-dracula-cyan">
                    Waiting for current performer...
                </div>
            </div>

            <!-- Scoring Form -->
            <div class="bg-dracula-current rounded-lg p-6 mb-8 shadow-lg">
                <h2 class="text-xl font-semibold text-dracula-pink mb-4">Submit Score</h2>
                <div class="flex items-end space-x-4">
                    <div class="flex-1">
                        <label class="block text-dracula-foreground mb-2">
                            Enter Score (0-10):
                        </label>
                        <input type="number" 
                               id="score" 
                               min="0" 
                               max="10" 
                               class="w-full bg-dracula-bg border border-dracula-purple rounded px-4 py-2 
                                      focus:outline-none focus:ring-2 focus:ring-dracula-purple
                                      text-dracula-foreground"
                               placeholder="Enter score...">
                    </div>
                    <button onclick="submitScore()" 
                            class="bg-dracula-purple text-dracula-foreground px-6 py-2 rounded
                                   hover:bg-opacity-90 transition duration-200 flex-shrink-0">
                        Submit Score
                    </button>
                </div>
            </div>

            <!-- Status Updates -->
            <div class="bg-dracula-current rounded-lg p-6 shadow-lg">
                <h2 class="text-xl font-semibold text-dracula-pink mb-4">Status Updates</h2>
                <div id="status-updates" 
                     class="h-64 overflow-y-auto bg-dracula-bg rounded p-4 space-y-2">
                    <div class="text-dracula-comment">Waiting for updates...</div>
                </div>
            </div>
        </div>

        <!-- Toast Notification -->
        <div id="toast" 
             class="fixed bottom-4 right-4 bg-dracula-green text-dracula-bg px-6 py-3 rounded-lg
                    shadow-lg transform translate-y-full opacity-0 transition-all duration-300">
        </div>

        <script>
            const eventSource = new EventSource("{{ url_for('sse_status') }}");
            const statusUpdates = document.getElementById("status-updates");
            
            eventSource.onmessage = function(event) {
                const data = event.data;
                if (data.startsWith("Performer")) {
                    document.getElementById("current-performer").innerText = data;
                }
                
                const updateElement = document.createElement('div');
                updateElement.className = 'p-2 rounded bg-dracula-selection text-dracula-foreground';
                updateElement.textContent = data;
                statusUpdates.appendChild(updateElement);
                statusUpdates.scrollTop = statusUpdates.scrollHeight;
            };

            function showToast(message, isError = false) {
                const toast = document.getElementById('toast');
                toast.textContent = message;
                toast.className = `fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg 
                                 transform transition-all duration-300 ${
                                     isError 
                                     ? 'bg-dracula-red text-dracula-foreground' 
                                     : 'bg-dracula-green text-dracula-bg'
                                 }`;
                
                // Show toast
                setTimeout(() => {
                    toast.style.transform = 'translateY(0)';
                    toast.style.opacity = '1';
                }, 100);

                // Hide toast
                setTimeout(() => {
                    toast.style.transform = 'translateY(full)';
                    toast.style.opacity = '0';
                }, 3000);
            }

            function submitScore() {
                const scoreInput = document.getElementById("score");
                const score = scoreInput.value;

                if (score === '' || score < 0 || score > 10) {
                    showToast('Please enter a valid score between 0 and 10', true);
                    return;
                }

                fetch("{{ url_for('submit_score') }}", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ score: score })
                })
                .then(response => response.json())
                .then(data => {
                    showToast(data.message);
                    scoreInput.value = ''; // Clear input after successful submission
                })
                .catch(error => {
                    console.error("Error submitting score:", error);
                    showToast('Error submitting score', true);
                });
            }

            // Add keyboard shortcut for submission
            document.addEventListener('keydown', function(event) {
                if (event.key === 'Enter') {
                    submitScore();
                }
            });
        </script>
    </body>
    </html>
    """)

@app.route('/view_only')
def view_only():
    return render_template_string("""
    <!DOCTYPE html>
    <html class="dark">
    <head>
        <script src="https://cdn.tailwindcss.com"></script>
        <script>
            tailwind.config = {
                darkMode: 'class',
                theme: {
                    extend: {
                        colors: {
                            dracula: {
                                bg: '#282a36',
                                current: '#44475a',
                                foreground: '#f8f8f2',
                                purple: '#bd93f9',
                                orange: '#ffb86c'
                            }
                        }
                    }
                }
            }
        </script>
    </head>
    <body class="bg-dracula-bg text-dracula-foreground min-h-screen">
        <div class="flex h-screen">
            <!-- Left Half: Events -->
            <div class="w-1/2 p-6 border-r border-dracula-current">
                <h2 class="text-dracula-pink text-xl font-semibold mb-4">Events Happening</h2>
                <div id="status-updates" class="bg-dracula-current rounded-lg p-4 h-[calc(100vh-10rem)] overflow-y-auto">
                </div>
            </div>

            <!-- Right Half: Performers Scores Table (without Performance Status Table) -->
            <div class="w-1/2 p-6 flex flex-col space-y-6">
                <div class="flex-1">
                    <h2 class="text-dracula-pink text-xl font-semibold mb-4">Performers Scores</h2>
                    <div class="overflow-x-auto bg-dracula-current rounded-lg">
                        <table class="w-full">
                            <thead class="bg-dracula-selection">
                                <tr>
                                    <th class="px-4 py-2 text-left text-dracula-purple">Performer ID</th>
                                    <th class="px-4 py-2 text-left text-dracula-purple">Judge 1</th>
                                    <th class="px-4 py-2 text-left text-dracula-purple">Judge 2</th>
                                    <th class="px-4 py-2 text-left text-dracula-purple">Admin</th>
                                    <th class="px-4 py-2 text-left text-dracula-purple">Total Score</th>  <!-- New Total Score Column -->
                                </tr>
                            </thead>
                            <tbody id="scores-table" class="divide-y divide-dracula-selection">
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <script>
            const eventSource = new EventSource("{{ url_for('sse_status') }}");
            eventSource.onmessage = function(event) {
                const data = event.data;
                const statusUpdatesDiv = document.getElementById("status-updates");
                const newUpdate = document.createElement('div');
                newUpdate.className = 'mb-2 p-2 rounded bg-dracula-selection text-dracula-foreground';
                newUpdate.textContent = data;
                statusUpdatesDiv.appendChild(newUpdate);
                statusUpdatesDiv.scrollTop = statusUpdatesDiv.scrollHeight;
            };

            function fetchScores() {
                fetch("{{ url_for('get_scores_with_total') }}")  // Use the new route with total score calculation
                    .then(response => response.json())
                    .then(data => {
                        const scoresTable = document.getElementById("scores-table");
                        scoresTable.innerHTML = "";
                        data.forEach(row => {
                            const tr = document.createElement('tr');
                            tr.className = 'hover:bg-dracula-selection';
                            tr.innerHTML = `
                                <td class="px-4 py-2">${row.performer_id}</td>
                                <td class="px-4 py-2">${row.judge1_score || '-'}</td>
                                <td class="px-4 py-2">${row.judge2_score || '-'}</td>
                                <td class="px-4 py-2">${row.admin_score || '-'}</td>
                                <td class="px-4 py-2">${row.total_score || '-'}</td>  <!-- Display Total Score -->
                            `;
                            scoresTable.appendChild(tr);
                        });
                    })
                    .catch(error => console.error("Error fetching scores:", error));
            }

            // Initial fetch and set interval to refresh data every 5 seconds
            setInterval(fetchScores, 5000);
            fetchScores();
        </script>
    </body>
    </html>
    """)
@app.route('/get_scores_with_total')
def get_scores_with_total():
    try:
        response = score_table.scan()
        items = response.get('Items', [])
        sorted_items = sorted(items, key=lambda x: x['performer_id'])
        
        # Calculate Total Score for each item
        for item in sorted_items:
            judge1_score = float(item.get('judge1_score', 0))
            judge2_score = float(item.get('judge2_score', 0))
            admin_score = float(item.get('admin_score', 0))
            total_score = (0.5 * judge1_score) + (0.25 * judge2_score) + (0.25 * admin_score)
            item['total_score'] = round(total_score, 2)  # Round to 2 decimal places if needed

        return jsonify(sorted_items)
    except Exception as e:
        print(f"Error fetching scores with total: {e}")
        return jsonify({"error": "Unable to fetch scores with total"}), 500

@app.route('/submit_score', methods=['POST'])
def submit_score():
    """Endpoint for judges and admin to submit their scores!"""
    global judge_entry_allowed, current_performer
    if not judge_entry_allowed:
        return jsonify({"message": "Score submission not allowed at this time!"}), 403
    
    data = request.get_json()
    score = int(data['score'])
    
    # Get the user's role from their cookie
    judge_id = request.cookies.get('judge_id')
    judge_role = judge_roles.get(judge_id)
    
    # Ensure that only valid roles (judge1, judge2, admin) can submit scores
    if judge_role not in ['judge1', 'judge2', 'admin']:
        return jsonify({"message": "Invalid role!"}), 403
    
    score_column = f"{judge_role}_score"  # Determine which column to update based on the role
    
    # Check if the score has already been submitted by this user for the current performer
    response = score_table.get_item(
        Key={'performer_id': f"performer_{current_performer}"}
    )
    
    # If the item exists and the score column for this user is already set, restrict further submissions
    if 'Item' in response and score_column in response['Item']:
        return jsonify({"message": f"Score already submitted by {judge_role} for Performer {current_performer}!"}), 403
    
    # Update the score for the current performer without overwriting other columns
    response = score_table.update_item(
        Key={'performer_id': f"performer_{current_performer}"},  # Use performer ID as key
        UpdateExpression=f"SET {score_column} = :score",  # Dynamically set correct score column
        ExpressionAttributeValues={':score': score},  # Set new score value
        ReturnValues="UPDATED_NEW"  # Return updated attributes
    )
    
    # Log that this judge has entered a score, but only in status_updates (for admin view)
    status_updates.append(f"{judge_role} entered score {score} for Performer {current_performer}")
    return jsonify({"message": f"Score of {score} submitted by {judge_role} for Performer {current_performer}!"}), 200

@app.route('/sse_status')
def sse_status():
    """Send server-sent events with performance updates!"""
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
    reset_all_login()
    reset_event_status()
    delete_all_PerformersScores_records()
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
