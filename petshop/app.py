from flask import Flask, request, render_template, jsonify, redirect, url_for, send_from_directory
import pymysql
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

app = Flask(__name__, static_folder='static')

# 数据库配置
db_config = {
    'host': '127.0.0.1',
    'user': 'root',
    'password': '041123',
    'database': 'petshop',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# 创建数据库连接
def get_db_connection():
    return pymysql.connect(**db_config)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    
    # 密码加密
    hashed_password = generate_password_hash(password)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO users (username, password, email) VALUES (%s, %s, %s)",
            (username, hashed_password, email)
        )
        conn.commit()
        return jsonify({"message": "注册成功"})
    except pymysql.Error as err:
        return jsonify({"error": f"注册失败：{str(err)}"}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "SELECT * FROM users WHERE username = %s",
            (username,)
        )
        user = cursor.fetchone()
        
        if user and check_password_hash(user['password'], password):
            return jsonify({
                "message": "登录成功",
                "username": user['username'],
                "user_id": user['id']
            })
        else:
            return jsonify({"error": "用户名或密码错误"}), 401
    except pymysql.Error as err:
        return jsonify({"error": f"登录失败：{str(err)}"}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/shop')
def shop():
    return render_template('shop.html')

@app.route('/admin')
def admin():
    return render_template('admin.html')

@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    # 设置固定的管理员账号和密码
    ADMIN_USERNAME = "2693045168"
    ADMIN_PASSWORD = "hjj20041123"
    
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        return jsonify({
            "message": "管理员登录成功",
            "isAdmin": True
        })
    else:
        return jsonify({"error": "管理员账号或密码错误"}), 401

@app.route('/admin/dashboard')
def admin_dashboard():
    # 不需要验证 cookies，直接返回页面
    # 前端会通过 localStorage 验证管理员身份
    return render_template('admin_dashboard.html')

# 商品相关路由
@app.route('/api/products', methods=['GET'])
def get_products():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM products")
        products = cursor.fetchall()
        return jsonify(products)
    finally:
        cursor.close()
        conn.close()

@app.route('/api/products', methods=['POST'])
def add_product():
    if not request.is_json:
        return jsonify({"error": "Missing JSON"}), 400
    
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO products (name, description, price, image_url, stock, category) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (data['name'], data['description'], data['price'], 
             data['image_url'], data['stock'], data['category'])
        )
        conn.commit()
        return jsonify({"message": "商品添加成功"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

# 服务相关路由
@app.route('/api/services', methods=['GET'])
def get_services():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM services")
        services = cursor.fetchall()
        return jsonify(services)
    finally:
        cursor.close()
        conn.close()

@app.route('/api/services', methods=['POST'])
def add_service():
    if not request.is_json:
        return jsonify({"error": "Missing JSON"}), 400
    
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO services (name, description, price, duration) "
            "VALUES (%s, %s, %s, %s)",
            (data['name'], data['description'], data['price'], data['duration'])
        )
        conn.commit()
        return jsonify({"message": "服务添加成功"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

# 购物车相关路由
@app.route('/api/cart', methods=['GET'])
def get_cart():
    user_id = request.args.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # 获取购物车中的商品
        cursor.execute("""
            SELECT ci.*, p.name, p.price, p.image_url,
                   (p.price * ci.quantity) as total_price
            FROM cart_items ci 
            LEFT JOIN products p ON ci.product_id = p.id 
            WHERE ci.user_id = %s AND ci.product_id IS NOT NULL
        """, (user_id,))
        products = cursor.fetchall()
        
        # 获取购物车中的服务
        cursor.execute("""
            SELECT ci.*, s.name, s.price,
                   s.price as total_price
            FROM cart_items ci 
            LEFT JOIN services s ON ci.service_id = s.id 
            WHERE ci.user_id = %s AND ci.service_id IS NOT NULL
        """, (user_id,))
        services = cursor.fetchall()
        
        # 计算总金额
        total_amount = sum(item['total_price'] for item in products + services)
        
        return jsonify({
            "products": products,
            "services": services,
            "total_amount": total_amount
        })
    finally:
        cursor.close()
        conn.close()

@app.route('/api/cart', methods=['POST'])
def add_to_cart():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if 'product_id' in data:
            cursor.execute(
                "INSERT INTO cart_items (user_id, product_id, quantity) VALUES (%s, %s, %s)",
                (data['user_id'], data['product_id'], data.get('quantity', 1))
            )
        elif 'service_id' in data:
            cursor.execute(
                "INSERT INTO cart_items (user_id, service_id) VALUES (%s, %s)",
                (data['user_id'], data['service_id'])
            )
        conn.commit()
        return jsonify({"message": "添加到购物车成功"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

# 订单相关路由
@app.route('/api/orders', methods=['GET'])
def get_orders():
    user_id = request.args.get('user_id')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                o.*,
                GROUP_CONCAT(DISTINCT 
                    CONCAT(p.name, ' (', op.quantity, '件, ¥', op.price, ')') 
                    SEPARATOR ', '
                ) as products,
                GROUP_CONCAT(DISTINCT 
                    CONCAT(s.name, ' (¥', os.price, ')') 
                    SEPARATOR ', '
                ) as services
            FROM orders o
            LEFT JOIN order_products op ON o.id = op.order_id
            LEFT JOIN products p ON op.product_id = p.id
            LEFT JOIN order_services os ON o.id = os.order_id
            LEFT JOIN services s ON os.service_id = s.id
            WHERE o.user_id = %s
            GROUP BY o.id
            ORDER BY o.create_time DESC
        """, (user_id,))
        orders = cursor.fetchall()
        
        # 处理时间格式
        for order in orders:
            order['create_time'] = order['create_time'].strftime('%Y-%m-%d %H:%M:%S')
            if order['update_time']:
                order['update_time'] = order['update_time'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify(orders)
    finally:
        cursor.close()
        conn.close()

@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.json
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 开始事务
        conn.begin()
        
        # 验证并计算商品���额
        total_amount = 0
        
        # 验证并计算商品总金额
        for product in data.get('products', []):
            # 检查库存
            cursor.execute(
                "SELECT price, stock FROM products WHERE id = %s FOR UPDATE",
                (product['id'],)
            )
            result = cursor.fetchone()
            if not result:
                raise Exception(f"商品ID {product['id']} 不存在")
            if result['stock'] < product['quantity']:
                raise Exception(f"商品库存不足")
            total_amount += result['price'] * product['quantity']
        
        # 验证并计算服务总金额
        for service in data.get('services', []):
            cursor.execute(
                "SELECT price FROM services WHERE id = %s",
                (service['id'],)
            )
            result = cursor.fetchone()
            if not result:
                raise Exception(f"服务ID {service['id']} 不存在")
            total_amount += result['price']
        
        # 创建订单
        cursor.execute(
            "INSERT INTO orders (user_id, total_amount, status) VALUES (%s, %s, 'pending')",
            (data['user_id'], total_amount)
        )
        order_id = cursor.lastrowid
        
        # 添加订单商品
        for product in data.get('products', []):
            cursor.execute(
                "INSERT INTO order_products (order_id, product_id, quantity, price) "
                "VALUES (%s, %s, %s, (SELECT price FROM products WHERE id = %s))",
                (order_id, product['id'], product['quantity'], product['id'])
            )
            
            # 直接更新库存
            cursor.execute(
                "UPDATE products SET stock = stock - %s WHERE id = %s",
                (product['quantity'], product['id'])
            )
        
        # 添加订单服务，使用正确的日期时间格式
        for service in data.get('services', []):
            # 使用当前时间作为默认预约时间
            appointment_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                "INSERT INTO order_services (order_id, service_id, price, appointment_time) "
                "VALUES (%s, %s, (SELECT price FROM services WHERE id = %s), %s)",
                (order_id, service['id'], service['id'], appointment_time)
            )
        
        # 清空购物车
        cursor.execute("DELETE FROM cart_items WHERE user_id = %s", (data['user_id'],))
        
        conn.commit()
        return jsonify({
            "message": "订单创建成功",
            "order_id": order_id,
            "total_amount": total_amount
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

@app.route('/api/orders/<int:order_id>', methods=['PUT'])
def update_order_status(order_id):
    if not request.is_json:
        return jsonify({"error": "Missing JSON"}), 400
    
    data = request.json
    status = data.get('status')
    
    # 验证状态值是否有效
    valid_statuses = ['pending', 'paid', 'completed', 'cancelled']
    if status not in valid_statuses:
        return jsonify({"error": "无效的状态值"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 开始事务
        conn.begin()
        
        # 获取当前订单状态
        cursor.execute("SELECT status FROM orders WHERE id = %s", (order_id,))
        current_order = cursor.fetchone()
        
        if not current_order:
            return jsonify({"error": "订单不存在"}), 404
            
        # 如果订单已经是完成或取消状态，则不允许更改
        if current_order['status'] in ['completed', 'cancelled']:
            return jsonify({"error": "该订单已经完成或取消，无法更改状态"}), 400

        # 如果要取消订单，恢复库存
        if status == 'cancelled' and current_order['status'] != 'cancelled':
            # 获取订单中的商品信息
            cursor.execute("""
                SELECT product_id, quantity 
                FROM order_products 
                WHERE order_id = %s
            """, (order_id,))
            order_products = cursor.fetchall()
            
            # 恢复每个商品的库存
            for item in order_products:
                cursor.execute("""
                    UPDATE products 
                    SET stock = stock + %s 
                    WHERE id = %s
                """, (item['quantity'], item['product_id']))

        # 更新订单状态
        cursor.execute(
            "UPDATE orders SET status = %s, update_time = CURRENT_TIMESTAMP WHERE id = %s",
            (status, order_id)
        )
        
        conn.commit()
        return jsonify({
            "message": f"订单状态已更新为：{status}",
            "order_id": order_id,
            "status": status
        })
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

# 删除商品路由
@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 首先检查是否有相关订单
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM order_products 
            WHERE product_id = %s
        """, (product_id,))
        result = cursor.fetchone()
        
        if result['count'] > 0:
            return jsonify({"error": "该商品已有订单，无法删除"}), 400
        
        # 删��购物车中的相关项目
        cursor.execute("DELETE FROM cart_items WHERE product_id = %s", (product_id,))
        
        # 删除商品
        cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
        conn.commit()
        
        return jsonify({"message": "商品删除成功"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

# 删除服务路由
@app.route('/api/services/<int:service_id>', methods=['DELETE'])
def delete_service(service_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 首先检查是否有相关订单
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM order_services 
            WHERE service_id = %s
        """, (service_id,))
        result = cursor.fetchone()
        
        if result['count'] > 0:
            return jsonify({"error": "该服务已有订单，无法删除"}), 400
        
        # 删除购物车中的相关项目
        cursor.execute("DELETE FROM cart_items WHERE service_id = %s", (service_id,))
        
        # 删除服务
        cursor.execute("DELETE FROM services WHERE id = %s", (service_id,))
        conn.commit()
        
        return jsonify({"message": "服务删除成功"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

# 获取所有订单的路由（管理员用）
@app.route('/api/admin/orders', methods=['GET'])
def get_all_orders():
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT 
                o.*,
                u.username,
                GROUP_CONCAT(DISTINCT 
                    CONCAT(p.name, ' (', op.quantity, '件)') 
                    SEPARATOR ', '
                ) as products,
                GROUP_CONCAT(DISTINCT 
                    CONCAT(s.name, ' (', DATE_FORMAT(os.appointment_time, '%Y-%m-%d %H:%i'), ')')
                    SEPARATOR ', '
                ) as services
            FROM orders o
            LEFT JOIN users u ON o.user_id = u.id
            LEFT JOIN order_products op ON o.id = op.order_id
            LEFT JOIN products p ON op.product_id = p.id
            LEFT JOIN order_services os ON o.id = os.order_id
            LEFT JOIN services s ON os.service_id = s.id
            GROUP BY o.id
            ORDER BY o.create_time DESC
        """)
        orders = cursor.fetchall()
        
        # 处理时间格式
        for order in orders:
            order['create_time'] = order['create_time'].strftime('%Y-%m-%d %H:%M:%S')
            if order['update_time']:
                order['update_time'] = order['update_time'].strftime('%Y-%m-%d %H:%M:%S')
        
        return jsonify(orders)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

# 添加自定义静态文件路由
@app.route('/images/<path:filename>')
def custom_static(filename):
    return send_from_directory('image', filename)

# 添加删除购物车项目的路由
@app.route('/api/cart/<int:item_id>', methods=['DELETE'])
def delete_cart_item(item_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM cart_items WHERE id = %s", (item_id,))
        conn.commit()
        return jsonify({"message": "商品已从购物车中删除"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

# 添加更新购物车数量的路由
@app.route('/api/cart/<int:item_id>', methods=['PUT'])
def update_cart_item(item_id):
    if not request.is_json:
        return jsonify({"error": "Missing JSON"}), 400
    
    data = request.json
    quantity = data.get('quantity')
    
    if not quantity or quantity < 1:
        return jsonify({"error": "无效的数量"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "UPDATE cart_items SET quantity = %s WHERE id = %s",
            (quantity, item_id)
        )
        conn.commit()
        return jsonify({"message": "购物车已更新"})
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    app.run(debug=True) 