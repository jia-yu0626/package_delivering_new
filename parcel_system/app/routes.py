from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from . import db, models, services
from functools import wraps
from datetime import datetime

main = Blueprint('main', __name__)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/track', methods=['GET', 'POST'])
def track():
    if request.method == 'POST':
        tracking_number = request.form.get('tracking_number')
        return redirect(url_for('main.tracking_result', tracking_number=tracking_number))
    return render_template('track.html')

@main.route('/track/<tracking_number>')
def tracking_result(tracking_number):
    package = services.get_package_by_tracking(tracking_number)
    if not package:
        flash('找不到該追蹤號碼 (Tracking number not found)', 'error')
        return redirect(url_for('main.index'))
    return render_template('tracking_result.html', package=package)

@main.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address')
        
        try:
            new_user = models.Customer(
                username=username,
                full_name=full_name,
                email=email,
                phone=phone,
                address=address,
                role=models.UserRole.CUSTOMER
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            
            # 記錄註冊日誌
            services.log_audit(new_user.id, '用戶註冊', new_user.id, f'新用戶註冊：{new_user.username}')
            
            flash('註冊成功，請登入 (Registration successful, please login)', 'success')
            return redirect(url_for('main.login'))
        except Exception as e:
            db.session.rollback()
            # Check if it's an integrity error (duplicate)
            if 'UNIQUE constraint failed' in str(e) or 'IntegrityError' in str(e):
                flash('使用者名稱或 Email 已存在 (Username or Email already exists)', 'error')
            else:
                flash(f'註冊失敗：{str(e)}', 'error')
                
    return render_template('register.html')

@main.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = db.session.execute(db.select(models.User).filter_by(username=username)).scalar_one_or_none()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['user_name'] = user.full_name
            session['user_role'] = user.role.value
            
            # 記錄登入日誌
            services.log_audit(user.id, '用戶登入', user.id, f'用戶登入：{user.username}')
            
            flash('登入成功 (Login successful)', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('帳號或密碼錯誤 (Invalid credentials)', 'error')
            
    return render_template('login.html')

@main.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))

@main.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    role = session['user_role']
    
    if role == 'customer':
        packages = services.get_user_packages(user_id)
        return render_template('dashboard_customer.html', packages=packages)
    elif role == 'customer_service':
        # Get Exception Packages
        exceptions = services.get_packages_by_status([
            models.PackageStatus.EXCEPTION,
            models.PackageStatus.LOST,
            models.PackageStatus.DELAYED,
            models.PackageStatus.DAMAGED
        ])
        return render_template('dashboard_cs.html', exceptions=exceptions)
    elif role == 'driver':
        packages = services.get_packages_for_driver(session['user_id'])
        return render_template('dashboard_employee.html', packages=packages, is_driver=True)
    elif role == 'admin':
        # Admin only sees pricing management
        return render_template('dashboard_admin.html')
    elif role == 'warehouse':
        # Warehouse sees packages that are not out for delivery or delivered
        recent_packages = db.session.execute(
            db.select(models.Package)
            .filter(models.Package.status.notin_([
                models.PackageStatus.OUT_FOR_DELIVERY,
                models.PackageStatus.DELIVERED
            ]))
            .order_by(models.Package.created_at.desc())
            .limit(20)
        ).scalars().all()
        return render_template('dashboard_employee.html', packages=recent_packages)
    
    return "Unknown Role"

@main.route('/cs/search', methods=['POST'])
@login_required
def cs_search_user():
    if session.get('user_role') not in ['customer_service', 'admin']:
         return "Unauthorized", 403
    
    query = request.form.get('query')
    users = services.search_users(query)
    # Re-render dashboard with search results
    exceptions = services.get_packages_by_status([
            models.PackageStatus.EXCEPTION,
            models.PackageStatus.LOST,
            models.PackageStatus.DELAYED,
            models.PackageStatus.DAMAGED
    ])
    return render_template('dashboard_cs.html', exceptions=exceptions, search_results=users, search_query=query)

@main.route('/cs/customer/<int:user_id>')
@login_required
def cs_customer_detail(user_id):
    if session.get('user_role') not in ['customer_service', 'admin']:
         return "Unauthorized", 403
         
    customer = services.get_user_by_id(user_id)
    if not customer:
        flash('User not found', 'error')
        return redirect(url_for('main.dashboard'))
        
    packages = services.get_user_packages(user_id)
    bills = services.get_customer_bills(user_id)
    
    return render_template('cs_customer_detail.html', customer=customer, packages=packages, bills=bills)

@main.route('/admin/pricing', methods=['GET', 'POST'])
@login_required
def admin_pricing():
    if session.get('user_role') != 'admin':
         return "Unauthorized", 403
         
    if request.method == 'POST':
        rule_id = request.form.get('rule_id')
        base_rate = float(request.form.get('base_rate'))
        rate_per_kg = float(request.form.get('rate_per_kg'))
        
        services.update_pricing_rule(rule_id, base_rate, rate_per_kg)
        
        # 記錄定價規則更新日誌
        services.log_audit(session['user_id'], '更新定價', rule_id, f'更新定價規則：基本費 {base_rate}，每公斤 {rate_per_kg}')
        
        flash('定價規則已更新', 'success')
        
    rules = services.get_all_pricing_rules()
    return render_template('admin_pricing.html', rules=rules)


@main.route('/my_bills')
@login_required
def my_bills():
    if session['user_role'] != 'customer':
        return "Unauthorized", 403
    
    bills = db.session.execute(
        db.select(models.Bill).filter_by(customer_id=session['user_id']).order_by(models.Bill.created_at.desc())
    ).scalars().all()
    user = db.session.get(models.Customer, session['user_id'])
    
    # 計算未付款帳單總額
    total_unpaid = sum(bill.amount for bill in bills if not bill.is_paid)
    
    return render_template('my_bills.html', bills=bills, balance=user.balance, customer=user, total_unpaid=total_unpaid)

@main.route('/pay_bill/<int:bill_id>', methods=['POST'])
@login_required
def pay_bill(bill_id):
    bill = db.session.get(models.Bill, bill_id)
    if not bill or bill.customer_id != session['user_id']:
        return "Unauthorized or Not Found", 404
        
    method = request.form.get('method')
    
    if method == 'balance':
        success, msg = services.pay_bill_with_balance(bill_id, session['user_id'])
        if success:
            # 記錄餘額付款日誌
            services.log_audit(session['user_id'], '帳單付款', bill_id, f'使用餘額付款帳單 #{bill_id}')
            flash(msg, 'success')
        else:
            flash(msg, 'error')
    else:
        # Cash/Credit (Mock)
        if method in models.PaymentMethod.__members__:
            bill.payment_method = models.PaymentMethod[method]

        bill.is_paid = True
        bill.paid_at = datetime.now()
        db.session.commit()
        
        # 記錄付款日誌
        services.log_audit(session['user_id'], '帳單付款', bill_id, f'付款帳單 #{bill_id}，金額 {bill.amount}，方式 {method}')
        flash('付款成功 (Payment Successful)', 'success')
        
    return redirect(url_for('main.my_bills'))

@main.route('/pay_all_bills', methods=['POST'])
@login_required
def pay_all_bills():
    if session['user_role'] != 'customer':
        return "Unauthorized", 403
    
    method = request.form.get('method')
    
    # Get all unpaid bills for the user
    bills = db.session.execute(
        db.select(models.Bill).filter_by(customer_id=session['user_id'], is_paid=False)
    ).scalars().all()
    
    if not bills:
        flash('沒有待付款的帳單 (No unpaid bills)', 'info')
        return redirect(url_for('main.my_bills'))
        
    count = 0
    total_amount = 0
    
    for bill in bills:
        # Mock payment processing
        if method in models.PaymentMethod.__members__:
            bill.payment_method = models.PaymentMethod[method]
        
        bill.is_paid = True
        bill.paid_at = datetime.now()
        count += 1
        total_amount += bill.amount
        
    db.session.commit()
    
    services.log_audit(session['user_id'], '批量付款', None, f'批量付款 {count} 筆帳單，總額 {total_amount}，方式 {method}')
    flash(f'成功付款 {count} 筆帳單 (Successfully paid {count} bills)', 'success')
    
    return redirect(url_for('main.my_bills'))

@main.route('/create_package', methods=['GET', 'POST'])
@login_required
def create_package():
    if session.get('user_role') != 'customer':
        flash("只有客戶可以寄送包裹 (Customers only)", "error")
        return redirect(url_for('main.dashboard'))

    current_user = db.session.get(models.Customer, session['user_id'])
    
    if request.method == 'POST':
        recipient_data = {
            'name': request.form.get('recipient_name'),
            'address': request.form.get('recipient_address'),
            'phone': request.form.get('recipient_phone')
        }
        package_data = {
            'weight': float(request.form.get('weight')),
            'width': float(request.form.get('width')),
            'height': float(request.form.get('height')),
            'length': float(request.form.get('length')),
            'package_type': request.form.get('package_type'),
            'delivery_speed': request.form.get('delivery_speed'),
            'content_description': request.form.get('content_description'),
            'is_fragile': 'is_fragile' in request.form,
            'is_hazardous': 'is_hazardous' in request.form,
            'is_international': 'is_international' in request.form
        }
        
        # 預設使用現金付款
        payment_method = models.PaymentMethod.CASH

        try:
            pkg = services.create_package(session['user_id'], recipient_data, package_data, payment_method)
            
            # 記錄建立包裹日誌
            services.log_audit(session['user_id'], '建立包裹', pkg.tracking_number, f'建立包裹，收件人：{recipient_data["name"]}，運送方式：{package_data["delivery_speed"]}')
            
            flash(f'包裹建立成功！追蹤號碼：{pkg.tracking_number}', 'success')
            return redirect(url_for('main.dashboard'))
        except Exception as e:
            flash(f'建立失敗：{str(e)}', 'error')
            
    return render_template('create_package.html', user=current_user)

@main.route('/update_status/<tracking_number>', methods=['POST'])
@login_required
def update_status(tracking_number):
    # Only employees should do this
    if session.get('user_role') == 'customer':
        return "Unauthorized", 403
        
    status = request.form.get('status')
    location = request.form.get('location')
    description = request.form.get('description') or '狀態更新'  # 預設描述
    
    # 司機只能更新為「已送達」或異常狀態
    driver_allowed_statuses = ['DELIVERED', 'EXCEPTION', 'LOST', 'DELAYED', 'DAMAGED']
    if session.get('user_role') == 'driver' and status not in driver_allowed_statuses:
        flash('司機只能更新狀態為「已送達」或異常狀態', 'error')
        return redirect(url_for('main.tracking_result', tracking_number=tracking_number))
    
    # 倉庫人員：正常狀態只能更新到 PICKED_UP、IN_TRANSIT、SORTING 且只能往前進；異常狀態隨時可選
    exception_statuses = ['EXCEPTION', 'LOST', 'DELAYED', 'DAMAGED']
    warehouse_allowed_statuses = ['PICKED_UP', 'IN_TRANSIT', 'SORTING']
    if session.get('user_role') == 'warehouse':
        # 如果不是異常狀態，則檢查正常狀態的限制
        if status not in exception_statuses:
            if status not in warehouse_allowed_statuses:
                flash('倉庫人員只能更新狀態為「已收件」、「運輸中」、「分揀中」或異常狀態', 'error')
                return redirect(url_for('main.tracking_result', tracking_number=tracking_number))
            
            # 驗證只能往前進不能往回
            status_order = {'CREATED': 0, 'PICKED_UP': 1, 'IN_TRANSIT': 2, 'SORTING': 3}
            package = services.get_package_by_tracking(tracking_number)
            current_order = status_order.get(package.status.name, 0)
            new_order = status_order.get(status, 0)
            
            if new_order <= current_order:
                flash('不能將狀態往回更改，只能選擇當前狀態之後的進度', 'error')
                return redirect(url_for('main.tracking_result', tracking_number=tracking_number))
    
    services.add_tracking_event(tracking_number, status, location, description, session['user_id'])
    
    # 記錄狀態更新日誌
    services.log_audit(session['user_id'], '更新狀態', tracking_number, f'更新狀態為 {status}，地點：{location}')
    
    flash('狀態更新成功', 'success')
    
    # 司機和倉庫人員跳轉到儀表板清單頁面
    if session.get('user_role') in ['driver', 'warehouse']:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('main.tracking_result', tracking_number=tracking_number))

@main.route('/admin/auto_assign', methods=['POST'])
@login_required
def auto_assign():
    if session.get('user_role') not in ['warehouse', 'admin']:
         return "Unauthorized", 403
         
    count = services.auto_assign_packages()
    if count == 0:
        flash('配送失敗，只能配送分揀中的包裹', 'error')
    else:
        # 記錄自動分配日誌
        services.log_audit(session['user_id'], '自動分配', None, f'自動分配 {count} 個包裹給司機')
        flash(f'已自動分配 {count} 個包裹給司機 (Assigned {count} packages)', 'success')
    return redirect(url_for('main.dashboard'))

@main.route('/edit_package/<tracking_number>', methods=['GET', 'POST'])
@login_required
def edit_package(tracking_number):
    # Only employees (Warehouse/Admin mainly) should do this
    if session.get('user_role') == 'customer':
        return "Unauthorized", 403
        
    package = services.get_package_by_tracking(tracking_number)
    if not package:
        flash('找不到包裹', 'error')
        return redirect(url_for('main.dashboard'))

    if request.method == 'POST':
        # 先記錄原始值以便比對變化
        original_data = {
            'weight': package.weight,
            'width': package.width,
            'height': package.height,
            'length': package.length,
            'delivery_speed': package.delivery_speed.name,
            'is_fragile': package.is_fragile,
            'is_hazardous': package.is_hazardous,
            'is_international': package.is_international
        }
        
        package_data = {
            'weight': max(0, float(request.form.get('weight'))),
            'width': max(0, float(request.form.get('width'))),
            'height': max(0, float(request.form.get('height'))),
            'length': max(0, float(request.form.get('length'))),
            'delivery_speed': request.form.get('delivery_speed'),
            'is_fragile': 'is_fragile' in request.form,
            'is_hazardous': 'is_hazardous' in request.form,
            'is_international': 'is_international' in request.form
        }
        
        try:
            services.update_package_details(tracking_number, package_data)
            
            # 記錄編輯包裹日誌 - 只記錄有修改的屬性
            changes = []
            if original_data['weight'] != package_data['weight']:
                changes.append(f'重量:{original_data["weight"]}→{package_data["weight"]}kg')
            if original_data['width'] != package_data['width'] or original_data['height'] != package_data['height'] or original_data['length'] != package_data['length']:
                changes.append(f'尺寸:{original_data["width"]}x{original_data["height"]}x{original_data["length"]}→{package_data["width"]}x{package_data["height"]}x{package_data["length"]}cm')
            if original_data['delivery_speed'] != package_data['delivery_speed']:
                changes.append(f'運送:{original_data["delivery_speed"]}→{package_data["delivery_speed"]}')
            if original_data['is_fragile'] != package_data['is_fragile']:
                changes.append(f'易碎:{"是" if package_data["is_fragile"] else "否"}')
            if original_data['is_hazardous'] != package_data['is_hazardous']:
                changes.append(f'危險品:{"是" if package_data["is_hazardous"] else "否"}')
            if original_data['is_international'] != package_data['is_international']:
                changes.append(f'國際件:{"是" if package_data["is_international"] else "否"}')
            
            if changes:
                services.log_audit(session['user_id'], '編輯包裹', tracking_number, ' | '.join(changes))
            
            flash('包裹屬性已更新 (Attributes Updated)', 'success')
            return redirect(url_for('main.tracking_result', tracking_number=tracking_number))
        except Exception as e:
            flash(f'更新失敗: {str(e)}', 'error')
            
    return render_template('edit_package.html', package=package)

@main.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """包裹多條件搜尋"""
    # 只有客服、管理員、倉儲人員可以使用搜尋功能
    if session.get('user_role') not in ['customer_service', 'admin', 'warehouse']:
        flash('您沒有權限使用搜尋功能', 'error')
        return redirect(url_for('main.dashboard'))
    
    packages = []
    drivers = services.get_all_drivers()
    locations = services.get_all_warehouse_locations()
    
    if request.method == 'POST':
        # 取得搜尋條件
        tracking_number = request.form.get('tracking_number', '').strip() or None
        customer_username = request.form.get('customer_username', '').strip() or None
        date_from_str = request.form.get('date_from', '').strip()
        date_to_str = request.form.get('date_to', '').strip()
        vehicle_id = request.form.get('vehicle_id', '').strip() or None
        warehouse_location = request.form.get('warehouse_location', '').strip() or None
        
        # 轉換日期格式
        date_from = None
        date_to = None
        if date_from_str:
            try:
                date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
            except ValueError:
                flash('起始日期格式錯誤', 'error')
        if date_to_str:
            try:
                # 設定為當天結束時間 (23:59:59)
                date_to = datetime.strptime(date_to_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            except ValueError:
                flash('結束日期格式錯誤', 'error')
        
        # 執行搜尋
        packages = services.search_packages(
            tracking_number=tracking_number,
            customer_username=customer_username,
            date_from=date_from,
            date_to=date_to,
            vehicle_id=vehicle_id,
            warehouse_location=warehouse_location
        )
        
        # 記錄搜尋日誌
        search_criteria = []
        if tracking_number:
            search_criteria.append(f'追蹤號:{tracking_number}')
        if customer_username:
            search_criteria.append(f'客戶:{customer_username}')
        if date_from_str:
            search_criteria.append(f'起始:{date_from_str}')
        if date_to_str:
            search_criteria.append(f'結束:{date_to_str}')
        if vehicle_id:
            search_criteria.append(f'車輛:{vehicle_id}')
        if warehouse_location:
            search_criteria.append(f'倉儲:{warehouse_location}')
        
        if search_criteria:
            services.log_audit(session['user_id'], '搜尋包裹', None, ' | '.join(search_criteria) + f' (找到 {len(packages)} 筆)')
        
        flash(f'搜尋結果: 找到 {len(packages)} 筆包裹', 'info')
    
    return render_template('search.html', 
                          packages=packages, 
                          drivers=drivers, 
                          locations=locations)

@main.route('/admin/users')
@login_required
def admin_users():
    """管理員：使用者列表頁面"""
    if session.get('user_role') != 'admin':
        return "Unauthorized", 403
    
    users = services.get_all_users()
    return render_template('admin_users.html', users=users)

@main.route('/admin/create_user', methods=['GET', 'POST'])
@login_required
def admin_create_user():
    """管理員：創建新帳號"""
    if session.get('user_role') != 'admin':
        return "Unauthorized", 403
    
    if request.method == 'POST':
        # 基本欄位
        username = request.form.get('username')
        password = request.form.get('password')
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        address = request.form.get('address', '')
        role = request.form.get('role')
        
        try:
            # 根據角色創建對應的用戶實體
            if role == 'customer':
                customer_type = request.form.get('customer_type', 'NON_CONTRACT')
                new_user = models.Customer(
                    username=username,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    address=address,
                    role=models.UserRole.CUSTOMER,
                    customer_type=models.CustomerType[customer_type]
                )
                
                # 預付客戶的專屬欄位
                if customer_type == 'PREPAID':
                    balance = float(request.form.get('balance', 0))
                    prepaid_by = request.form.get('prepaid_by', '')
                    new_user.balance = balance
                    new_user.prepaid_by = prepaid_by
                    
            elif role == 'driver':
                vehicle_id = request.form.get('vehicle_id', '')
                new_user = models.Driver(
                    username=username,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    address=address,
                    role=models.UserRole.DRIVER,
                    vehicle_id=vehicle_id
                )
                
            elif role == 'warehouse':
                warehouse_location_id = request.form.get('warehouse_location_id', '')
                new_user = models.WarehouseStaff(
                    username=username,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    address=address,
                    role=models.UserRole.WAREHOUSE,
                    warehouse_location_id=warehouse_location_id
                )
                
            elif role == 'customer_service':
                new_user = models.Employee(
                    username=username,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    address=address,
                    role=models.UserRole.CS
                )
                
            elif role == 'admin':
                new_user = models.Employee(
                    username=username,
                    full_name=full_name,
                    email=email,
                    phone=phone,
                    address=address,
                    role=models.UserRole.ADMIN
                )
            else:
                flash('無效的角色類型', 'error')
                return redirect(url_for('main.admin_create_user'))
            
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            
            # 記錄操作日誌
            services.log_audit(session['user_id'], '建立帳號', new_user.id, 
                             f'管理員建立帳號：{username}，角色：{role}')
            
            flash(f'帳號 {username} 建立成功！', 'success')
            return redirect(url_for('main.admin_users'))
            
        except Exception as e:
            db.session.rollback()
            if 'UNIQUE constraint failed' in str(e) or 'IntegrityError' in str(e):
                flash('使用者名稱或 Email 已存在', 'error')
            else:
                flash(f'建立失敗：{str(e)}', 'error')
    
    return render_template('admin_create_user.html')

@main.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    """管理員：刪除帳號"""
    if session.get('user_role') != 'admin':
        return "Unauthorized", 403
    
    # 不能刪除自己
    if user_id == session.get('user_id'):
        flash('無法刪除自己的帳號', 'error')
        return redirect(url_for('main.admin_users'))
    
    user = db.session.get(models.User, user_id)
    if not user:
        flash('找不到該使用者', 'error')
        return redirect(url_for('main.admin_users'))
    
    # 檢查是否為最後一個管理員
    if user.role == models.UserRole.ADMIN:
        admin_count = db.session.execute(
            db.select(models.User).filter_by(role=models.UserRole.ADMIN)
        ).scalars().all()
        if len(admin_count) <= 1:
            flash('無法刪除最後一個管理員帳號', 'error')
            return redirect(url_for('main.admin_users'))
    
    username = user.username
    
    try:
        # 如果是客戶，需要先刪除相關的包裹、帳單、追蹤事件
        if user.role == models.UserRole.CUSTOMER:
            # 取得該客戶的所有包裹
            packages = db.session.execute(
                db.select(models.Package).filter_by(sender_id=user_id)
            ).scalars().all()
            
            for package in packages:
                # 刪除追蹤事件
                db.session.execute(
                    db.delete(models.TrackingEvent).where(models.TrackingEvent.package_id == package.id)
                )
                # 刪除帳單
                db.session.execute(
                    db.delete(models.Bill).where(models.Bill.package_id == package.id)
                )
                # 刪除包裹
                db.session.delete(package)
        
        # 刪除該用戶的審計日誌
        db.session.execute(
            db.delete(models.AuditLog).where(models.AuditLog.user_id == user_id)
        )
        
        # 刪除用戶
        db.session.delete(user)
        db.session.commit()
        
        # 記錄操作日誌（使用當前管理員的 ID）
        services.log_audit(session['user_id'], '刪除帳號', user_id, 
                         f'管理員刪除帳號：{username}')
        
        flash(f'帳號 {username} 已成功刪除', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'刪除失敗：{str(e)}', 'error')
    
    return redirect(url_for('main.admin_users'))
