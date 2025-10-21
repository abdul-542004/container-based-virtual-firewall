from flask import Flask, request, jsonify, render_template_string
from flask_cors import CORS
from datetime import datetime
import json
import os

app = Flask(__name__)
CORS(app)

# In-memory database for employees
employees = [
    {"id": 1, "name": "John Doe", "position": "Software Engineer", "department": "IT", "salary": 75000, "email": "john@company.com"},
    {"id": 2, "name": "Jane Smith", "position": "HR Manager", "department": "HR", "salary": 65000, "email": "jane@company.com"},
    {"id": 3, "name": "Bob Johnson", "position": "DevOps Engineer", "department": "IT", "salary": 80000, "email": "bob@company.com"},
    {"id": 4, "name": "Alice Williams", "position": "Product Manager", "department": "Product", "salary": 90000, "email": "alice@company.com"},
]

next_id = 5

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Employee Management System</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background-color: white;
            border-radius: 8px;
            padding: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        h2 {
            color: #34495e;
            margin-top: 30px;
        }
        .info-box {
            background-color: #e8f4f8;
            border-left: 4px solid #3498db;
            padding: 15px;
            margin: 20px 0;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #3498db;
            color: white;
        }
        tr:hover {
            background-color: #f5f5f5;
        }
        .form-group {
            margin-bottom: 15px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #2c3e50;
        }
        input, select {
            width: 100%;
            padding: 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            box-sizing: border-box;
        }
        button {
            background-color: #3498db;
            color: white;
            padding: 10px 20px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            margin-right: 10px;
        }
        button:hover {
            background-color: #2980b9;
        }
        .delete-btn {
            background-color: #e74c3c;
        }
        .delete-btn:hover {
            background-color: #c0392b;
        }
        .api-endpoints {
            background-color: #f9f9f9;
            padding: 15px;
            border-radius: 4px;
            margin-top: 20px;
        }
        .endpoint {
            font-family: monospace;
            background-color: #2c3e50;
            color: #2ecc71;
            padding: 5px 10px;
            border-radius: 3px;
            display: inline-block;
            margin: 5px 0;
        }
        .method {
            background-color: #e74c3c;
            color: white;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 12px;
            margin-right: 5px;
        }
        .method.get { background-color: #3498db; }
        .method.post { background-color: #2ecc71; }
        .method.put { background-color: #f39c12; }
        .method.delete { background-color: #e74c3c; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏢 Employee Management System</h1>
        
        <div class="info-box">
            <strong>Server Information:</strong><br>
            Container: Server (Employee Management System)<br>
            IP Address: {{ request.host }}<br>
            Timestamp: {{ timestamp }}
        </div>

        <h2>👥 Employee List</h2>
        <table id="employeeTable">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Position</th>
                    <th>Department</th>
                    <th>Salary</th>
                    <th>Email</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                {% for emp in employees %}
                <tr>
                    <td>{{ emp.id }}</td>
                    <td>{{ emp.name }}</td>
                    <td>{{ emp.position }}</td>
                    <td>{{ emp.department }}</td>
                    <td>${{ "{:,}".format(emp.salary) }}</td>
                    <td>{{ emp.email }}</td>
                    <td>
                        <button class="delete-btn" onclick="deleteEmployee({{ emp.id }})">Delete</button>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>

        <h2>➕ Add New Employee</h2>
        <form id="addEmployeeForm">
            <div class="form-group">
                <label>Name:</label>
                <input type="text" id="name" required>
            </div>
            <div class="form-group">
                <label>Position:</label>
                <input type="text" id="position" required>
            </div>
            <div class="form-group">
                <label>Department:</label>
                <input type="text" id="department" required>
            </div>
            <div class="form-group">
                <label>Salary:</label>
                <input type="number" id="salary" required>
            </div>
            <div class="form-group">
                <label>Email:</label>
                <input type="email" id="email" required>
            </div>
            <button type="submit">Add Employee</button>
        </form>

        <h2>📡 API Endpoints</h2>
        <div class="api-endpoints">
            <p><span class="method get">GET</span> <span class="endpoint">/api/employees</span> - Get all employees</p>
            <p><span class="method get">GET</span> <span class="endpoint">/api/employees/&lt;id&gt;</span> - Get employee by ID</p>
            <p><span class="method post">POST</span> <span class="endpoint">/api/employees</span> - Add new employee</p>
            <p><span class="method put">PUT</span> <span class="endpoint">/api/employees/&lt;id&gt;</span> - Update employee</p>
            <p><span class="method delete">DELETE</span> <span class="endpoint">/api/employees/&lt;id&gt;</span> - Delete employee</p>
            <p><span class="method get">GET</span> <span class="endpoint">/health</span> - Health check</p>
        </div>
    </div>

    <script>
        // Add employee form handler
        document.getElementById('addEmployeeForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const employee = {
                name: document.getElementById('name').value,
                position: document.getElementById('position').value,
                department: document.getElementById('department').value,
                salary: parseInt(document.getElementById('salary').value),
                email: document.getElementById('email').value
            };

            try {
                const response = await fetch('/api/employees', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(employee)
                });

                if (response.ok) {
                    alert('Employee added successfully!');
                    location.reload();
                } else {
                    alert('Error adding employee');
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        });

        // Delete employee
        async function deleteEmployee(id) {
            if (!confirm('Are you sure you want to delete this employee?')) {
                return;
            }

            try {
                const response = await fetch(`/api/employees/${id}`, {
                    method: 'DELETE'
                });

                if (response.ok) {
                    alert('Employee deleted successfully!');
                    location.reload();
                } else {
                    alert('Error deleting employee');
                }
            } catch (error) {
                alert('Error: ' + error.message);
            }
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, 
                                 employees=employees, 
                                 timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                 request=request)

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "service": "Employee Management System",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/employees', methods=['GET'])
def get_employees():
    return jsonify(employees)

@app.route('/api/employees/<int:emp_id>', methods=['GET'])
def get_employee(emp_id):
    employee = next((emp for emp in employees if emp['id'] == emp_id), None)
    if employee:
        return jsonify(employee)
    return jsonify({"error": "Employee not found"}), 404

@app.route('/api/employees', methods=['POST'])
def add_employee():
    global next_id
    data = request.get_json()
    
    new_employee = {
        "id": next_id,
        "name": data.get('name'),
        "position": data.get('position'),
        "department": data.get('department'),
        "salary": data.get('salary'),
        "email": data.get('email')
    }
    
    employees.append(new_employee)
    next_id += 1
    
    return jsonify(new_employee), 201

@app.route('/api/employees/<int:emp_id>', methods=['PUT'])
def update_employee(emp_id):
    employee = next((emp for emp in employees if emp['id'] == emp_id), None)
    if not employee:
        return jsonify({"error": "Employee not found"}), 404
    
    data = request.get_json()
    employee.update({
        "name": data.get('name', employee['name']),
        "position": data.get('position', employee['position']),
        "department": data.get('department', employee['department']),
        "salary": data.get('salary', employee['salary']),
        "email": data.get('email', employee['email'])
    })
    
    return jsonify(employee)

@app.route('/api/employees/<int:emp_id>', methods=['DELETE'])
def delete_employee(emp_id):
    global employees
    employee = next((emp for emp in employees if emp['id'] == emp_id), None)
    if not employee:
        return jsonify({"error": "Employee not found"}), 404
    
    employees = [emp for emp in employees if emp['id'] != emp_id]
    return jsonify({"message": "Employee deleted successfully"})

if __name__ == '__main__':
    print("=" * 50)
    print("Employee Management System Server")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
