import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_uploads import UploadSet, configure_uploads, IMAGES
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import pytz

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 設定上傳目錄
app.config['UPLOADED_PHOTOS_DEST'] = os.path.join(app.root_path, 'static/photos')
photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)

# 設定 SQLite 資料庫位置
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# 定義路由或其他邏輯
with app.app_context():
    db.create_all()  # 確保在上下文中創建表

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    line_nickname = db.Column(db.String(150))
    points = db.Column(db.Integer, default=100)
    is_blacklisted = db.Column(db.Boolean, default=False)  # 黑名單標記
    is_admin = db.Column(db.Boolean, default=False)  # 管理員標記

# 定義產品模型
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    sponsor = db.Column(db.String(150))
    image = db.Column(db.String(150), default='default.jpg')

# 定義贊助者模型
class Sponsor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    image = db.Column(db.String(150), default='default.jpg')
    facebook_link = db.Column(db.String(200))

# 定義兌換紀錄模型
class ExchangeRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), nullable=False)
    line_nickname = db.Column(db.String(100), nullable=True)  # 新增 LINE社群暱稱欄位
    item_name = db.Column(db.String(150), nullable=False)
    exchange_time = db.Column(db.DateTime, default=datetime.utcnow)
    cost = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    sponsor = db.Column(db.String(150))

# 遊戲設置表
class GameSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_number = db.Column(db.Integer, nullable=False)  # 存儲遊戲數字
    setup_completed = db.Column(db.Boolean, default=False)  # 遊戲是否已設置完成

# 用戶猜測表
class UserGuess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    guess = db.Column(db.Integer, nullable=True)  # 用戶猜的數字，如果未猜過為 None
    guessed_at = db.Column(db.DateTime, default=datetime.utcnow)  # 記錄猜測時間

# 點數記錄表
class PointsRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    operation = db.Column(db.String(200), nullable=False)  # 操作類型（如“遊戲獲得”）
    points = db.Column(db.Integer, nullable=False)  # 增加的點數
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)  # 時間戳

class PredictedRank(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    predicted_rank_number = db.Column(db.Integer, nullable=False)
    game_setup_completed = db.Column(db.Boolean, default=False)

class PredictedRankGuess(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    guess = db.Column(db.Integer, nullable=False)
    bet_amount = db.Column(db.Integer, nullable=False)
    bet_multiplier = db.Column(db.Integer, nullable=False)

class UserPoints(db.Model):
    username = db.Column(db.String(80), primary_key=True)
    points = db.Column(db.Integer, default=0)


with app.app_context():  # 這段代碼確保只執行一次
    db.create_all()

    # 檢查是否存在管理員用戶
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            password=generate_password_hash('adminadmin'),  # 預設密碼
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()


@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        line_nickname = request.form['line_nickname']

        if User.query.filter_by(username=username).first():
            return "用戶名已存在！"

        new_user = User(username=username, password=generate_password_hash(password), line_nickname=line_nickname)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # 檢查是否在黑名單中
        user = User.query.filter_by(username=username).first()
        if user and user.is_blacklisted:
            message = "用戶已被凍結！"
            return render_template('login.html', message=message)

        # 檢查用戶名是否存在
        if not user:
            message = "無此用戶名！"
            return render_template('login.html', message=message)

        # 檢查密碼是否正確
        if check_password_hash(user.password, password):
            session['username'] = user.username
            session['line_nickname'] = user.line_nickname
            return redirect(url_for('home'))

        message = "密碼不正確！"
        return render_template('login.html', message=message)

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)  # 清除會話
    return redirect(url_for('home'))

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    return f"歡迎回來，{session['username']}！"

@app.route('/member_center')
def member_center():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']

    # 查找資料庫中對應的用戶
    user = User.query.filter_by(username=username).first()

    if not user:
        return "用戶不存在！"

    points = user.points  # 獲取該用戶的點數
    line_nickname = user.line_nickname  # 獲取該用戶的 LINE 暱稱

    return render_template('member_center.html', username=username, points=points, line_nickname=line_nickname)

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))  # 如果用戶沒有登錄，重定向到登錄頁面

    username = session['username']
    old_password = request.form['old_password']
    new_password = request.form['new_password']
    message = ""  # 初始化消息變數

    # 從資料庫獲取用戶對象
    user = User.query.filter_by(username=username).first()

    if user and check_password_hash(user.password, old_password):  # 驗證舊密碼是否正確
        user.password = generate_password_hash(new_password)  # 更新密碼
        db.session.commit()  # 提交更改
        message = "新密碼更改成功！"  # 成功消息
    else:
        message = "舊密碼不正確！"  # 錯誤消息

    # 獲取用戶的積分和 Line 暱稱
    points = user.points if user else 0
    line_nickname = user.line_nickname if user else None

    return render_template('member_center.html', username=username, points=points, message=message, user_line_nicknames=line_nickname)

@app.route('/admin')
def admin():
    if 'username' not in session or not User.query.filter_by(username=session['username'], is_admin=True).first():
        return redirect(url_for('login'))

    products_list = Product.query.all()
    sponsors_list = Sponsor.query.all()
    
    return render_template('admin.html', products=products_list, sponsors=sponsors_list)

@app.route('/admin/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        stock = int(request.form['stock'])
        sponsor_name = request.form.get('sponsor')

        filename=None
        if 'photo' in request.files and request.files['photo'].filename != '':
            photo=request.files['photo']
            filename=photos.save(photo)

        new_product=Product(name=name, price=price, stock=stock,
                            sponsor=sponsor_name,
                            image=filename if filename else 'default.jpg')
        
        db.session.add(new_product)
        db.session.commit()
        
        return redirect(url_for('admin'))

    return render_template('add_product.html')

@app.route('/admin/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product_to_edit = Product.query.get(product_id)

    if request.method == 'POST':
        product_to_edit.name = request.form['name']
        product_to_edit.price = float(request.form['price'])
        product_to_edit.stock = int(request.form['stock'])
        
        sponsor_name=request.form.get('sponsor')
        product_to_edit.sponsor=sponsor_name

        if 'photo' in request.files and request.files['photo'].filename != '':
            photo=request.files['photo']
            filename=photos.save(photo)
            product_to_edit.image=filename

        db.session.commit()
        
        return redirect(url_for('admin'))

    return render_template('edit_product.html', product=product_to_edit)

@app.route('/admin/products')
def product_list():
    # 確保使用者是管理員
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))

    # 從資料庫中獲取所有產品
    products = Product.query.all()  # 獲取所有產品

    return render_template('product_list.html', products=products)


@app.route('/admin/delete/<int:product_id>', methods=['POST'])
def delete_product(product_id):
    product_to_delete = Product.query.get(product_id)
    
    if product_to_delete:
        db.session.delete(product_to_delete)
        db.session.commit()

    return redirect(url_for('admin'))


@app.route('/sponsor_info')
def sponsor_info():
    # 從資料庫中獲取所有贊助商
    sponsors = Sponsor.query.all()
    return render_template('sponsor_info.html', sponsors=sponsors)


@app.route('/admin/add_sponsor', methods=['GET', 'POST'])
def add_sponsor():
    if request.method == 'POST':
        name = request.form['name']
        fb_link = request.form['fb_link']

        filename = None
        if 'photo' in request.files and request.files['photo'].filename != '':
            photo = request.files['photo']
            filename = photos.save(photo)

        new_sponsor = Sponsor(name=name, image=filename if filename else 'default.jpg',
                            facebook_link=fb_link)

        db.session.add(new_sponsor)
        db.session.commit()

        return redirect(url_for('admin'))

    return render_template('add_sponsor.html')


@app.route('/admin/edit_sponsor/<int:sponsor_id>', methods=['GET', 'POST'])
def edit_sponsor(sponsor_id):
    sponsor = Sponsor.query.get(sponsor_id)  # 從資料庫中查找贊助者
    if not sponsor:
        return redirect(url_for('admin'))  # 如果沒有找到該贊助者，返回管理頁面

    if request.method == 'POST':
        name = request.form['name']
        fb_link = request.form['fb_link']
        
        if 'photo' in request.files and request.files['photo'].filename != '':
            photo = request.files['photo']
            filename = photos.save(photo)  # 儲存圖片並獲取檔名
            sponsor.image = filename  # 更新圖片欄位
        
        sponsor.name = name  # 更新名稱
        sponsor.facebook_link = fb_link  # 更新 Facebook 連結

        db.session.commit()  # 提交更改至資料庫
        
        return redirect(url_for('admin'))  # 返回管理介面

    return render_template('edit_sponsor.html', sponsor=sponsor)


@app.route('/admin/delete_sponsor/<int:sponsor_id>', methods=['POST'])
def delete_sponsor(sponsor_id):
    sponsor = Sponsor.query.get(sponsor_id)  # 從資料庫查找贊助者
    if sponsor:
        db.session.delete(sponsor)  # 刪除贊助者
        db.session.commit()  # 提交更改至資料庫
    return redirect(url_for('admin'))  # 返回管理介面


@app.route('/admin/sponsors')
def sponsor_list():
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))
    
    sponsors = Sponsor.query.all()  # 獲取所有贊助者資料
    return render_template('sponsor_list.html', sponsors=sponsors)


@app.route('/leaderboard')
def leaderboard():
    users_points_sorted = User.query.order_by(User.points.desc()).limit(20).all()
    
    leaderboard = [(index + 1, user.username, user.line_nickname, user.points) for index, user in enumerate(users_points_sorted)]
    
    return render_template('leaderboard.html', leaderboard=leaderboard)


@app.route('/admin/game_setup', methods=['GET', 'POST'])
def game_setup():
    if request.method == 'POST':
        game_number = int(request.form['game_number'])  # 獲取遊戲數字

        # 創建遊戲設定條目
        game_setting = GameSetting.query.first()  # 獲取現有的設定，如果沒有則創建一個新的
        if game_setting:
            game_setting.game_number = game_number
            game_setting.setup_completed = True
        else:
            new_game_setting = GameSetting(game_number=game_number, setup_completed=True)
            db.session.add(new_game_setting)
        
        db.session.commit()  # 提交更改

        # 清空使用者的猜測狀態
        UserGuess.query.delete()  # 清空所有使用者的猜測記錄
        db.session.commit()

        return redirect(url_for('admin'))  # 返回管理介面

    return render_template('game_setup.html')  # 返回設置頁面


@app.route('/guess_number', methods=['GET', 'POST'])
def guess_number():
    message = ""
    username = session.get('username', 'Guest')  # 獲取當前用戶名

    # 檢查遊戲是否已設置
    game_setting = GameSetting.query.first()  # 獲取遊戲設定
    if not game_setting or not game_setting.setup_completed:
        return render_template('guess_number.html', message="管理員尚未開啟此遊戲，無法開始猜數字呦。", can_guess=False)

    if request.method == 'POST':
        user = User.query.filter_by(username=username).first()  # 獲取使用者物件
        if not user:
            return "用戶不存在！請重新登入。"

        # 檢查使用者是否已經猜過該遊戲
        user_guess = UserGuess.query.filter_by(username=username).first()
        if user_guess:
            message = "您已經猜過了！靜等下次遊戲開放"
        else:
            guess = int(request.form['guess'])
            if guess == game_setting.game_number:
                user.points += 5  # 猜對了，增加點數
                message = "恭喜你！猜對了！獲得5點！"
                # 記錄點數變化
                points_record = PointsRecord(username=username, operation="遊戲獲得", points=5)
                db.session.add(points_record)
            else:
                message = "很遺憾，猜錯了！下次再來！"
            
            # 創建使用者猜測記錄
            new_guess = UserGuess(username=username, guess=guess)
            db.session.add(new_guess)

        db.session.commit()

    return render_template('guess_number.html', message=message, can_guess=True)


@app.route('/admin/add_points', methods=['GET', 'POST'])
def add_points():
    if request.method == 'POST':
        username = request.form['username']
        points_to_add = int(request.form['points'])

        user = User.query.filter_by(username=username).first()  # 獲取使用者物件
        if user:
            user.points += points_to_add

            # 記錄新增點數的操作
            new_points_record = PointsRecord(
                username=username,
                operation='新增',
                points=points_to_add,
                timestamp=datetime.now(pytz.timezone('Asia/Taipei'))
            )
            db.session.add(new_points_record)
            db.session.commit()  # 提交更改

            return redirect(url_for('admin'))  # 返回管理介面
        else:
            return "用戶不存在！"
    
    return render_template('add_points.html')


@app.route('/admin/deduct_points', methods=['GET', 'POST'])
def deduct_points():
    if request.method == 'POST':
        username = request.form['username']
        points_to_deduct = int(request.form['points'])

        user = User.query.filter_by(username=username).first()  # 獲取使用者物件
        if user and user.points >= points_to_deduct:
            user.points -= points_to_deduct

            # 記錄扣除點數的操作
            new_points_record = PointsRecord(
                username=username,
                operation='扣除',
                points=-points_to_deduct,
                timestamp=datetime.now(pytz.timezone('Asia/Taipei'))
            )
            db.session.add(new_points_record)
            db.session.commit()  # 提交更改

            return redirect(url_for('admin'))  # 返回管理介面
        else:
            return "用戶不存在或點數不足！"
    
    return render_template('deduct_points.html')


@app.route('/points_exchange', methods=['GET', 'POST'])
def points_exchange():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    user = User.query.filter_by(username=username).first()  # 獲取用戶資料
    message = None  # 確保訊息被初始化

    if request.method == 'POST':
        item_id = int(request.form['item_id'])
        quantity = int(request.form['quantity'])

        # 獲取商品資料
        product = Product.query.get(item_id)

        # 檢查商品是否存在且庫存是否足夠
        if product and product.stock >= quantity:
            item_cost = product.price * quantity

            if user.points >= item_cost:
                user.points -= item_cost  # 扣除積分
                product.stock -= quantity  # 扣除庫存

                # 記錄兌換信息到兌換記錄表
                exchange_record = ExchangeRecord(
                    username=username,
                    item_name=product.name,
                    cost=item_cost,
                    quantity=quantity,
                    sponsor=product.sponsor or '無'
                )
                db.session.add(exchange_record)

                # 記錄積分變更
                new_points_record = PointsRecord(
                    username=username,
                    operation='兌換',
                    points=-item_cost,  # 扣除的積分為負值
                    timestamp=datetime.now()
                )
                db.session.add(new_points_record)

                db.session.commit()  # 提交更改

                message = "兌換成功！謝謝您！"
            else:
                message = "積分不足，無法兌換！"
        else:
            message = "庫存不足，無法完成兌換！"

    # 從資料庫獲取所有商品
    items = Product.query.all()

    return render_template('points_exchange.html', items=items, message=message)


@app.route('/admin/exchange_records')
def exchange_records_view():
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))

    # 獲取所有兌換記錄
    exchange_records = ExchangeRecord.query.all()

    return render_template('exchange_records.html', exchange_records=exchange_records)

def get_user_records(username):
    # 獲取所有與指定用戶名相關的紀錄
    records = PointsRecord.query.filter(PointsRecord.username == username).all()
    
    # 如果需要返回特定的字段格式（例如 operation, points, timestamp），可以轉換格式
    formatted_records = []
    for record in records:
        formatted_records.append({
            'operation': record.operation,  # 操作類型
            'points': record.points,  # 增加或扣除的點數
            'timestamp': record.timestamp.astimezone(pytz.timezone('Asia/Taipei'))
        })

    return formatted_records

@app.route('/admin/user_records', methods=['GET', 'POST'])
def user_records():
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))  # 如果不是管理員，重定向到登入頁面

    records = []
    message = None
    user_line_nicknames = {}  # 定義這個變數來儲存用戶名對應的 Line 昵称

    if request.method == 'POST':
        username = request.form.get('username')

        if username:
            # 從資料庫中查詢該用戶的所有點數紀錄
            records = PointsRecord.query.filter_by(username=username).all()

            if not records:
                message = "未找到該用戶的紀錄！"

            # 查詢該用戶的 Line 昵称並儲存
            user = User.query.filter_by(username=username).first()  # 查詢用戶
            if user:
                user_line_nicknames[username] = user.line_nickname  # 儲存 Line 昵称
            else:
                user_line_nicknames[username] = None  # 沒找到用戶則為 None
        else:
            message = "請輸入用戶名！"

    # 渲染模板並傳遞紀錄、訊息
    return render_template('user_records.html', records=records, message=message, user_line_nicknames=user_line_nicknames)


@app.route('/admin/predict_rank_setup', methods=['GET', 'POST'])
def predict_rank_setup():
    if request.method == 'POST':
        predicted_rank_number = int(request.form['predicted_rank_number'])  # 獲取正確名次
        game_setup_completed = True  # 設定遊戲已完成

        # 設定正確名次
        rank_setup = PredictedRank.query.first()
        if rank_setup:
            rank_setup.predicted_rank_number = predicted_rank_number
            rank_setup.game_setup_completed = game_setup_completed
        else:
            rank_setup = PredictedRank(predicted_rank_number=predicted_rank_number, game_setup_completed=game_setup_completed)
            db.session.add(rank_setup)
        
        db.session.commit()

        return redirect(url_for('admin'))  # 返回管理介面

    return render_template('predict_rank_setup.html')  # 返回設置頁面


@app.route('/predict_rank', methods=['GET', 'POST'])
def predict_rank():
    message = ""
    username = session.get('username', 'Guest')  # 獲取當前用戶名

    # 檢查遊戲是否已經設定
    rank_setup = PredictedRank.query.first()
    if not rank_setup or not rank_setup.game_setup_completed:
        return render_template('predict_rank.html', message="管理員尚未設定正確名次，無法開始預測。", can_guess=False)

    predicted_rank_number = rank_setup.predicted_rank_number

    # 查詢用戶的點數
    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username, points=0)  # 如果用戶不存在，創建新用戶
        db.session.add(user)
        db.session.commit()

    if request.method == 'POST':
        # 檢查用戶是否已經猜過
        existing_guess = PredictedRankGuess.query.filter_by(username=username).first()
        if existing_guess:
            message = "您已經猜過了，無法再次猜測！"
        else:
            # 處理預測名次
            guess = int(request.form['guess'])
            bet_amount = int(request.form['bet_amount'])  # 獲取下注金額
            bet_multiplier = int(request.form['bet_multiplier'])  # 獲取下注權重

            if bet_amount > user.points:
                message = "下注金額超過您的剩餘點數！"
            elif bet_amount * bet_multiplier > user.points:
                message = "下注金額乘以權重超過您的剩餘點數！"
            else:
                if guess == predicted_rank_number:
                    winnings = bet_amount * bet_multiplier  # 計算贏得的點數
                    user.points += winnings  # 增加贏得的點數
                    message = f"恭喜你！猜對了！獲得 {winnings} 點！"
                    points_record = PointsRecord(username=username, operation='預測名次獲得', points=winnings, timestamp=datetime.now(pytz.timezone('Asia/Taipei')))
                    db.session.add(points_record)
                    db.session.commit()  # 提交資料庫更改
                else:
                    user.points -= bet_amount  # 扣除下注金額
                    message = f"很遺憾，猜錯了！扣除 {bet_amount} 點。"
                    points_record = PointsRecord(username=username, operation='預測名次失敗', points=-bet_amount, timestamp=datetime.now(pytz.timezone('Asia/Taipei')))
                    db.session.add(points_record)
                    db.session.commit()  # 提交資料庫更改

                # 儲存用戶的猜測資料
                guess_entry = PredictedRankGuess(username=username, guess=guess, bet_amount=bet_amount, bet_multiplier=bet_multiplier)
                db.session.add(guess_entry)
                db.session.commit()  # 提交資料庫更改

    return render_template('predict_rank.html', message=message, remaining_points=user.points, can_guess=True)


@app.route('/admin/blacklist', methods=['GET', 'POST'])
def blacklist_users():
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))

    message = None
    if request.method == 'POST':
        username_to_blacklist = request.form['username']
        user = User.query.filter_by(username=username_to_blacklist).first()  # 查找用戶

        if user:
            if not user.is_blacklisted:
                user.is_blacklisted = True  # 將用戶標記為黑名單
                db.session.commit()  # 提交更改
                message = f"{username_to_blacklist} 已被加入黑名單！"
            else:
                message = f"{username_to_blacklist} 已在黑名單中！"
        else:
            message = "無法找到該用戶！"

    # 獲取所有被加入黑名單的用戶
    blacklisted_users = User.query.filter_by(is_blacklisted=True).all()
    return render_template('blacklist.html', blacklist=blacklisted_users, message=message)

@app.route('/admin/unblacklist/<username>', methods=['POST'])
def unblacklist_user(username):
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))

    user = User.query.filter_by(username=username).first()  # 查找用戶

    if user and user.is_blacklisted:
        user.is_blacklisted = False  # 將用戶從黑名單中移除
        db.session.commit()  # 提交更改
        message = f"{username} 已從黑名單中移除！"
    else:
        message = f"{username} 不在黑名單中！"

    return redirect(url_for('blacklist_users', message=message))

if __name__ == '__main__':
    app.run(debug=True)  # 在本地開發時使用debug模式
