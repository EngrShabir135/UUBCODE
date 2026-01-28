import streamlit as st
import sqlite3, bcrypt, random, time, os
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from fpdf import FPDF
from PIL import Image

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="United Union Bank",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ---------------- CUSTOM CSS ----------------
st.markdown("""
<style>
    /* Main styling */
    .main-header {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    
    .card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin-bottom: 1rem;
        border-left: 4px solid #1e3c72;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
    }
    
    .success-card {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
    }
    
    .warning-card {
        background: linear-gradient(135deg, #f46b45 0%, #eea849 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 5px;
        font-weight: bold;
        width: 100%;
    }
    
    .stButton > button:hover {
        background: linear-gradient(135deg, #2a5298 0%, #3a62a8 100%);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(42, 82, 152, 0.3);
    }
    
    /* Transaction list styling */
    .transaction-positive {
        background: rgba(0, 200, 83, 0.1);
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 3px solid #00c853;
        margin: 0.25rem 0;
    }
    
    .transaction-negative {
        background: rgba(255, 82, 82, 0.1);
        padding: 0.5rem;
        border-radius: 5px;
        border-left: 3px solid #ff5252;
        margin: 0.25rem 0;
    }
    
    /* OTP display styling */
    .otp-display {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 15px;
        text-align: center;
        margin: 2rem 0;
        border: 3px solid white;
        box-shadow: 0 10px 30px rgba(0,0,0,0.2);
    }
    
    .otp-number {
        font-size: 3.5rem;
        font-weight: bold;
        letter-spacing: 15px;
        margin: 1rem 0;
        font-family: 'Courier New', monospace;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .whatsapp-sim {
        background: #25D366;
        color: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border-left: 5px solid #128C7E;
    }
    
    /* Hide Streamlit default elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .st-emotion-cache-1y4p8pa {padding: 2rem 1rem;}
</style>
""", unsafe_allow_html=True)

# ---------------- DATABASE INITIALIZATION ----------------
def initialize_database():
    """Initialize database with proper schema"""
    conn = sqlite3.connect("united_union_bank.db", check_same_thread=False)
    c = conn.cursor()
    
    # Create users table with all columns
    c.execute("""
        CREATE TABLE IF NOT EXISTS users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password BLOB,
            full_name TEXT,
            email TEXT,
            phone TEXT,
            account_number TEXT UNIQUE,
            created_at TEXT
        )
    """)
    
    # Check and add missing columns to users table
    c.execute("PRAGMA table_info(users)")
    existing_columns = [col[1] for col in c.fetchall()]
    
    # List of columns that should exist
    required_columns = [
        ("full_name", "TEXT"),
        ("email", "TEXT"),
        ("phone", "TEXT"),
        ("account_number", "TEXT UNIQUE"),
        ("created_at", "TEXT")
    ]
    
    for column_name, column_type in required_columns:
        if column_name not in existing_columns:
            try:
                c.execute(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}")
            except:
                pass
    
    # Create wallets table
    c.execute("""
        CREATE TABLE IF NOT EXISTS wallets(
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            last_updated TEXT
        )
    """)
    
    # Create transactions table
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender INTEGER,
            receiver INTEGER,
            amount REAL,
            type TEXT,
            description TEXT,
            time TEXT,
            status TEXT DEFAULT 'COMPLETED'
        )
    """)
    
    # Create virtual_cards table
    c.execute("""
        CREATE TABLE IF NOT EXISTS virtual_cards(
            user_id INTEGER,
            card_number TEXT,
            expiry_date TEXT,
            cvv TEXT,
            is_active INTEGER DEFAULT 1
        )
    """)
    
    conn.commit()
    return conn, c

# Initialize database
conn, c = initialize_database()

# ---------------- HELPERS ----------------
def generate_account_number():
    return f"UU{random.randint(10000000, 99999999)}"

def hash_pass(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def check_pass(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed)

def get_user(username):
    c.execute("SELECT * FROM users WHERE username=?", (username,))
    return c.fetchone()

def get_user_by_id(user_id):
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    return c.fetchone()

def get_balance(user_id):
    c.execute("SELECT balance FROM wallets WHERE user_id=?", (user_id,))
    result = c.fetchone()
    return result[0] if result else 0

def update_balance(user_id, amount):
    c.execute("UPDATE wallets SET balance=?, last_updated=? WHERE user_id=?",
              (amount, datetime.now().isoformat(), user_id))
    conn.commit()

def log_transaction(sender, receiver, amount, trans_type, description="", status="COMPLETED"):
    c.execute("""
        INSERT INTO transactions 
        (sender, receiver, amount, type, description, time, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (sender, receiver, amount, trans_type, description, datetime.now().isoformat(), status))
    conn.commit()

def generate_otp():
    return str(random.randint(100000, 999999))

def format_currency(amount):
    return f"₹{amount:,.2f}"

# ---------------- SESSION MANAGEMENT ----------------
if 'user' not in st.session_state:
    st.session_state.user = None
if 'otp' not in st.session_state:
    st.session_state.otp = None
if 'otp_time' not in st.session_state:
    st.session_state.otp_time = None
if 'temp_user' not in st.session_state:
    st.session_state.temp_user = None
if 'show_otp' not in st.session_state:
    st.session_state.show_otp = False

# ---------------- LOGO DISPLAY ----------------
def display_logo(size=100):
    """Display logo if available, otherwise show default icon"""
    try:
        if os.path.exists("logo.jpeg"):
            image = Image.open("logo.jpeg")
            image = image.resize((size, size))
            st.image(image)
            return True
        elif os.path.exists("logo.png"):
            image = Image.open("logo.png")
            image = image.resize((size, size))
            st.image(image)
            return True
        elif os.path.exists("logo.jpg"):
            image = Image.open("logo.jpg")
            image = image.resize((size, size))
            st.image(image)
            return True
        else:
            st.markdown(f'<div style="text-align: center; font-size: {size//2}px;">🏦</div>', unsafe_allow_html=True)
            return False
    except:
        st.markdown(f'<div style="text-align: center; font-size: {size//2}px;">🏦</div>', unsafe_allow_html=True)
        return False

# ---------------- OTP DISPLAY ----------------
def show_otp_display(otp, phone_number=None):
    """Display OTP prominently on screen"""
    st.markdown("""
    <div class="otp-display">
        <h2>🔐 Two-Factor Authentication</h2>
        <p>Your One-Time Password for United Union Bank</p>
        <div class="otp-number">""" + otp + """</div>
        <p>Enter this 6-digit code to continue</p>
        <p><small>Valid for 5 minutes</small></p>
    </div>
    """, unsafe_allow_html=True)
    
    # Simulate WhatsApp message
    if phone_number:
        st.markdown(f"""
        <div class="whatsapp-sim">
            <h4>📱 WhatsApp Simulation</h4>
            <div style="background: white; color: #333; padding: 15px; border-radius: 8px; margin: 10px 0;">
                <strong>From:</strong> United Union Bank<br>
                <strong>To:</strong> {phone_number}<br><br>
                🔐 Your verification code is: <strong>{otp}</strong><br>
                Valid for 5 minutes.<br><br>
                ⚠️ Do not share this code with anyone.
            </div>
            <small><i>In production, this would be sent via real WhatsApp/SMS</i></small>
        </div>
        """, unsafe_allow_html=True)
    
    # Copy to clipboard button
    st.markdown(f"""
    <script>
    function copyToClipboard(text) {{
        navigator.clipboard.writeText(text).then(function() {{
            alert('OTP copied to clipboard: ' + text);
        }}, function(err) {{
            console.error('Could not copy text: ', err);
        }});
    }}
    </script>
    <button onclick="copyToClipboard('{otp}')" style="
        background: linear-gradient(135deg, #25D366 0%, #128C7E 100%);
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        font-size: 16px;
        cursor: pointer;
        width: 100%;
        margin: 10px 0;">
        📋 Copy OTP to Clipboard
    </button>
    """, unsafe_allow_html=True)

# ---------------- AUTHENTICATION PAGE ----------------
def show_auth_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # Display logo
        display_logo(100)
        
        st.title("United Union Bank")
        st.markdown("<h4 style='text-align: center; color: #1e3c72;'>Secure Digital Banking • Trusted Worldwide</h4>", unsafe_allow_html=True)
    
    st.markdown('<div class="main-header">', unsafe_allow_html=True)
    st.markdown('<h3 style="text-align: center; margin: 0;">Welcome to Secure Banking</h3>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # If OTP is generated, show OTP verification page
    if st.session_state.otp and not st.session_state.user:
        show_otp_verification_page()
        return
    
    # Otherwise show login/signup tabs
    tab1, tab2 = st.tabs(["🔐 **Login to Your Account**", "📝 **Create New Account**"])
    
    with tab1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("Welcome Back")
            username = st.text_input("Username", key="login_user")
            password = st.text_input("Password", type="password", key="login_pass")
            
            if st.button("Secure Login", key="login_btn", type="primary"):
                if username and password:
                    user = get_user(username)
                    if user and check_pass(password, user[2]):
                        st.session_state.temp_user = user
                        st.session_state.otp = generate_otp()
                        st.session_state.otp_time = time.time()
                        
                        # Show success message and OTP
                        st.success("✅ Login credentials verified!")
                        
                        # Get user's phone for simulation
                        phone_number = user[5] if user[5] else "+91XXXXXXXXXX"
                        
                        # Display OTP prominently
                        show_otp_display(st.session_state.otp, phone_number)
                        
                        st.info("🔒 **Security Note:** In production, this OTP would be sent via WhatsApp/SMS. For this demo, it's shown on screen.")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials. Please try again.")
                else:
                    st.warning("⚠️ Please enter both username and password")
        
        with col2:
            st.markdown("### Security Features")
            st.markdown("""
            - 🔒 **256-bit Encryption**
            - 🔐 **Two-Factor Authentication**
            - 🛡️ **Fraud Detection**
            - 📱 **Real-time Alerts**
            - 🔄 **Instant Transfers**
            - 🌍 **Global Access**
            """)
            
            st.markdown("---")
            st.markdown("### Demo Instructions")
            st.markdown("""
            1. Enter username & password
            2. Click **Secure Login**
            3. **Copy the OTP** shown on screen
            4. **Paste OTP** in verification page
            5. Access your dashboard
            """)
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Open Your Account")
        
        col1, col2 = st.columns(2)
        with col1:
            full_name = st.text_input("Full Name", placeholder="John Doe")
            username = st.text_input("Choose Username", placeholder="johndoe")
            password = st.text_input("Password", type="password")
        
        with col2:
            email = st.text_input("Email Address", placeholder="john@example.com")
            phone = st.text_input("Phone Number", placeholder="+919876543210")
            confirm_pass = st.text_input("Confirm Password", type="password")
        
        st.markdown("---")
        st.markdown("**Demo Note:** For testing, use any phone number format. OTP will be displayed on screen.")
        
        if st.button("Create Account", key="signup_btn", type="primary"):
            if not all([full_name, username, password, email, phone]):
                st.error("❌ Please fill all fields")
            elif password != confirm_pass:
                st.error("❌ Passwords do not match!")
            elif get_user(username):
                st.error("❌ Username already exists!")
            else:
                account_number = generate_account_number()
                c.execute("""
                    INSERT INTO users 
                    (username, password, full_name, email, phone, account_number, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (username, hash_pass(password), full_name, email, phone, 
                     account_number, datetime.now().isoformat()))
                
                user_id = c.lastrowid
                c.execute("INSERT INTO wallets (user_id, last_updated) VALUES (?, ?)",
                         (user_id, datetime.now().isoformat()))
                conn.commit()
                
                st.success(f"""
                ✅ **Account created successfully!**
                
                **Account Details:**
                - **Account Number:** `{account_number}`
                - **Username:** `{username}`
                - **Full Name:** {full_name}
                - **Created:** {datetime.now().strftime('%Y-%m-%d %H:%M')}
                
                **Next Steps:**
                1. **Save your account number**
                2. **Login with your credentials**
                3. **OTP will be displayed on screen**
                """)
        st.markdown('</div>', unsafe_allow_html=True)

def show_otp_verification_page():
    """Show OTP verification page with OTP displayed prominently"""
    st.markdown('<div class="card">', unsafe_allow_html=True)
    
    # Show OTP at the top
    show_otp_display(st.session_state.otp)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([3, 1, 1])
    
    with col1:
        st.subheader("Enter OTP to Continue")
        otp_input = st.text_input("Enter 6-digit OTP", 
                                 max_chars=6, 
                                 placeholder="Enter the code above",
                                 key="otp_input_field",
                                 label_visibility="collapsed")
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("✅ Verify OTP", type="primary", use_container_width=True):
            if otp_input == st.session_state.otp:
                if time.time() - st.session_state.otp_time < 300:  # 5 minutes
                    st.session_state.user = st.session_state.temp_user
                    st.session_state.otp = None
                    st.success("✅ OTP Verified! Redirecting to dashboard...")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("❌ OTP has expired. Please login again.")
            else:
                st.error("❌ Invalid OTP. Please check and try again.")
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 New OTP", use_container_width=True):
            st.session_state.otp = generate_otp()
            st.session_state.otp_time = time.time()
            st.success("🔄 New OTP generated!")
            st.rerun()
    
    # Timer display
    time_left = 300 - (time.time() - st.session_state.otp_time)
    if time_left > 0:
        minutes = int(time_left // 60)
        seconds = int(time_left % 60)
        
        # Create progress bar
        progress = time_left / 300
        st.progress(progress)
        
        # Color based on time left
        if time_left > 120:
            color = "green"
        elif time_left > 60:
            color = "orange"
        else:
            color = "red"
            
        st.markdown(f"<p style='color: {color}; text-align: center;'><b>Time remaining: {minutes}:{seconds:02d}</b></p>", unsafe_allow_html=True)
    else:
        st.error("⏰ OTP expired! Please go back and login again.")
        if st.button("← Back to Login"):
            st.session_state.otp = None
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Help section
    with st.expander("❓ Need Help?"):
        st.markdown("""
        **Troubleshooting:**
        1. **OTP not visible?** - Scroll up to see the large OTP display
        2. **OTP expired?** - Click "New OTP" button
        3. **Wrong OTP?** - Make sure you're entering the 6-digit number shown above
        4. **Copy OTP** - Click the green "Copy OTP to Clipboard" button
        
        **Demo Note:** In a real banking app, OTP would be sent via WhatsApp/SMS. 
        This demo shows it on screen for testing purposes.
        """)

# ---------------- DASHBOARD PAGE ----------------
def show_dashboard():
    user_id = st.session_state.user[0]
    username = st.session_state.user[1]
    full_name = st.session_state.user[3] if st.session_state.user[3] else username
    account_number = st.session_state.user[6] if st.session_state.user[6] else "Not assigned"
    balance = get_balance(user_id)
    
    # Sidebar with logo and navigation
    with st.sidebar:
        # Display logo
        display_logo(80)
        
        st.markdown(f"""
        <div class="card">
            <h4>👤 {full_name}</h4>
            <p>📋 {account_number}</p>
            <p>💳 Member Since: {st.session_state.user[7][:10] if st.session_state.user[7] else 'N/A'}</p>
            <hr>
        </div>
        """, unsafe_allow_html=True)
        
        menu_option = st.radio(
            "Navigation",
            ["📊 Dashboard", "💰 Deposit", "🔁 Transfer", "💳 Cards", 
             "📈 Analytics", "🌍 Currency", "🧾 Statements", "⚙️ Settings", "🚪 Logout"],
            label_visibility="collapsed"
        )
    
    # Header
    st.markdown(f'<div class="main-header">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.markdown(f"### 👋 Welcome back, {full_name}")
        st.markdown(f"**Account:** {account_number} | **Member Since:** {st.session_state.user[7][:10] if st.session_state.user[7] else 'N/A'}")
    
    with col2:
        st.markdown("### Available Balance")
        st.markdown(f'<h1 style="color:white">{format_currency(balance)}</h1>', unsafe_allow_html=True)
    
    with col3:
        st.markdown("### Quick Actions")
        if st.button("🔄 Refresh Data"):
            st.rerun()
        if st.button("📱 Contact Support"):
            st.info("📞 Support: 1800-123-4567")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Main content based on menu selection
    if menu_option == "📊 Dashboard":
        show_dashboard_home(user_id, balance)
    elif menu_option == "💰 Deposit":
        show_deposit_page(user_id, balance)
    elif menu_option == "🔁 Transfer":
        show_transfer_page(user_id, balance)
    elif menu_option == "💳 Cards":
        show_cards_page(user_id)
    elif menu_option == "📈 Analytics":
        show_analytics_page(user_id)
    elif menu_option == "🌍 Currency":
        show_currency_page()
    elif menu_option == "🧾 Statements":
        show_statements_page(user_id)
    elif menu_option == "⚙️ Settings":
        show_settings_page()
    elif menu_option == "🚪 Logout":
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("✅ Logged out successfully!")
        time.sleep(1)
        st.rerun()

def show_dashboard_home(user_id, balance):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### 💰 Balance")
        st.markdown(f"## {format_currency(balance)}")
        st.markdown("Available for withdrawal")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### 📊 This Month")
        c.execute("""
            SELECT SUM(amount) FROM transactions 
            WHERE receiver=? AND strftime('%m', time) = strftime('%m', 'now')
            AND type='DEPOSIT'
        """, (user_id,))
        monthly_deposit = c.fetchone()[0] or 0
        st.markdown(f"## {format_currency(monthly_deposit)}")
        st.markdown("Total deposits")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col3:
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.markdown("### 🔄 Transactions")
        c.execute("SELECT COUNT(*) FROM transactions WHERE sender=? OR receiver=?", (user_id, user_id))
        total_tx = c.fetchone()[0]
        st.markdown(f"## {total_tx}")
        st.markdown("Total transactions")
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Recent Transactions
    st.markdown("### 📋 Recent Transactions")
    c.execute("""
        SELECT t.amount, t.type, t.description, t.time,
               CASE 
                   WHEN t.sender = ? THEN 'sent'
                   WHEN t.receiver = ? THEN 'received'
               END as direction
        FROM transactions t
        WHERE (t.sender=? OR t.receiver=?)
        ORDER BY t.time DESC LIMIT 10
    """, (user_id, user_id, user_id, user_id))
    
    transactions = c.fetchall()
    
    if transactions:
        for tx in transactions:
            amount, tx_type, desc, tx_time, direction = tx
            if tx_type == "DEPOSIT" or direction == "received":
                css_class = "transaction-positive"
                prefix = "+"
                icon = "📥"
            else:
                css_class = "transaction-negative"
                prefix = "-"
                icon = "📤"
            
            display_desc = f"{icon} {desc or tx_type} ({direction})"
            
            st.markdown(f"""
            <div class="{css_class}">
                <strong>{display_desc}</strong><br>
                <small>{tx_time[:19]}</small>
                <div style="float: right; font-weight: bold;">
                    {prefix}{format_currency(amount)}
                </div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("📭 No transactions yet. Make your first deposit or transfer!")

def show_deposit_page(user_id, current_balance):
    st.markdown("### 💰 Deposit Funds")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        amount = st.number_input("Deposit Amount", min_value=100.0, max_value=1000000.0, value=1000.0, step=100.0)
        description = st.text_input("Description (Optional)", placeholder="e.g., Salary, Freelance Payment, Gift")
        
        if st.button("Process Deposit", type="primary"):
            new_balance = current_balance + amount
            update_balance(user_id, new_balance)
            log_transaction(None, user_id, amount, "DEPOSIT", description)
            
            st.success(f"""
            ✅ **Deposit Successful!**
            
            **Details:**
            - **Amount:** {format_currency(amount)}
            - **New Balance:** {format_currency(new_balance)}
            - **Transaction ID:** TX{int(time.time())}
            - **Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            - **Status:** Completed
            
            Funds are available immediately.
            """)
            time.sleep(2)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="success-card">', unsafe_allow_html=True)
        st.markdown("### 💡 Deposit Tips")
        st.markdown("""
        - **Minimum deposit:** ₹100
        - **Instant credit** to account
        - **No hidden fees**
        - **24/7 deposit facility**
        - **Secure & encrypted**
        - **Email notification**
        """)
        st.markdown('</div>', unsafe_allow_html=True)

def show_transfer_page(user_id, current_balance):
    st.markdown("### 🔁 Transfer Funds")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        recipient = st.text_input("Recipient Username", placeholder="Enter username")
        amount = st.number_input("Transfer Amount", min_value=1.0, max_value=current_balance, value=100.0)
        description = st.text_input("Description", placeholder="e.g., Rent, Dinner, Shared expenses")
        
        if st.button("Verify & Transfer", type="primary"):
            if not recipient:
                st.error("❌ Please enter recipient username")
            elif amount > current_balance:
                st.error("❌ Insufficient funds!")
            else:
                recipient_user = get_user(recipient)
                
                if not recipient_user:
                    st.error("❌ Recipient not found!")
                elif recipient_user[0] == user_id:
                    st.error("❌ Cannot transfer to yourself!")
                else:
                    # Update balances
                    recipient_balance = get_balance(recipient_user[0])
                    update_balance(user_id, current_balance - amount)
                    update_balance(recipient_user[0], recipient_balance + amount)
                    
                    # Log transaction
                    log_transaction(user_id, recipient_user[0], amount, "TRANSFER", description)
                    
                    st.success(f"""
                    ✅ **Transfer Successful!**
                    
                    **Details:**
                    - **To:** {recipient_user[3] or recipient_user[1]}
                    - **Amount:** {format_currency(amount)}
                    - **New Balance:** {format_currency(current_balance - amount)}
                    - **Reference:** TX{int(time.time())}
                    - **Time:** {datetime.now().strftime('%H:%M:%S')}
                    
                    Recipient will receive funds immediately.
                    """)
                    time.sleep(2)
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown('<div class="warning-card">', unsafe_allow_html=True)
        st.markdown("### ⚠️ Transfer Limits")
        st.markdown("""
        - **Daily limit:** ₹50,000
        - **Per transaction:** ₹25,000
        - **Real-time processing**
        - **Instant notification**
        - **Secure encryption**
        - **24/7 availability**
        """)
        st.markdown('</div>', unsafe_allow_html=True)

def show_cards_page(user_id):
    st.markdown("### 💳 Virtual Cards")
    
    # Check if user has a card
    c.execute("SELECT * FROM virtual_cards WHERE user_id=? AND is_active=1", (user_id,))
    existing_card = c.fetchone()
    
    if existing_card:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.markdown(f"""
            #### Your Virtual Card Details
            **Card Number:** `{existing_card[1]}`
            **Expiry Date:** {existing_card[2]}
            **CVV:** `{existing_card[3]}`
            
            *Linked to your main account*
            *For online purchases only*
            """)
            
            if st.button("Generate New Card", type="secondary"):
                c.execute("UPDATE virtual_cards SET is_active=0 WHERE user_id=?", (user_id,))
                conn.commit()
                st.success("✅ Old card deactivated. Generating new card...")
                time.sleep(1)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("### Generate New Virtual Card")
        st.info("Create a secure virtual card for online purchases.")
        
        if st.button("Generate New Virtual Card", type="primary"):
            card_number = f"4111 {random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)}"
            expiry = f"{random.randint(1,12):02d}/{(datetime.now().year + 3) % 100:02d}"
            cvv = f"{random.randint(100,999)}"
            
            c.execute("INSERT INTO virtual_cards VALUES (?, ?, ?, ?, ?)",
                     (user_id, card_number, expiry, cvv, 1))
            conn.commit()
            st.success("✅ New virtual card generated successfully!")
            time.sleep(2)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

def show_analytics_page(user_id):
    st.markdown("### 📈 Financial Analytics")
    
    # Get transaction data
    c.execute("""
        SELECT date(time) as date, type, SUM(amount) as total
        FROM transactions 
        WHERE sender=? OR receiver=?
        GROUP BY date(time), type
        ORDER BY date(time)
    """, (user_id, user_id))
    
    data = c.fetchall()
    
    if data:
        df = pd.DataFrame(data, columns=["Date", "Type", "Amount"])
        
        # Create visualization
        fig = px.bar(df, x="Date", y="Amount", color="Type",
                     title="Transaction History",
                     color_discrete_map={"DEPOSIT": "#00c853", "TRANSFER": "#ff5252"})
        st.plotly_chart(fig, use_container_width=True)
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            total_deposits = df[df["Type"] == "DEPOSIT"]["Amount"].sum()
            st.metric("💰 Total Deposits", format_currency(total_deposits))
        with col2:
            total_transfers = df[df["Type"] == "TRANSFER"]["Amount"].sum()
            st.metric("🔁 Total Transfers", format_currency(total_transfers))
        with col3:
            st.metric("📊 Transaction Count", len(df))
    else:
        st.info("📊 No transaction data available yet.")

def show_currency_page():
    st.markdown("### 🌍 Currency Converter")
    
    # Exchange rates
    exchange_rates = {
        "INR (₹)": 1.0,
        "USD ($)": 83.0,
        "EUR (€)": 89.5,
        "GBP (£)": 105.2,
        "AED (د.إ)": 22.6,
        "PKR (₨)": 0.30
    }
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        amount = st.number_input("Amount", min_value=1.0, value=1000.0)
        
        col_from, col_to = st.columns(2)
        with col_from:
            from_currency = st.selectbox("From", list(exchange_rates.keys()))
        with col_to:
            to_currency = st.selectbox("To", list(exchange_rates.keys()))
        
        if from_currency and to_currency and amount > 0:
            in_inr = amount * exchange_rates[from_currency]
            converted = in_inr / exchange_rates[to_currency]
            
            st.markdown(f"""
            ### 💱 Conversion Result
            
            <div style="text-align: center; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
            border-radius: 10px; color: white; margin: 20px 0;">
                <h2>{amount:,.2f} {from_currency.split()[0]} =</h2>
                <h1>{converted:,.2f} {to_currency.split()[0]}</h1>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 📊 Live Exchange Rates")
        
        # Create rates table
        rates_data = []
        for currency, rate in exchange_rates.items():
            if currency != "INR (₹)":
                rates_data.append({
                    "Currency": currency,
                    "Rate (per ₹1)": f"{1/rate:.4f}"
                })
        
        rates_df = pd.DataFrame(rates_data)
        st.dataframe(rates_df, hide_index=True, use_container_width=True)

def show_statements_page(user_id):
    st.markdown("### 🧾 Account Statements")
    
    # Date range selector
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("From Date", value=datetime.now() - timedelta(days=30))
    with col2:
        end_date = st.date_input("To Date", value=datetime.now())
    
    if st.button("Generate Statement", type="primary", icon="📥"):
        # Get transactions
        c.execute("""
            SELECT t.time, t.type, t.amount, t.description
            FROM transactions t
            WHERE (t.sender=? OR t.receiver=?)
            AND date(t.time) BETWEEN ? AND ?
            ORDER BY t.time DESC
        """, (user_id, user_id, start_date, end_date))
        
        transactions = c.fetchall()
        
        if transactions:
            # Create PDF
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(0, 10, "United Union Bank - Account Statement", ln=True, align='C')
            
            pdf.set_font("Arial", '', 12)
            user = get_user_by_id(user_id)
            pdf.cell(0, 10, f"Account Holder: {user[3] if user and user[3] else user[1]}", ln=True)
            pdf.cell(0, 10, f"Account Number: {user[6] if user and user[6] else 'N/A'}", ln=True)
            pdf.cell(0, 10, f"Statement Period: {start_date} to {end_date}", ln=True)
            pdf.cell(0, 10, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
            pdf.ln(10)
            
            # Table header
            pdf.set_fill_color(200, 220, 255)
            pdf.cell(40, 10, "Date", 1, 0, 'C', 1)
            pdf.cell(30, 10, "Type", 1, 0, 'C', 1)
            pdf.cell(60, 10, "Description", 1, 0, 'C', 1)
            pdf.cell(40, 10, "Amount", 1, 1, 'C', 1)
            
            # Table rows
            pdf.set_fill_color(245, 245, 245)
            fill = False
            for tx in transactions:
                fill = not fill
                pdf.cell(40, 10, tx[0][:10], 1, 0, 'C', fill)
                pdf.cell(30, 10, tx[1], 1, 0, 'C', fill)
                pdf.cell(60, 10, tx[3] or "-", 1, 0, 'C', fill)
                amount_str = f"+₹{tx[2]:,.2f}" if tx[1] == "DEPOSIT" else f"-₹{tx[2]:,.2f}"
                pdf.cell(40, 10, amount_str, 1, 1, 'R', fill)
            
            pdf_filename = f"statement_{int(time.time())}.pdf"
            pdf.output(pdf_filename)
            
            # Download button
            with open(pdf_filename, "rb") as file:
                st.download_button(
                    label="📥 Download PDF Statement",
                    data=file,
                    file_name=f"UU_Statement_{start_date}_{end_date}.pdf",
                    mime="application/pdf",
                    type="primary"
                )
            
            # Clean up
            try:
                os.remove(pdf_filename)
            except:
                pass
        else:
            st.info("📭 No transactions in the selected period.")

def show_settings_page():
    st.markdown("### ⚙️ Account Settings")
    
    tab1, tab2, tab3 = st.tabs(["👤 Profile", "🔒 Security", "ℹ️ About"])
    
    with tab1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### Personal Information")
        
        current_user = st.session_state.user
        
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Full Name", value=current_user[3] or "Not set", disabled=True)
            st.text_input("Username", value=current_user[1], disabled=True)
        
        with col2:
            st.text_input("Email", value=current_user[4] or "Not set", disabled=True)
            st.text_input("Phone", value=current_user[5] or "Not set", disabled=True)
        
        st.text_input("Account Number", value=current_user[6] or "Not set", disabled=True)
        st.text_input("Member Since", value=current_user[7][:10] if current_user[7] else "N/A", disabled=True)
        
        st.info("📝 Contact customer support to update your profile.")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### Security Settings")
        
        st.markdown("##### 🔐 Two-Factor Authentication")
        st.info("✅ **Status:** Active (OTP shown on screen for demo)")
        
        st.markdown("##### Change Password")
        current_pass = st.text_input("Current Password", type="password")
        new_pass = st.text_input("New Password", type="password")
        confirm_pass = st.text_input("Confirm New Password", type="password")
        
        if st.button("Update Password", type="primary"):
            st.success("✅ Password update request sent to your email!")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    with tab3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### About United Union Bank")
        
        st.markdown("""
        **United Union Bank** - Secure Digital Banking
        
        ##### Demo Features:
        - 🔐 **Two-Factor Authentication** (OTP on screen)
        - 💰 **Deposit & Transfer funds**
        - 💳 **Virtual cards**
        - 📈 **Analytics dashboard**
        - 🌍 **Currency converter**
        - 🧾 **PDF statements**
        
        ##### Contact:
        - 📞 **Support:** 1800-123-4567
        - 📧 **Email:** support@unitedunionbank.com
        
        *Version 2.0.0 | Demo Mode*
        """)
        st.markdown('</div>', unsafe_allow_html=True)

# ---------------- MAIN APP LOGIC ----------------
def main():
    if st.session_state.user:
        show_dashboard()
    else:
        show_auth_page()

if __name__ == "__main__":
    main()