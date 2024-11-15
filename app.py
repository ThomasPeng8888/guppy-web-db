import os
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_uploads import UploadSet, configure_uploads, IMAGES
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 用於會話加密

# 設定上傳目錄
app.config['UPLOADED_PHOTOS_DEST'] = os.path.join(app.root_path, 'static/photos')
photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)

# 模擬用戶資料和商品資料
users = {
    'admin': generate_password_hash('adminadmin')  # 管理員帳號及密碼
}
# 用於存儲輪播圖片的列表
banners = [
    {'image': 'banner1.jpg', 'alt_text': 'Banner 1'},
    {'image': 'banner2.jpg', 'alt_text': 'Banner 2'},
    {'image': 'banner3.jpg', 'alt_text': 'Banner 3'},
]
products = {
    1: {'name': '商品 A', 'price': 50, 'stock': 10, 'sponsor': '贊助者 A', 'image': 'product_a.jpg'},
    2: {'name': '商品 B', 'price': 100, 'stock': 0, 'sponsor': '贊助者 B', 'image': 'product_b.jpg'},
    # 添加更多商品...
}
# 模擬贊助者資料
sponsors = [
    {
        'name': '贊助者 A',
        'image': 'sponsor_a.jpg',
        'facebook_link': 'https://www.facebook.com/sponsorA'
    },
    {
        'name': '贊助者 B',
        'image': 'sponsor_b.jpg',
        'facebook_link': 'https://www.facebook.com/sponsorB'
    },
]

@app.route('/sponsor_info')
def sponsor_info():
    return render_template('sponsor_info.html', sponsors=sponsors)
user_points = {
    'admin': 200,
}
exchange_records = []

@app.route('/')
def home():
    return render_template('home.html')

# 用於存儲用戶的 LINE 社群暱稱
user_line_nicknames = {}  # 新增這一行

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        line_nickname = request.form['line_nickname']  # 獲取 LINE 社群暱稱

        if username in users:
            return "用戶名已存在！"
        
        users[username] = generate_password_hash(password)  # 儲存用戶資料
        user_points[username] = 100  # 新用戶初始點數
        
        # 如果需要，您可以將 line_nickname 儲存到一個字典中
        user_line_nicknames[username] = line_nickname

        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # 檢查是否在黑名單中
        if username in blacklist:
            message = "用戶已被凍結！"  # 設置錯誤訊息
            return render_template('login.html', message=message)  # 重新渲染登入頁面並顯示訊息
        
        # 檢查用戶名是否存在
        if username not in users:
            message = "無此用戶名！"  # 設置錯誤訊息
            return render_template('login.html', message=message)  # 重新渲染登入頁面並顯示訊息

        # 檢查密碼是否正確
        if check_password_hash(users[username], password):
            session['username'] = username  # 設置會話
            session['line_nickname'] = user_line_nicknames.get(username, '')  # 儲存 LINE 暱稱
            return redirect(url_for('home'))  # 登入成功後重定向到首頁
        
        message = "密碼不正確！"  # 密碼錯誤的訊息
        return render_template('login.html', message=message)  # 重新渲染登入頁面並顯示訊息
    
    return render_template('login.html')  # GET 請求時顯示登入頁面


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
    points = user_points.get(username, 0)  # 獲取該用戶的點數
    line_nickname = user_line_nicknames.get(username, '未設定')  # 獲取該用戶的 LINE 暱稱

    return render_template('member_center.html', username=username, points=points, user_line_nicknames=user_line_nicknames)

@app.route('/change_password', methods=['POST'])
def change_password():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']
    old_password = request.form['old_password']
    new_password = request.form['new_password']
    message = ""  # 初始化訊息變量

    # 檢查舊密碼是否正確
    if username in users and check_password_hash(users[username], old_password):
        users[username] = generate_password_hash(new_password)  # 更新密碼
        message = "新密碼更改成功！"  # 成功訊息
    else:
        message = "舊密碼不正確！"  # 錯誤訊息

    return render_template('member_center.html', username=username, points=user_points.get(username, 0), message=message, user_line_nicknames=user_line_nicknames)
    
@app.route('/admin')
def admin():
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))
    return render_template('admin.html', products=products, exchange_records=exchange_records)

@app.route('/admin/add_product', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        stock = int(request.form['stock'])  # 獲取庫存數量
        sponsor = request.form.get('sponsor')  # 獲取贊助者信息
        filename = None
        
        if 'photo' in request.files and request.files['photo'].filename != '':
            photo = request.files['photo']
            filename = photos.save(photo)  # 儲存圖片並獲取檔名
        
        product_id = len(products) + 1
        products[product_id] = {
            'name': name,
            'price': price,
            'stock': stock,  # 儲存庫存數量
            'sponsor': sponsor,
            'image': filename if filename else 'default.jpg'
        }
        
        return redirect(url_for('admin'))  # 返回管理介面
    
    return render_template('add_product.html')

@app.route('/admin/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        stock = int(request.form['stock'])  # 獲取庫存數量
        sponsor = request.form.get('sponsor')  # 獲取贊助者信息

        products[product_id] = {
            'name': name,
            'price': price,
            'stock': stock,  # 儲存庫存數量
            'sponsor': sponsor,  # 儲存贊助者信息
        }

        if 'photo' in request.files and request.files['photo'].filename != '':
            photo = request.files['photo']
            filename = photos.save(photo)  # 儲存圖片並獲取檔名
            products[product_id]['image'] = filename  # 更新圖片

        return redirect(url_for('admin'))  # 返回管理介面

    product = products.get(product_id)
    return render_template('edit_product.html', product=product)

points_records = []  # 儲存所有點數變更紀錄

@app.route('/admin/add_points', methods=['GET', 'POST'])
def add_points():
    if request.method == 'POST':
        username = request.form['username']
        points_to_add = int(request.form['points'])
        
        if username in user_points:
            user_points[username] += points_to_add
            
            # 記錄新增點數的操作
            points_records.append({
                'username': username,
                'operation': '新增',
                'points': points_to_add,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            return redirect(url_for('admin'))  # 返回管理介面
        else:
            return "用戶不存在！"
    
    return render_template('add_points.html')

@app.route('/admin/deduct_points', methods=['GET', 'POST'])
def deduct_points():
    if request.method == 'POST':
        username = request.form['username']
        points_to_deduct = int(request.form['points'])
        
        if username in user_points and user_points[username] >= points_to_deduct:
            user_points[username] -= points_to_deduct
            
            # 記錄扣除點數的操作
            points_records.append({
                'username': username,
                'operation': '扣除',
                'points': -points_to_deduct,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
            
            return redirect(url_for('admin'))  # 返回管理介面
        else:
            return "用戶不存在或點數不足！"
    
    return render_template('deduct_points.html')

@app.route('/search_users/<string:prefix>', methods=['GET'])
def search_users(prefix):
    matching_users = [user for user in user_points.keys() if user.startswith(prefix)]
    return jsonify(matching_users)  # 返回 JSON 格式的匹配用戶名列表

@app.route('/points_exchange', methods=['GET', 'POST'])
def points_exchange():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    username = session['username']
    message = None  # 確保 message 被初始化
    
    if request.method == 'POST':
        item_id = int(request.form['item_id'])
        quantity = int(request.form['quantity'])
        
        # 檢查庫存是否足夠
        if products[item_id]['stock'] >= quantity:
            item_cost = products[item_id]['price'] * quantity
            
            if user_points[username] >= item_cost:
                user_points[username] -= item_cost  # 扣除點數
                products[item_id]['stock'] -= quantity  # 扣除庫存
                
                # 紀錄兌換信息
                exchange_record = {
                    'username': username,
                    'item_name': products[item_id]['name'],
                    'exchange_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'cost': item_cost,
                    'quantity': quantity,
                    'sponsor': products[item_id].get('sponsor', '無')
                }
                exchange_records.append(exchange_record)  # 記錄兌換操作到點數紀錄
                
                points_records.append({
                    'username': username,
                    'operation': '兌換',
                    'points': -item_cost,  # 扣除的點數是負值
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
                
                message = "兌換成功！謝謝您！"
            else:
                message = "點數不足，無法兌換！"
        else:
            message = "庫存不足，無法完成兌換！"

    items = [
        {
            'id': id,
            'name': product['name'],
            'cost': product['price'],
            'stock': product['stock'],  # 顯示庫存數量
            'image': product.get('image', 'default.jpg'),
            'sponsor': product.get('sponsor', '無')
        } for id, product in products.items()
    ]
    
    return render_template('points_exchange.html', items=items, message=message)

@app.route('/admin/exchange_records')
def exchange_records_view():
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))
    return render_template('exchange_records.html', exchange_records=exchange_records)

@app.route('/admin/products')
def product_list():
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))
    return render_template('product_list.html', products=products)

def get_user_records(username):
    records = []
    
    # 假設有一個 list 存儲所有的操作紀錄
    for record in exchange_records:
        if record['username'] == username:
            records.append({
                'operation': '兌換',
                'points': -record['cost'],
                'timestamp': record['exchange_time']
            })

    # 假設有其他方式來獲取新增和扣除點數的紀錄
    return records

# 用於存儲遊戲設定
game_number = None
points_records = []  # 用於儲存點數變更紀錄
user_guesses = {}  # 用於記錄每個用戶的猜測狀態
game_guesses = {}  # 用於記錄每個用戶對該遊戲的猜測狀態
game_setup_completed_1 = False  # 新增變量，檢查遊戲是否已設定

@app.route('/admin/game_setup', methods=['GET', 'POST'])
def game_setup():
    global game_number, game_setup_completed_1, user_guesses
    if request.method == 'POST':
        game_number = int(request.form['game_number'])  # 設定遊戲數字
        game_setup_completed_1 = True  # 設定遊戲已完成
        user_guesses.clear()  # 清空所有用戶的猜測狀態，允許再次參加
        return redirect(url_for('admin'))  # 返回管理介面

    return render_template('game_setup.html')  # 返回設置頁面

@app.route('/guess_number', methods=['GET', 'POST'])
def guess_number():
    global game_number, game_setup_completed_1
    message = ""
    username = session.get('username', 'Guest')  # 獲取當前用戶名

    # 檢查遊戲是否已經設定
    if not game_setup_completed_1:
        return render_template('guess_number.html', message="管理員尚未設定正確數字，無法開始猜數字。", can_guess=False)

    if request.method == 'POST':
        if username not in user_points:  # 檢查用戶是否存在
            return "用戶不存在！請重新登入。"

        # 檢查用戶是否已經猜過該遊戲
        if username in user_guesses:
            message = "您已經猜過了，無法再次猜測！"
        else:
            guess = int(request.form['guess'])
            if guess == game_number:
                user_points[username] += 5  # 猜對了，增加點數
                message = "恭喜你！猜對了！獲得5點！"
                # 記錄獲得點數的操作
                points_records.append({
                    'username': username,
                    'operation': '遊戲獲得',
                    'points': 5,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                })
            else:
                message = "很遺憾，猜錯了！"
            user_guesses[username] = True  # 標記該用戶為已猜過

    return render_template('guess_number.html', message=message, can_guess=True)

@app.route('/admin/user_records', methods=['GET', 'POST'])
def user_records():
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))

    records = []
    message = None
    if request.method == 'POST':
        username = request.form['username']
        records = [record for record in points_records if record['username'] == username]

        if not records:
            message = "未找到該用戶的紀錄！"
    
    return render_template('user_records.html', records=records, message=message, user_line_nicknames=user_line_nicknames)

# 用於存儲預測名次的正確答案和用戶猜測
predicted_rank_number = None
predicted_rank_guesses = {} # 儲存每個用戶的猜測狀態
predicted_rank_bets = {}  # 儲存每個用戶的下注金額

# 用於存儲預測名次的正確答案
predicted_rank_number = None
game_setup_completed = False  # 新增變量，檢查遊戲是否已設定

@app.route('/admin/predict_rank_setup', methods=['GET', 'POST'])
def predict_rank_setup():
    global predicted_rank_number, game_setup_completed, predicted_rank_guesses
    if request.method == 'POST':
        predicted_rank_number = int(request.form['predicted_rank_number'])  # 獲取正確名次
        game_setup_completed = True  # 設定遊戲已完成
        predicted_rank_guesses.clear()  # 清空所有用戶的猜測狀態，允許再次參加
        return redirect(url_for('admin'))  # 返回管理介面

    return render_template('predict_rank_setup.html')  # 返回設置頁面

@app.route('/predict_rank', methods=['GET', 'POST'])
def predict_rank():
    global predicted_rank_number, predicted_rank_bets, game_setup_completed
    message = ""
    username = session.get('username', 'Guest')  # 獲取當前用戶名

    # 檢查遊戲是否已經設定
    if not game_setup_completed:
        return render_template('predict_rank.html', message="管理員尚未設定正確名次，無法開始預測。", remaining_points=user_points.get(username, 0), can_guess=False)

    if request.method == 'POST':
        if username not in user_points:  # 檢查用戶是否存在
            return "用戶不存在！請重新登入。"

        # 檢查用戶是否已經猜過
        if username in predicted_rank_guesses:
            message = "您已經猜過了，無法再次猜測！"
        else:
            # 處理預測名次
            guess = int(request.form['guess'])
            bet_amount = int(request.form['bet_amount'])  # 獲取下注金額
            bet_multiplier = int(request.form['bet_multiplier'])  # 獲取下注權重

            if bet_amount > user_points[username]:
                message = "下注金額超過您的剩餘點數！"
            elif bet_amount * bet_multiplier > user_points[username]:
                message = "下注金額乘以權重超過您的剩餘點數！"
            else:
                if guess == predicted_rank_number:
                    winnings = bet_amount * bet_multiplier  # 計算贏得的點數
                    user_points[username] += winnings  # 增加贏得的點數
                    message = f"恭喜你！猜對了！獲得 {winnings} 點！"
                    points_records.append({
                        'username': username,
                        'operation': '預測名次獲得',
                        'points': winnings,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                else:
                    user_points[username] -= bet_amount  # 扣除下注金額
                    message = f"很遺憾，猜錯了！扣除 {bet_amount} 點。"
                    points_records.append({
                        'username': username,
                        'operation': '預測名次失敗',
                        'points': -bet_amount,
                        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })

                predicted_rank_guesses[username] = guess  # 保存該用戶的猜測
                predicted_rank_bets[username] = bet_amount  # 保存該用戶的下注金額

    return render_template('predict_rank.html', message=message, remaining_points=user_points.get(username, 0), can_guess=True)

sponsors = {}

@app.route('/admin/add_sponsor', methods=['GET', 'POST'])
def add_sponsor():
    if request.method == 'POST':
        name = request.form['name']
        fb_link = request.form['fb_link']
        filename = None
        
        if 'photo' in request.files and request.files['photo'].filename != '':
            photo = request.files['photo']
            filename = photos.save(photo)  # 儲存圖片並獲取檔名

        sponsor_id = len(sponsors) + 1
        sponsors[sponsor_id] = {
            'name': name,
            'image': filename if filename else 'default.jpg',
            'facebook_link': fb_link
        }
        
        return redirect(url_for('admin'))  # 返回管理介面

    return render_template('add_sponsor.html')

@app.route('/admin/edit_sponsor/<int:sponsor_id>', methods=['GET', 'POST'])
def edit_sponsor(sponsor_id):
    sponsor = sponsors.get(sponsor_id)
    if request.method == 'POST':
        name = request.form['name']
        fb_link = request.form['fb_link']
        
        if 'photo' in request.files and request.files['photo'].filename != '':
            photo = request.files['photo']
            filename = photos.save(photo)  # 儲存圖片並獲取檔名
            sponsor['image'] = filename
        
        sponsor['name'] = name
        sponsor['facebook_link'] = fb_link
        
        return redirect(url_for('admin'))  # 返回管理介面

    return render_template('edit_sponsor.html', sponsor=sponsor)

@app.route('/admin/delete_sponsor/<int:sponsor_id>', methods=['POST'])
def delete_sponsor(sponsor_id):
    if sponsor_id in sponsors:
        del sponsors[sponsor_id]  # 刪除贊助者
    return redirect(url_for('admin'))  # 返回管理介面

@app.route('/admin/sponsors')
def sponsor_list():
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))
    
    return render_template('sponsor_list.html', sponsors=sponsors)

@app.route('/leaderboard')
def leaderboard():
    # 獲取所有用戶的點數並排序
    sorted_users = sorted(user_points.items(), key=lambda x: x[1], reverse=True)[:20]  # 獲取前20名
    leaderboard = [(index + 1, username, user_line_nicknames.get(username, '未設定'), points) 
                   for index, (username, points) in enumerate(sorted_users)]
    return render_template('leaderboard.html', leaderboard=leaderboard)

# 用於存儲被禁用的用戶
blacklist = set()

@app.route('/admin/blacklist', methods=['GET', 'POST'])
def blacklist_users():
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))

    message = None
    if request.method == 'POST':
        username_to_blacklist = request.form['username']
        if username_to_blacklist in users and username_to_blacklist not in blacklist:
            blacklist.add(username_to_blacklist)
            message = f"{username_to_blacklist} 已被加入黑名單！"
        elif username_to_blacklist in blacklist:
            message = f"{username_to_blacklist} 已在黑名單中！"
        else:
            message = "無法找到該用戶！"

    return render_template('blacklist.html', blacklist=blacklist, message=message)

@app.route('/admin/unblacklist/<username>', methods=['POST'])
def unblacklist_user(username):
    if 'username' not in session or session['username'] != 'admin':
        return redirect(url_for('login'))

    if username in blacklist:
        blacklist.remove(username)  # 從黑名單中移除用戶
        message = f"{username} 已從黑名單中移除！"
    else:
        message = f"{username} 不在黑名單中！"

    return redirect(url_for('blacklist_users', message=message))


if __name__ == '__main__':
    app.run(debug=True)