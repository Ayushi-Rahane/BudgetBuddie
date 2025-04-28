from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta 
import matplotlib
matplotlib.use('Agg')  # Use a non-GUI backend before importing pyplot
import matplotlib.pyplot as plt
import io
import base64
load_dotenv() # Load environment variables from .env file



conn = mysql.connector.connect(
    host="localhost",        
    port=3307,               
    user="root",
    password="root",
    database="budgetbuddie"
)

cursor = conn.cursor(dictionary=True)

app = Flask(__name__)

#app.secret_key = os.getenv('SECRET_KEY')
app.secret_key = '8c0f560fe793bc1ca1899625700c6c0b'




@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        # Get form data
        username = request.form['email']
        password = request.form['password']
        # Check if the user exists in the database
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cursor.fetchone()

        if user:
            # Verify the password
            if check_password_hash(user['password'], password):
                # Password is correct, redirect to the home page
                session['user_id'] = user['id']
                session['username'] = user['username']
                return redirect(url_for('home'))
        
        else:
            # User not found
            return "Invalid email or password. Please try again."
            
        
    
    return render_template('login.html')


# Add a new expense (ADD EXPENSE)
@app.route('/add_expense', methods=['POST'])
def add_expense():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    title = request.form['title']
    category = request.form['category']
    amount = request.form['amount']
    date = request.form.get('date')
    if not date:
        date = datetime.today()
    else:
        date = datetime.strptime(date, '%Y-%m-%d')

    user_id = session['user_id']  # Assuming the user is logged in

    cursor.execute(
        "INSERT INTO expenses (user_id, title, category, amount, date) VALUES (%s, %s, %s, %s, %s)",
        (user_id, title, category, amount, date)
    )
    conn.commit()
    return redirect(url_for('add_expense_page'))


# Delete an expense (DELETE EXPENSE)
@app.route('/delete_expense/<int:expense_id>', methods=['POST'])
def delete_expense(expense_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cursor.execute("DELETE FROM expenses WHERE id = %s", (expense_id,))
    conn.commit()
    return redirect(url_for('view_expense_page'))

#Show the Edit form
@app.route('/edit_expense/<int:expense_id>', methods=['GET'])
def edit_expense(expense_id):
    cursor.execute("SELECT * FROM expenses WHERE id = %s", (expense_id,))
    expense = cursor.fetchone()
    return render_template('edit_expense.html', expense=expense)

#Show the Update form
@app.route('/update_expense/<int:expense_id>', methods=['POST'])
def update_expense(expense_id):
    title = request.form['title']
    category = request.form['category']
    amount = request.form['amount']

    cursor.execute(
        "UPDATE expenses SET title = %s, category = %s, amount = %s WHERE id = %s",
        (title, category, amount, expense_id)
    )
    conn.commit()
    return redirect(url_for('view_expense_page'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Get form data
        username = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Check if the passwords match
        if password != confirm_password:
            return "Passwords do not match. Please try again."
        
        # Hash the password
        hashed_password = generate_password_hash(password)
        
        # Check if the email already exists in the database
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        existing_user = cursor.fetchone()
        
        if existing_user:
            return "Email already registered. Please login or use a different email."
        
        # Insert the new user into the database
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, hashed_password))
        conn.commit()
        
        return render_template('login.html')
    
    return render_template('register.html')


@app.route('/')
def home():
    if 'user_id' in session:
        # User is logged in, show the home page
        
        user_id = session['user_id']
             
        cursor.execute("SELECT * FROM expenses WHERE user_id = %s order by date desc limit 3", (user_id,))
        expenses = cursor.fetchall()
        cursor.execute("select * from expenses where user_id = %s", (user_id,))
        all_expenses = cursor.fetchall()
        total_expense = sum(exp['amount'] for exp in all_expenses)
        cursor.execute("select * from income where user_id=%s", (user_id,))
        incomes = cursor.fetchall()
        total_income = sum(income['amount'] for income in incomes)
        total_balance = total_income - total_expense

         # Create financial overview pie chart
        overview_labels = ['Total Income', 'Total Expenses']
        overview_sizes = [total_income, total_expense]
        overview_image_base64 = create_financial_overview_piechart(overview_labels, overview_sizes)


        return render_template('index.html', expenses=expenses, total_expense=total_expense, total_income=total_income, total_balance=total_balance,           overview_image_base64=overview_image_base64)
    
    else:
        # User is not logged in, redirect to the login page
        return redirect(url_for('login'))

def create_financial_overview_piechart(labels, sizes):
    colors = ['#4CAF50', '#F44336']  # Green for Income, Red for Expenses

    fig, ax = plt.subplots(figsize=(5, 3))
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=None,
        autopct='%1.1f%%',
        startangle=90,
        colors=colors,
        textprops={'color': 'white'}
    )

    # Donut style
    centre_circle = plt.Circle((0, 0), 0.70, fc='white')
    fig.gca().add_artist(centre_circle)

    #Add total balance in center
    total_balance = sizes[0] - sizes[1]
    plt.text(0, 0, f'Total Balance\n₹{total_balance:.2f}', horizontalalignment='center', verticalalignment='center', fontsize=14, fontweight='bold')

    # Legend
    ax.legend(wedges, labels, loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

    plt.tight_layout()

    # Save to buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()

    plt.close(fig)
    return image_base64



#Add expense page rendering
@app.route('/add_expense_page')
def add_expense_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    user_id = session['user_id']
    cursor.execute("SELECT * FROM expenses order by date desc limit 3")
    expenses = cursor.fetchall()    
    cursor.execute("select * from expenses where user_id = %s", (user_id,))
    all_expenses = cursor.fetchall()
    total_expense = sum(exp['amount'] for exp in all_expenses) 
    return render_template('add_expense.html',expenses=expenses, total=total_expense)


#View expense page rendering
@app.route('/view_expense_page')
def view_expense_page():
    if 'user_id' in session:
        # User is logged in, show the home page
        
        user_id = session['user_id']
        search_query = request.args.get('query')
        amount = request.args.get('amount')
        date = request.args.get('date')
        # Fetch expenses from the database
        sql = "SELECT id,title, category, amount, date FROM expenses WHERE user_id = %s"
        params = [user_id]

        if search_query:
            sql +=" AND (title LIKE %s OR category LIKE %s)"
            params.extend([f"%{search_query}%", f"%{search_query}%"])

        if amount:
            sql += " AND amount = %s"
            params.append(amount)
        
        if date:
            sql += " AND DATE(date) = %s"
            params.append(date)
        
        cursor.execute(sql, tuple(params))
        expenses = cursor.fetchall()
    # --- Category-wise analysis ---
        cursor.execute("SELECT category, SUM(amount) as total FROM expenses WHERE user_id = %s GROUP BY category", (user_id,))
        category_data = cursor.fetchall()

        categories = [row['category'] for row in category_data]
        amounts = [row['total'] for row in category_data]

        # Generate pie chart
        category_chart_base64 = create_category_pie_chart(categories, amounts)
        return render_template('view_expense.html', expenses=expenses, category_chart_base64=category_chart_base64)

def create_category_pie_chart(categories, amounts):
    colors = plt.cm.Paired.colors  # Use a colormap

    fig, ax = plt.subplots(figsize=(6, 4))
    
    wedges, texts, autotexts = ax.pie(
        amounts,
        # Remove labels from here
        autopct='%1.1f%%',
        startangle=140,
        colors=colors,
        textprops={'fontsize': 10, 'color': 'black'}  # only % will be black
    )

    # Manually add category labels with white color
    for i, text in enumerate(texts):
        text.set_text(categories[i])  # Set category name
        text.set_color('white')       # Make it white
        text.set_fontsize(10)       


    ax.axis('equal')  # Equal aspect ratio ensures pie is circular.

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight', transparent=True)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()

    return img_base64
@app.route('/income_page')
def income_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    # Fetch all incomes
    cursor.execute("SELECT * FROM income WHERE user_id = %s ORDER BY date DESC LIMIT 3", (session['user_id'],))
    incomes = cursor.fetchall()

    # Fetch income grouped by source for Pie Chart
    cursor.execute("SELECT source, SUM(amount) as total FROM income WHERE user_id = %s GROUP BY source", (session['user_id'],))
    income_sources = cursor.fetchall()

    total_income = sum(row['total'] for row in income_sources)

    # Generate pie chart
    if income_sources:
        labels = [row['source'] for row in income_sources]
        sizes = [row['total'] for row in income_sources]
        image_base64 = create_income_piechart(labels, sizes, total_income)
    else:
        image_base64 = None

    return render_template('income.html', incomes=incomes, image_base64=image_base64)
#piechart function to show income based on income source
def create_income_piechart(labels, sizes, total_income):
    # Colors (optional: you can customize)
    colors = plt.cm.Paired.colors[:len(labels)]

    # Create a figure for the pie chart
    fig, ax = plt.subplots(figsize=(6, 6))
    wedges, texts, autotexts = ax.pie(
        sizes, 
        labels=None, 
        autopct='%1.1f%%', 
        startangle=140, 
        colors=colors,
        textprops={'color':"w"}
    )

    # Draw circle for donut
    centre_circle = plt.Circle((0, 0), 0.70, fc='white')
    fig.gca().add_artist(centre_circle)

    # Add Total Income in center
    plt.text(0, 0, f'Total\n₹{total_income:.2f}', horizontalalignment='center', verticalalignment='center', fontsize=14, fontweight='bold')

    # Add Legend
    ax.legend(wedges, labels, title="Sources", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

    plt.tight_layout()

  #save plot to ByteIO instead saving to file
    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)

    # Encode the image to base64
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()


    # Close the plot to avoid GUI interference
    plt.close(fig)
    return image_base64


@app.route('/add_income', methods=['POST'])
def add_income():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    amount = request.form['amount']
    date = request.form.get('date')
    if not date:
        date = datetime.today()
    else:
        date = datetime.strptime(date, '%Y-%m-%d')
    source = request.form['source']
    user_id = session['user_id']
    cursor.execute(
        "INSERT INTO income (user_id, amount, source, date) VALUES (%s, %s, %s, %s)",
        (user_id, amount,source, date)
    )
    conn.commit()
    return redirect(url_for('income_page'))



@app.route('/edit_income_page/<int:income_id>')
def edit_income_page(income_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cursor.execute("SELECT * FROM income WHERE id = %s", (income_id,))
    income = cursor.fetchone()

    if not income:
        return "Income not found", 404

    return render_template('edit_income.html', income=income)

@app.route('/update_income/<int:income_id>', methods=['POST'])
def update_income(income_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    amount = request.form['amount']
    source = request.form['source']
    date = request.form['date']
    
    if not date:
        date = datetime.today()
    else:
        date = datetime.strptime(date, '%Y-%m-%d')
    
    cursor.execute(
        "UPDATE income SET amount = %s, source = %s, date = %s WHERE id = %s",
        (amount, source, date, income_id)
    )
    conn.commit()
    return redirect(url_for('income_page'))


@app.route('/delete_income/<int:income_id>', methods=['POST'])
def delete_income(income_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    cursor.execute("DELETE FROM income WHERE id = %s", (income_id,))
    conn.commit()
    return redirect(url_for('income_page'))

@app.route('/budget_setting', methods=['GET', 'POST'])
def budget_setting_page():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']

    if request.method == 'POST':
        budget = request.form.get('budget')
        if budget:
            budget = float(budget)
            cursor.execute("SELECT * FROM budgets WHERE user_id = %s", (user_id,))
            existing_budget = cursor.fetchone()
            if existing_budget:
                cursor.execute("UPDATE budgets SET budget_amount = %s WHERE user_id = %s", (budget, user_id))
            else:
                cursor.execute("INSERT INTO budgets (user_id, budget_amount) VALUES (%s, %s)", (user_id, budget))
            conn.commit()
        return redirect(url_for('budget_setting_page'))

    # For GET request: fetch budget
    cursor.execute("SELECT budget_amount FROM budgets WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    budget = float(result['budget_amount']) if result else None

    # Calculate total expense
    cursor.execute("SELECT SUM(amount) as total_expense FROM expenses WHERE user_id = %s", (user_id,))
    total_expense = cursor.fetchone()['total_expense'] or 0
    total_expense = float(total_expense)

    budget_doughnut_chart_base64 = None
    warning_message = None
    warning_color = None
    motivational_message = None

    if budget is not None:
        budget_doughnut_chart_base64 = create_budget_doughnut_chart(budget, total_expense)

        if budget > 0:
            usage_percent = (total_expense / budget) * 100

            if usage_percent >= 100:
                warning_message = "🚨 You have exceeded your budget! Please review your expenses."
                warning_color = "danger"  # Red
            elif usage_percent >= 90:
                warning_message = "⚠️ You have used over 90% of your budget. Spend carefully!"
                warning_color = "warning"  # Yellow
            else:
                motivational_message = "🎯 Great job! You're managing your budget well. Keep going!"

    return render_template('budget_setting.html',
                           budget=budget,
                           budget_doughnut_chart_base64=budget_doughnut_chart_base64,
                           warning_message=warning_message,
                           warning_color=warning_color,
                           motivational_message=motivational_message)

# --- function to create Budget Doughnut Chart ---
def create_budget_doughnut_chart(budget, total_expense):
    labels = ['Used', 'Remaining']
    sizes = [total_expense, max(0, budget - total_expense)]
    colors = ['#FF6F61', '#6FCF97']  # Red for used, Green for remaining

    fig, ax = plt.subplots(figsize=(6, 6))
    wedges, texts, autotexts = ax.pie(
        sizes,
        labels=None,
        autopct='%1.1f%%',
        startangle=90,
        colors=colors,
        textprops={'color': "w"}
    )

    # Donut style
    centre_circle = plt.Circle((0, 0), 0.70, fc='white')
    fig.gca().add_artist(centre_circle)

    # Add remaining budget in center
    remaining = budget - total_expense
    plt.text(0, 0, f'Remaining\n₹{remaining:.2f}', horizontalalignment='center', verticalalignment='center', fontsize=14, fontweight='bold')

    ax.legend(wedges, labels, title="Budget", loc="center left", bbox_to_anchor=(1, 0, 0.5, 1))

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png', transparent=True)
    buf.seek(0)
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    buf.close()
    plt.close(fig)
    return image_base64


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

#inject_budget_warning() automatically injects warning_message and warning_color into every template without you needing to manually pass them in every render_template().
@app.context_processor
def inject_budget_warning():
    if 'user_id' not in session:
        return {}

    user_id = session['user_id']

    cursor.execute("SELECT budget_amount FROM budgets WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    budget = float(result['budget_amount']) if result else None

    cursor.execute("SELECT SUM(amount) as total_expense FROM expenses WHERE user_id = %s", (user_id,))
    total_expense = cursor.fetchone()['total_expense'] or 0
    total_expense = float(total_expense)

    warning_message = None
    warning_color = None

    if budget is not None and budget > 0:
        usage_percent = (total_expense / budget) * 100
        if usage_percent >= 100:
            warning_message = "🚨 You have exceeded your budget! Please review your expenses."
            warning_color = "danger"
        elif usage_percent >= 90:
            warning_message = "⚠️ You have used over 90% of your budget. Spend carefully!"
            warning_color = "warning"

    return dict(warning_message=warning_message, warning_color=warning_color)

if __name__ == '__main__':
    app.run(debug=True, threaded=False)