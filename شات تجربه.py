import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, font
import threading
import socket
import json
import hashlib
import datetime
import time
import os
import sqlite3
from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum
import queue

# ======================== إعدادات التطبيق ========================

class MessageType(Enum):
    TEXT = "text"
    IMAGE = "image"
    FILE = "file"
    VOICE = "voice"
    VIDEO = "video"

class UserStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    AWAY = "away"
    BUSY = "busy"

@dataclass
class User:
    """فئة المستخدم"""
    id: int
    username: str
    email: str
    password_hash: str
    status: UserStatus = UserStatus.OFFLINE
    avatar: str = ""
    last_seen: datetime.datetime = None
    contacts: List[int] = None

@dataclass
class Message:
    """فئة الرسالة"""
    id: int
    sender_id: int
    receiver_id: int
    content: str
    type: MessageType = MessageType.TEXT
    timestamp: datetime.datetime = None
    read: bool = False
    delivered: bool = False
    file_path: str = ""

@dataclass
class Chat:
    """فئة المحادثة"""
    id: int
    participants: List[int]
    last_message: Message = None
    updated_at: datetime.datetime = None
    unread_count: Dict[int, int] = None

# ======================== قاعدة البيانات ========================

class Database:
    """فئة إدارة قاعدة البيانات"""
    
    def __init__(self, db_name="chatme.db"):
        self.db_name = db_name
        self.init_database()
    
    def get_connection(self):
        """إنشاء اتصال بقاعدة البيانات"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """تهيئة قاعدة البيانات وإنشاء الجداول"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # جدول المستخدمين
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                status TEXT DEFAULT 'offline',
                avatar TEXT DEFAULT '',
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # جدول جهات الاتصال
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                user_id INTEGER,
                contact_id INTEGER,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (contact_id) REFERENCES users(id),
                PRIMARY KEY (user_id, contact_id)
            )
        ''')
        
        # جدول الرسائل
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sender_id INTEGER NOT NULL,
                receiver_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                type TEXT DEFAULT 'text',
                file_path TEXT DEFAULT '',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                read BOOLEAN DEFAULT 0,
                delivered BOOLEAN DEFAULT 0,
                FOREIGN KEY (sender_id) REFERENCES users(id),
                FOREIGN KEY (receiver_id) REFERENCES users(id)
            )
        ''')
        
        # جدول المحادثات
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                last_message_id INTEGER,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (last_message_id) REFERENCES messages(id)
            )
        ''')
        
        # جدول المشاركين في المحادثة
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_participants (
                chat_id INTEGER,
                user_id INTEGER,
                unread_count INTEGER DEFAULT 0,
                FOREIGN KEY (chat_id) REFERENCES chats(id),
                FOREIGN KEY (user_id) REFERENCES users(id),
                PRIMARY KEY (chat_id, user_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_user(self, username, email, password):
        """إنشاء مستخدم جديد"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        try:
            cursor.execute('''
                INSERT INTO users (username, email, password_hash)
                VALUES (?, ?, ?)
            ''', (username, email, password_hash))
            conn.commit()
            user_id = cursor.lastrowid
            conn.close()
            return user_id
        except sqlite3.IntegrityError:
            conn.close()
            return None
    
    def verify_user(self, email, password):
        """التحقق من بيانات المستخدم"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        cursor.execute('''
            SELECT * FROM users WHERE email = ? AND password_hash = ?
        ''', (email, password_hash))
        
        user = cursor.fetchone()
        conn.close()
        
        if user:
            return dict(user)
        return None
    
    def get_user_by_id(self, user_id):
        """الحصول على مستخدم بواسطة المعرف"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        return dict(user) if user else None
    
    def get_user_by_username(self, username):
        """الحصول على مستخدم بواسطة اسم المستخدم"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()
        
        return dict(user) if user else None
    
    def search_users(self, query, current_user_id):
        """البحث عن المستخدمين"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, username, email, status, avatar 
            FROM users 
            WHERE (username LIKE ? OR email LIKE ?) AND id != ?
            LIMIT 20
        ''', (f'%{query}%', f'%{query}%', current_user_id))
        
        users = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return users
    
    def add_contact(self, user_id, contact_id):
        """إضافة جهة اتصال"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO contacts (user_id, contact_id)
                VALUES (?, ?)
            ''', (user_id, contact_id))
            conn.commit()
            success = True
        except sqlite3.IntegrityError:
            success = False
        
        conn.close()
        return success
    
    def get_contacts(self, user_id):
        """الحصول على جهات اتصال المستخدم"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.* FROM users u
            JOIN contacts c ON u.id = c.contact_id
            WHERE c.user_id = ?
        ''', (user_id,))
        
        contacts = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return contacts
    
    def save_message(self, sender_id, receiver_id, content, msg_type="text", file_path=""):
        """حفظ رسالة جديدة"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO messages (sender_id, receiver_id, content, type, file_path)
            VALUES (?, ?, ?, ?, ?)
        ''', (sender_id, receiver_id, content, msg_type, file_path))
        
        message_id = cursor.lastrowid
        conn.commit()
        
        # تحديث أو إنشاء محادثة
        self.update_chat(sender_id, receiver_id, message_id)
        
        conn.close()
        return message_id
    
    def update_chat(self, user1_id, user2_id, last_message_id):
        """تحديث المحادثة بين مستخدمين"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # البحث عن محادثة موجودة
        cursor.execute('''
            SELECT c.id FROM chats c
            JOIN chat_participants cp1 ON c.id = cp1.chat_id
            JOIN chat_participants cp2 ON c.id = cp2.chat_id
            WHERE cp1.user_id = ? AND cp2.user_id = ?
        ''', (user1_id, user2_id))
        
        chat = cursor.fetchone()
        
        if chat:
            # تحديث المحادثة الموجودة
            chat_id = chat[0]
            cursor.execute('''
                UPDATE chats 
                SET last_message_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (last_message_id, chat_id))
        else:
            # إنشاء محادثة جديدة
            cursor.execute('''
                INSERT INTO chats (last_message_id) VALUES (?)
            ''', (last_message_id,))
            chat_id = cursor.lastrowid
            
            # إضافة المشاركين
            cursor.execute('''
                INSERT INTO chat_participants (chat_id, user_id) VALUES (?, ?)
            ''', (chat_id, user1_id))
            cursor.execute('''
                INSERT INTO chat_participants (chat_id, user_id) VALUES (?, ?)
            ''', (chat_id, user2_id))
        
        # تحديث عدد الرسائل غير المقروءة للمستلم
        cursor.execute('''
            UPDATE chat_participants 
            SET unread_count = unread_count + 1
            WHERE chat_id = ? AND user_id = ?
        ''', (chat_id, user2_id))
        
        conn.commit()
        conn.close()
        return chat_id
    
    def get_messages(self, user1_id, user2_id, limit=50):
        """الحصول على الرسائل بين مستخدمين"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM messages 
            WHERE (sender_id = ? AND receiver_id = ?) 
               OR (sender_id = ? AND receiver_id = ?)
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (user1_id, user2_id, user2_id, user1_id, limit))
        
        messages = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return list(reversed(messages))  # عكس الترتيب ليصبح تصاعدياً
    
    def get_chats(self, user_id):
        """الحصول على محادثات المستخدم"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.id, c.last_message_id, c.updated_at,
                   cp.unread_count,
                   u.id as other_user_id, u.username, u.status, u.avatar,
                   m.content as last_message_content, m.timestamp as last_message_time,
                   m.type as last_message_type
            FROM chats c
            JOIN chat_participants cp ON c.id = cp.chat_id
            JOIN chat_participants cp2 ON c.id = cp2.chat_id AND cp2.user_id != ?
            JOIN users u ON cp2.user_id = u.id
            LEFT JOIN messages m ON c.last_message_id = m.id
            WHERE cp.user_id = ?
            ORDER BY c.updated_at DESC
        ''', (user_id, user_id))
        
        chats = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return chats
    
    def mark_messages_as_read(self, user_id, sender_id):
        """تحديد الرسائل كمقروءة"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE messages 
            SET read = 1 
            WHERE sender_id = ? AND receiver_id = ? AND read = 0
        ''', (sender_id, user_id))
        
        # إعادة تعيين عدد الرسائل غير المقروءة
        cursor.execute('''
            UPDATE chat_participants 
            SET unread_count = 0
            WHERE user_id = ? AND chat_id IN (
                SELECT c.id FROM chats c
                JOIN chat_participants cp ON c.id = cp.chat_id
                WHERE cp.user_id = ? AND c.id IN (
                    SELECT chat_id FROM chat_participants WHERE user_id = ?
                )
            )
        ''', (user_id, user_id, sender_id))
        
        conn.commit()
        conn.close()
    
    def update_user_status(self, user_id, status):
        """تحديث حالة المستخدم"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET status = ?, last_seen = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, user_id))
        
        conn.commit()
        conn.close()

# ======================== خادم الدردشة ========================

class ChatServer:
    """خادم الدردشة الرئيسي"""
    
    def __init__(self, host='localhost', port=9999):
        self.host = host
        self.port = port
        self.server_socket = None
        self.clients = {}  # {user_id: (socket, address)}
        self.running = False
        self.db = Database()
        self.message_queue = queue.Queue()
        
    def start(self):
        """بدء تشغيل الخادم"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            print(f"🚀 خادم Chat Me يعمل على {self.host}:{self.port}")
            
            # بدء معالجة الرسائل في خيط منفصل
            threading.Thread(target=self.process_messages, daemon=True).start()
            
            while self.running:
                client_socket, address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, address)).start()
                
        except Exception as e:
            print(f"❌ خطأ في تشغيل الخادم: {e}")
    
    def stop(self):
        """إيقاف الخادم"""
        self.running = False
        for client in self.clients.values():
            try:
                client[0].close()
            except:
                pass
        if self.server_socket:
            self.server_socket.close()
    
    def handle_client(self, client_socket, address):
        """معالجة اتصال عميل جديد"""
        try:
            while self.running:
                data = client_socket.recv(4096).decode('utf-8')
                if not data:
                    break
                
                message = json.loads(data)
                self.handle_message(client_socket, message)
                
        except Exception as e:
            print(f"خطأ في معالجة العميل: {e}")
        finally:
            self.remove_client(client_socket)
    
    def handle_message(self, client_socket, message):
        """معالجة الرسائل الواردة من العملاء"""
        msg_type = message.get('type')
        
        if msg_type == 'login':
            self.handle_login(client_socket, message)
        elif msg_type == 'logout':
            self.handle_logout(client_socket, message)
        elif msg_type == 'message':
            self.handle_chat_message(message)
        elif msg_type == 'typing':
            self.handle_typing(message)
        elif msg_type == 'read':
            self.handle_read_receipt(message)
        elif msg_type == 'get_contacts':
            self.send_contacts(client_socket, message)
        elif msg_type == 'search':
            self.handle_search(client_socket, message)
    
    def handle_login(self, client_socket, message):
        """معالجة تسجيل الدخول"""
        user_id = message.get('user_id')
        if user_id:
            self.clients[user_id] = (client_socket, message.get('address'))
            self.db.update_user_status(user_id, 'online')
            
            # إرسال تأكيد تسجيل الدخول
            response = {
                'type': 'login_success',
                'message': 'تم تسجيل الدخول بنجاح'
            }
            self.send_to_client(client_socket, response)
            
            # إخطار جهات الاتصال
            self.notify_contacts_status(user_id, 'online')
    
    def handle_logout(self, client_socket, message):
        """معالجة تسجيل الخروج"""
        user_id = message.get('user_id')
        if user_id:
            self.db.update_user_status(user_id, 'offline')
            self.notify_contacts_status(user_id, 'offline')
            self.remove_client(client_socket)
    
    def handle_chat_message(self, message):
        """معالجة رسالة دردشة"""
        sender_id = message['sender_id']
        receiver_id = message['receiver_id']
        content = message['content']
        msg_type = message.get('type', 'text')
        
        # حفظ الرسالة في قاعدة البيانات
        message_id = self.db.save_message(sender_id, receiver_id, content, msg_type)
        
        # إضافة معرف الرسالة
        message['id'] = message_id
        message['timestamp'] = str(datetime.datetime.now())
        
        # إرسال الرسالة إلى المستلم إذا كان متصلاً
        if receiver_id in self.clients:
            receiver_socket = self.clients[receiver_id][0]
            self.send_to_client(receiver_socket, message)
            
            # تأكيد التسليم
            delivery_confirmation = {
                'type': 'delivered',
                'message_id': message_id,
                'to': sender_id
            }
            if sender_id in self.clients:
                self.send_to_client(self.clients[sender_id][0], delivery_confirmation)
    
    def handle_typing(self, message):
        """معالجة حالة الكتابة"""
        sender_id = message['sender_id']
        receiver_id = message['receiver_id']
        is_typing = message['is_typing']
        
        if receiver_id in self.clients:
            typing_notification = {
                'type': 'typing',
                'user_id': sender_id,
                'is_typing': is_typing
            }
            self.send_to_client(self.clients[receiver_id][0], typing_notification)
    
    def handle_read_receipt(self, message):
        """معالجة تأكيد القراءة"""
        user_id = message['user_id']
        sender_id = message['sender_id']
        
        self.db.mark_messages_as_read(user_id, sender_id)
        
        # إخطار المرسل بأن الرسائل قد قرئت
        if sender_id in self.clients:
            read_receipt = {
                'type': 'read',
                'by': user_id
            }
            self.send_to_client(self.clients[sender_id][0], read_receipt)
    
    def send_contacts(self, client_socket, message):
        """إرسال قائمة جهات الاتصال"""
        user_id = message['user_id']
        contacts = self.db.get_contacts(user_id)
        
        # تحديث حالة كل جهة اتصال
        for contact in contacts:
            contact['online'] = contact['id'] in self.clients
        
        response = {
            'type': 'contacts_list',
            'contacts': contacts
        }
        self.send_to_client(client_socket, response)
    
    def handle_search(self, client_socket, message):
        """معالجة البحث عن مستخدمين"""
        query = message['query']
        user_id = message['user_id']
        
        users = self.db.search_users(query, user_id)
        
        # تحديث حالة كل مستخدم
        for user in users:
            user['online'] = user['id'] in self.clients
        
        response = {
            'type': 'search_results',
            'users': users
        }
        self.send_to_client(client_socket, response)
    
    def notify_contacts_status(self, user_id, status):
        """إخطار جهات الاتصال بتغيير الحالة"""
        contacts = self.db.get_contacts(user_id)
        
        notification = {
            'type': 'status_change',
            'user_id': user_id,
            'status': status,
            'last_seen': str(datetime.datetime.now())
        }
        
        for contact in contacts:
            if contact['id'] in self.clients:
                self.send_to_client(self.clients[contact['id']][0], notification)
    
    def send_to_client(self, client_socket, message):
        """إرسال رسالة إلى عميل معين"""
        try:
            client_socket.send(json.dumps(message).encode('utf-8'))
        except:
            pass
    
    def remove_client(self, client_socket):
        """إزالة عميل من القائمة"""
        for user_id, (sock, addr) in list(self.clients.items()):
            if sock == client_socket:
                del self.clients[user_id]
                self.db.update_user_status(user_id, 'offline')
                self.notify_contacts_status(user_id, 'offline')
                break

# ======================== عميل الدردشة (واجهة المستخدم) ========================

class ChatClient:
    """عميل الدردشة مع واجهة المستخدم"""
    
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Chat Me - تطبيق مراسلة فوري")
        self.window.geometry("1200x700")
        self.window.minsize(900, 600)
        
        # تعيين الأيقونة والألوان
        self.window.configure(bg='#f0f2f5')
        
        # متغيرات العميل
        self.current_user = None
        self.current_chat = None
        self.socket = None
        self.connected = False
        self.db = Database()
        self.message_queue = queue.Queue()
        
        # إعداد الخطوط
        self.setup_fonts()
        
        # إعداد واجهة المستخدم
        self.setup_ui()
        
        # بدء معالجة الرسائل
        self.window.after(100, self.process_messages)
        
    def setup_fonts(self):
        """إعداد الخطوط المستخدمة في التطبيق"""
        self.title_font = font.Font(family="Segoe UI", size=24, weight="bold")
        self.header_font = font.Font(family="Segoe UI", size=16, weight="bold")
        self.normal_font = font.Font(family="Segoe UI", size=12)
        self.small_font = font.Font(family="Segoe UI", size=10)
        
    def setup_ui(self):
        """إعداد واجهة المستخدم"""
        # الإطار الرئيسي
        self.main_frame = ttk.Frame(self.window)
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # شاشة تسجيل الدخول
        self.show_login_screen()
        
    def show_login_screen(self):
        """عرض شاشة تسجيل الدخول"""
        # تنظيف الإطار الرئيسي
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # إطار تسجيل الدخول
        login_frame = ttk.Frame(self.main_frame)
        login_frame.pack(expand=True)
        
        # الشعار
        logo_label = ttk.Label(login_frame, text="💬 Chat Me", font=self.title_font)
        logo_label.pack(pady=20)
        
        # نوت بوك للتبويب
        notebook = ttk.Notebook(login_frame)
        notebook.pack(pady=20, padx=40)
        
        # تبويب تسجيل الدخول
        login_tab = ttk.Frame(notebook)
        notebook.add(login_tab, text="تسجيل الدخول")
        
        ttk.Label(login_tab, text="البريد الإلكتروني:", font=self.normal_font).pack(pady=5)
        self.login_email = ttk.Entry(login_tab, width=30, font=self.normal_font)
        self.login_email.pack(pady=5)
        
        ttk.Label(login_tab, text="كلمة المرور:", font=self.normal_font).pack(pady=5)
        self.login_password = ttk.Entry(login_tab, width=30, font=self.normal_font, show="•")
        self.login_password.pack(pady=5)
        
        ttk.Button(login_tab, text="دخول", command=self.login).pack(pady=20)
        
        # تبويب إنشاء حساب
        register_tab = ttk.Frame(notebook)
        notebook.add(register_tab, text="إنشاء حساب جديد")
        
        ttk.Label(register_tab, text="اسم المستخدم:", font=self.normal_font).pack(pady=5)
        self.register_username = ttk.Entry(register_tab, width=30, font=self.normal_font)
        self.register_username.pack(pady=5)
        
        ttk.Label(register_tab, text="البريد الإلكتروني:", font=self.normal_font).pack(pady=5)
        self.register_email = ttk.Entry(register_tab, width=30, font=self.normal_font)
        self.register_email.pack(pady=5)
        
        ttk.Label(register_tab, text="كلمة المرور:", font=self.normal_font).pack(pady=5)
        self.register_password = ttk.Entry(register_tab, width=30, font=self.normal_font, show="•")
        self.register_password.pack(pady=5)
        
        ttk.Label(register_tab, text="تأكيد كلمة المرور:", font=self.normal_font).pack(pady=5)
        self.register_confirm = ttk.Entry(register_tab, width=30, font=self.normal_font, show="•")
        self.register_confirm.pack(pady=5)
        
        ttk.Button(register_tab, text="إنشاء حساب", command=self.register).pack(pady=20)
        
    def show_main_screen(self):
        """عرض الشاشة الرئيسية للتطبيق"""
        # تنظيف الإطار الرئيسي
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        
        # إنشاء إطار رئيسي منقسيم
        self.paned = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        self.paned.pack(fill=tk.BOTH, expand=True)
        
        # الإطار الجانبي (قائمة المحادثات)
        self.sidebar = ttk.Frame(self.paned, width=300)
        self.paned.add(self.sidebar, weight=1)
        
        # إطار الدردشة الرئيسي
        self.chat_frame = ttk.Frame(self.paned)
        self.paned.add(self.chat_frame, weight=3)
        
        self.setup_sidebar()
        self.setup_chat_area()
        
        # الاتصال بالخادم
        self.connect_to_server()
        
        # تحميل المحادثات
        self.load_chats()
        
    def setup_sidebar(self):
        """إعداد الشريط الجانبي"""
        # معلومات المستخدم
        user_frame = ttk.Frame(self.sidebar)
        user_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # صورة المستخدم وحالته
        avatar_frame = ttk.Frame(user_frame)
        avatar_frame.pack(side=tk.RIGHT, padx=5)
        
        avatar_label = ttk.Label(avatar_frame, text="👤", font=("Segoe UI", 30))
        avatar_label.pack()
        
        self.status_label = ttk.Label(avatar_frame, text="●", foreground="green")
        self.status_label.pack()
        
        # معلومات المستخدم
        info_frame = ttk.Frame(user_frame)
        info_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=10)
        
        ttk.Label(info_frame, text=self.current_user['username'], 
                 font=self.header_font).pack(anchor=tk.W)
        
        self.user_status_text = ttk.Label(info_frame, text="متصل", 
                                          font=self.small_font, foreground="green")
        self.user_status_text.pack(anchor=tk.W)
        
        # زر الإعدادات
        settings_btn = ttk.Button(user_frame, text="⚙️", command=self.show_settings, width=3)
        settings_btn.pack(side=tk.LEFT)
        
        # شريط البحث
        search_frame = ttk.Frame(self.sidebar)
        search_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(search_frame, text="🔍", font=self.normal_font).pack(side=tk.RIGHT)
        self.search_entry = ttk.Entry(search_frame, font=self.normal_font)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.bind('<KeyRelease>', self.search_users)
        
        # قائمة المحادثات
        chats_label = ttk.Label(self.sidebar, text="المحادثات", font=self.header_font)
        chats_label.pack(anchor=tk.W, padx=10, pady=5)
        
        # إطار القائمة مع سكرول
        list_frame = ttk.Frame(self.sidebar)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5)
        
        self.chats_canvas = tk.Canvas(list_frame, bg='#f0f2f5', highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.chats_canvas.yview)
        self.chats_scrollable = ttk.Frame(self.chats_canvas)
        
        self.chats_scrollable.bind(
            "<Configure>",
            lambda e: self.chats_canvas.configure(scrollregion=self.chats_canvas.bbox("all"))
        )
        
        self.chats_canvas.create_window((0, 0), window=self.chats_scrollable, anchor="nw")
        self.chats_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.chats_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
    def setup_chat_area(self):
        """إعداد منطقة الدردشة"""
        # شاشة الترحيب
        self.welcome_frame = ttk.Frame(self.chat_frame)
        self.welcome_frame.pack(expand=True)
        
        ttk.Label(self.welcome_frame, text="💬", font=("Segoe UI", 80)).pack()
        ttk.Label(self.welcome_frame, text="مرحباً بك في Chat Me", 
                 font=self.header_font).pack(pady=10)
        ttk.Label(self.welcome_frame, text="اختر محادثة لتبدأ المراسلة", 
                 font=self.normal_font).pack()
        
        # إطار الدردشة النشط (مخفي في البداية)
        self.active_chat_frame = ttk.Frame(self.chat_frame)
        
        # رأس الدردشة
        chat_header = ttk.Frame(self.active_chat_frame)
        chat_header.pack(fill=tk.X, padx=10, pady=5)
        
        # معلومات جهة الاتصال
        contact_frame = ttk.Frame(chat_header)
        contact_frame.pack(side=tk.RIGHT)
        
        self.contact_avatar = ttk.Label(contact_frame, text="👤", font=("Segoe UI", 30))
        self.contact_avatar.pack(side=tk.RIGHT, padx=5)
        
        contact_info = ttk.Frame(contact_frame)
        contact_info.pack(side=tk.RIGHT)
        
        self.contact_name = ttk.Label(contact_info, text="", font=self.header_font)
        self.contact_name.pack(anchor=tk.W)
        
        self.contact_status = ttk.Label(contact_info, text="", font=self.small_font)
        self.contact_status.pack(anchor=tk.W)
        
        # أزرار الإجراءات
        actions_frame = ttk.Frame(chat_header)
        actions_frame.pack(side=tk.LEFT)
        
        ttk.Button(actions_frame, text="📞", width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(actions_frame, text="📹", width=3).pack(side=tk.LEFT, padx=2)
        ttk.Button(actions_frame, text="⋮", width=3).pack(side=tk.LEFT, padx=2)
        
        # خط فاصل
        ttk.Separator(self.active_chat_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)
        
        # منطقة عرض الرسائل
        messages_frame = ttk.Frame(self.active_chat_frame)
        messages_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.messages_canvas = tk.Canvas(messages_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(messages_frame, orient=tk.VERTICAL, command=self.messages_canvas.yview)
        self.messages_scrollable = ttk.Frame(self.messages_canvas)
        
        self.messages_scrollable.bind(
            "<Configure>",
            lambda e: self.messages_canvas.configure(scrollregion=self.messages_canvas.bbox("all"))
        )
        
        self.messages_canvas.create_window((0, 0), window=self.messages_scrollable, anchor="nw")
        self.messages_canvas.configure(yscrollcommand=scrollbar.set)
        
        self.messages_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # منطقة إدخال الرسالة
        input_frame = ttk.Frame(self.active_chat_frame)
        input_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(input_frame, text="📎", width=3).pack(side=tk.RIGHT, padx=2)
        ttk.Button(input_frame, text="😊", width=3).pack(side=tk.RIGHT, padx=2)
        
        self.message_input = ttk.Entry(input_frame, font=self.normal_font)
        self.message_input.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.message_input.bind('<Return>', self.send_message)
        
        ttk.Button(input_frame, text="📤", command=self.send_message, width=3).pack(side=tk.LEFT, padx=2)
        
    def login(self):
        """معالجة تسجيل الدخول"""
        email = self.login_email.get()
        password = self.login_password.get()
        
        if not email or not password:
            messagebox.showerror("خطأ", "الرجاء إدخال البريد الإلكتروني وكلمة المرور")
            return
        
        user = self.db.verify_user(email, password)
        if user:
            self.current_user = user
            self.show_main_screen()
        else:
            messagebox.showerror("خطأ", "بيانات الدخول غير صحيحة")
    
    def register(self):
        """معالجة إنشاء حساب جديد"""
        username = self.register_username.get()
        email = self.register_email.get()
        password = self.register_password.get()
        confirm = self.register_confirm.get()
        
        if not all([username, email, password, confirm]):
            messagebox.showerror("خطأ", "الرجاء ملء جميع الحقول")
            return
        
        if password != confirm:
            messagebox.showerror("خطأ", "كلمة المرور غير متطابقة")
            return
        
        user_id = self.db.create_user(username, email, password)
        if user_id:
            messagebox.showinfo("نجاح", "تم إنشاء الحساب بنجاح")
            # تسجيل الدخول تلقائياً
            self.login_email.insert(0, email)
            self.login_password.insert(0, password)
        else:
            messagebox.showerror("خطأ", "البريد الإلكتروني أو اسم المستخدم موجود مسبقاً")
    
    def connect_to_server(self):
        """الاتصال بخادم الدردشة"""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect(('localhost', 9999))
            self.connected = True
            
            # إرسال طلب تسجيل الدخول
            login_msg = {
                'type': 'login',
                'user_id': self.current_user['id'],
                'address': str(self.socket.getsockname())
            }
            self.send_message_to_server(login_msg)
            
            # بدء استقبال الرسائل
            threading.Thread(target=self.receive_messages, daemon=True).start()
            
        except Exception as e:
            messagebox.showerror("خطأ", f"فشل الاتصال بالخادم: {e}")
    
    def receive_messages(self):
        """استقبال الرسائل من الخادم"""
        while self.connected:
            try:
                data = self.socket.recv(4096).decode('utf-8')
                if data:
                    message = json.loads(data)
                    self.message_queue.put(message)
            except:
                self.connected = False
                break
    
    def process_messages(self):
        """معالجة الرسائل الواردة في الواجهة الرئيسية"""
        try:
            while True:
                message = self.message_queue.get_nowait()
                self.handle_server_message(message)
        except queue.Empty:
            pass
        finally:
            self.window.after(100, self.process_messages)
    
    def handle_server_message(self, message):
        """معالجة الرسائل الواردة من الخادم"""
        msg_type = message.get('type')
        
        if msg_type == 'message':
            self.display_received_message(message)
        elif msg_type == 'typing':
            self.handle_typing_indicator(message)
        elif msg_type == 'status_change':
            self.handle_status_change(message)
        elif msg_type == 'delivered':
            self.handle_delivery_confirmation(message)
        elif msg_type == 'read':
            self.handle_read_confirmation(message)
        elif msg_type == 'contacts_list':
            self.display_contacts(message['contacts'])
        elif msg_type == 'search_results':
            self.display_search_results(message['users'])
    
    def load_chats(self):
        """تحميل قائمة المحادثات"""
        # طلب قائمة جهات الاتصال من الخادم
        if self.connected:
            request = {
                'type': 'get_contacts',
                'user_id': self.current_user['id']
            }
            self.send_message_to_server(request)
    
    def display_contacts(self, contacts):
        """عرض قائمة جهات الاتصال"""
        # تنظيف القائمة
        for widget in self.chats_scrollable.winfo_children():
            widget.destroy()
        
        for contact in contacts:
            self.add_chat_item(contact)
    
    def add_chat_item(self, contact):
        """إضافة عنصر محادثة إلى القائمة"""
        frame = ttk.Frame(self.chats_scrollable)
        frame.pack(fill=tk.X, padx=5, pady=2)
        
        # صورة المستخدم
        avatar = ttk.Label(frame, text="👤", font=("Segoe UI", 25))
        avatar.pack(side=tk.RIGHT, padx=5)
        
        # معلومات المحادثة
        info_frame = ttk.Frame(frame)
        info_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True)
        
        name_frame = ttk.Frame(info_frame)
        name_frame.pack(fill=tk.X)
        
        ttk.Label(name_frame, text=contact['username'], 
                 font=self.normal_font).pack(side=tk.RIGHT)
        
        # حالة الاتصال
        status_color = "green" if contact.get('online', False) else "gray"
        ttk.Label(name_frame, text="●", foreground=status_color).pack(side=tk.LEFT)
        
        # آخر رسالة
        ttk.Label(info_frame, text="آخر رسالة هنا...", 
                 font=self.small_font, foreground='gray').pack(anchor=tk.W)
        
        # ربط النقر لفتح المحادثة
        frame.bind('<Button-1>', lambda e, c=contact: self.open_chat(c))
        
    def open_chat(self, contact):
        """فتح محادثة مع جهة اتصال"""
        self.current_chat = contact
        
        # إخفاء شاشة الترحيب وإظهار منطقة الدردشة
        self.welcome_frame.pack_forget()
        self.active_chat_frame.pack(fill=tk.BOTH, expand=True)
        
        # تحديث معلومات جهة الاتصال
        self.contact_name.config(text=contact['username'])
        status_text = "متصل" if contact.get('online', False) else "غير متصل"
        status_color = "green" if contact.get('online', False) else "gray"
        self.contact_status.config(text=status_text, foreground=status_color)
        
        # تحميل الرسائل السابقة
        self.load_messages(contact['id'])
    
    def load_messages(self, contact_id):
        """تحميل الرسائل السابقة"""
        messages = self.db.get_messages(self.current_user['id'], contact_id)
        
        # تنظيف منطقة الرسائل
        for widget in self.messages_scrollable.winfo_children():
            widget.destroy()
        
        for msg in messages:
            self.display_message(msg)
        
        # التمرير لأسفل
        self.messages_canvas.yview_moveto(1.0)
    
    def display_message(self, message):
        """عرض رسالة في منطقة الدردشة"""
        frame = ttk.Frame(self.messages_scrollable)
        frame.pack(fill=tk.X, pady=2)
        
        # تحديد ما إذا كانت الرسالة مرسلة أم مستقبلة
        is_sent = message['sender_id'] == self.current_user['id']
        align = tk.RIGHT if is_sent else tk.LEFT
        
        # محتوى الرسالة
        msg_frame = ttk.Frame(frame)
        msg_frame.pack(side=align, padx=10, pady=2)
        
        # فقاعة الرسالة
        bg_color = '#dcf8c6' if is_sent else '#ffffff'
        bubble = tk.Frame(msg_frame, bg=bg_color, relief=tk.RAISED, borderwidth=1)
        bubble.pack()
        
        # نص الرسالة
        label = tk.Label(bubble, text=message['content'], bg=bg_color, 
                         font=self.normal_font, wraplength=300, justify=tk.RIGHT)
        label.pack(padx=10, pady=5)
        
        # وقت الرسالة
        timestamp = datetime.datetime.fromisoformat(message['timestamp']).strftime('%H:%M')
        time_label = tk.Label(bubble, text=timestamp, bg=bg_color, 
                              font=self.small_font, foreground='gray')
        time_label.pack(anchor=tk.SE, padx=5, pady=2)
        
        # علامات الحالة (للرسائل المرسلة)
        if is_sent:
            status = "✓✓" if message['read'] else "✓" if message['delivered'] else "🕒"
            status_label = tk.Label(bubble, text=status, bg=bg_color, 
                                    font=self.small_font, foreground='gray')
            status_label.pack(anchor=tk.SE, padx=5)
    
    def display_received_message(self, message):
        """عرض رسالة مستلمة"""
        if self.current_chat and message['sender_id'] == self.current_chat['id']:
            self.display_message(message)
            self.messages_canvas.yview_moveto(1.0)
            
            # إرسال تأكيد القراءة
            read_receipt = {
                'type': 'read',
                'user_id': self.current_user['id'],
                'sender_id': message['sender_id']
            }
            self.send_message_to_server(read_receipt)
    
    def send_message(self, event=None):
        """إرسال رسالة"""
        content = self.message_input.get().strip()
        if not content or not self.current_chat:
            return
        
        # إنشاء كائن الرسالة
        message = {
            'type': 'message',
            'sender_id': self.current_user['id'],
            'receiver_id': self.current_chat['id'],
            'content': content,
            'timestamp': str(datetime.datetime.now())
        }
        
        # إرسال إلى الخادم
        self.send_message_to_server(message)
        
        # عرض الرسالة محلياً
        self.display_message({
            'sender_id': self.current_user['id'],
            'receiver_id': self.current_chat['id'],
            'content': content,
            'timestamp': message['timestamp'],
            'read': False,
            'delivered': False
        })
        
        # مسح حقل الإدخال
        self.message_input.delete(0, tk.END)
        
        # التمرير لأسفل
        self.messages_canvas.yview_moveto(1.0)
    
    def handle_typing_indicator(self, message):
        """معالجة مؤشر الكتابة"""
        if self.current_chat and message['user_id'] == self.current_chat['id']:
            if message['is_typing']:
                self.contact_status.config(text="يكتب...", foreground="blue")
            else:
                status = "متصل" if self.current_chat.get('online') else "غير متصل"
                color = "green" if self.current_chat.get('online') else "gray"
                self.contact_status.config(text=status, foreground=color)
    
    def handle_status_change(self, message):
        """معالجة تغيير حالة المستخدم"""
        if self.current_chat and message['user_id'] == self.current_chat['id']:
            self.current_chat['online'] = message['status'] == 'online'
            status_text = "متصل" if message['status'] == 'online' else "غير متصل"
            status_color = "green" if message['status'] == 'online' else "gray"
            self.contact_status.config(text=status_text, foreground=status_color)
    
    def handle_delivery_confirmation(self, message):
        """معالجة تأكيد التسليم"""
        # تحديث حالة الرسالة
        pass
    
    def handle_read_confirmation(self, message):
        """معالجة تأكيد القراءة"""
        # تحديث حالة الرسائل
        pass
    
    def search_users(self, event=None):
        """البحث عن مستخدمين"""
        query = self.search_entry.get().strip()
        if len(query) < 2:
            return
        
        if self.connected:
            search_msg = {
                'type': 'search',
                'query': query,
                'user_id': self.current_user['id']
            }
            self.send_message_to_server(search_msg)
    
    def display_search_results(self, users):
        """عرض نتائج البحث"""
        # إنشاء نافذة منبثقة للنتائج
        result_window = tk.Toplevel(self.window)
        result_window.title("نتائج البحث")
        result_window.geometry("400x500")
        
        # قائمة النتائج
        listbox = tk.Listbox(result_window, font=self.normal_font)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for user in users:
            status = "🟢" if user.get('online') else "⚪"
            listbox.insert(tk.END, f"{status} {user['username']} ({user['email']})")
        
        # زر إضافة جهة اتصال
        def add_selected():
            selection = listbox.curselection()
            if selection:
                user = users[selection[0]]
                if self.db.add_contact(self.current_user['id'], user['id']):
                    messagebox.showinfo("نجاح", f"تم إضافة {user['username']} إلى جهات الاتصال")
                    result_window.destroy()
                    self.load_chats()
                else:
                    messagebox.showerror("خطأ", "فشل إضافة جهة الاتصال")
        
        ttk.Button(result_window, text="إضافة جهة اتصال", 
                  command=add_selected).pack(pady=5)
    
    def show_settings(self):
        """عرض نافذة الإعدادات"""
        settings_window = tk.Toplevel(self.window)
        settings_window.title("الإعدادات")
        settings_window.geometry("300x400")
        
        ttk.Label(settings_window, text="الإعدادات", 
                 font=self.header_font).pack(pady=10)
        
        # معلومات المستخدم
        info_frame = ttk.Frame(settings_window)
        info_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(info_frame, text="اسم المستخدم:", font=self.normal_font).pack(anchor=tk.W)
        ttk.Label(info_frame, text=self.current_user['username'], 
                 font=self.normal_font).pack(anchor=tk.W, pady=2)
        
        ttk.Label(info_frame, text="البريد الإلكتروني:", font=self.normal_font).pack(anchor=tk.W)
        ttk.Label(info_frame, text=self.current_user['email'], 
                 font=self.normal_font).pack(anchor=tk.W, pady=2)
        
        # تغيير الحالة
        status_frame = ttk.Frame(settings_window)
        status_frame.pack(fill=tk.X, padx=20, pady=10)
        
        ttk.Label(status_frame, text="الحالة:", font=self.normal_font).pack(anchor=tk.W)
        status_var = tk.StringVar(value="online")
        ttk.Radiobutton(status_frame, text="متصل", variable=status_var, 
                       value="online").pack(anchor=tk.W)
        ttk.Radiobutton(status_frame, text="غير متصل", variable=status_var, 
                       value="offline").pack(anchor=tk.W)
        ttk.Radiobutton(status_frame, text="مشغول", variable=status_var, 
                       value="busy").pack(anchor=tk.W)
        
        # زر تسجيل الخروج
        def logout():
            if messagebox.askyesno("تسجيل الخروج", "هل تريد تسجيل الخروج؟"):
                if self.connected:
                    logout_msg = {
                        'type': 'logout',
                        'user_id': self.current_user['id']
                    }
                    self.send_message_to_server(logout_msg)
                    self.connected = False
                    self.socket.close()
                
                self.current_user = None
                self.show_login_screen()
        
        ttk.Button(settings_window, text="تسجيل الخروج", 
                  command=logout).pack(pady=20)
    
    def send_message_to_server(self, message):
        """إرسال رسالة إلى الخادم"""
        try:
            self.socket.send(json.dumps(message).encode('utf-8'))
        except:
            self.connected = False
    
    def run(self):
        """تشغيل التطبيق"""
        self.window.mainloop()

# ======================== تشغيل التطبيق ========================

def main():
    """الدالة الرئيسية لتشغيل التطبيق"""
    import sys
    
    print("=" * 50)
    print("🚀 Chat Me - تطبيق مراسلة فوري")
    print("=" * 50)
    
    # التحقق من وجود قاعدة البيانات وإنشائها إذا لزم الأمر
    db = Database()
    print("✅ تم تهيئة قاعدة البيانات")
    
    # تشغيل الخادم في خيط منفصل
    server = ChatServer()
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    print("✅ تم تشغيل خادم الدردشة")
    
    # انتظار قليلاً حتى يبدأ الخادم
    time.sleep(1)
    
    # تشغيل واجهة المستخدم
    print("✅ تشغيل واجهة المستخدم...")
    client = ChatClient()
    
    try:
        client.run()
    except KeyboardInterrupt:
        print("\n🛑 إيقاف التطبيق...")
    finally:
        server.stop()
        print("👋 تم إيقاف التطبيق بنجاح")

if __name__ == "__main__":
    main()
