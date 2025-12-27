import uuid
from datetime import datetime
from . import db, models
from sqlalchemy.exc import IntegrityError

def generate_tracking_number():
    """Generate a unique tracking number."""
    return f"TW-{uuid.uuid4().hex[:8].upper()}"

def calculate_shipping_cost(weight, service_type_enum):
    """Calculate shipping cost based on weight and service type."""
    rule = db.session.execute(
        db.select(models.PricingRule).filter_by(service_type=service_type_enum)
    ).scalar_one_or_none()
    
    if not rule:
        return 0.0 # Default or error fallback
        
    cost = rule.base_rate + (weight * rule.rate_per_kg)
    return round(cost, 2)

def create_package(sender_id, recipient_data, package_data, payment_method=models.PaymentMethod.CASH):
    """
    Create a new package.
    recipient_data: dict with name, address, phone
    package_data: dict with weight, dimensions, type, speed, flags
    payment_method: PaymentMethod enum
    """
    tracking_number = generate_tracking_number()
    
    # Validation
    if package_data['weight'] <= 0 or package_data['width'] <= 0 or package_data['height'] <= 0 or package_data['length'] <= 0:
        raise ValueError("重量與尺寸必須大於 0 (Weight and dimensions must be positive)")

    # Calculate Cost
    cost = calculate_shipping_cost(
        package_data['weight'], 
        models.DeliverySpeed[package_data['delivery_speed']]
    )
    
    sender = db.session.get(models.Customer, sender_id)
    
    # Force use of PREPAID payment method for PREPAID customers
    if sender.customer_type == models.CustomerType.PREPAID:
        payment_method = models.PaymentMethod.PREPAID

    is_paid = False
    paid_at = None
    
    # 1. Handle Prepaid Balance Deduction
    if payment_method == models.PaymentMethod.PREPAID:
        # User requested that Prepaid customers don't need balance and are always Paid
        # We deduce the cost (allowing negative balance) or just track it
        sender.balance -= cost
        is_paid = True
        paid_at = datetime.now()
            
    # 2. Handle Online Payments (Mock)
    elif payment_method in [models.PaymentMethod.CREDIT_CARD, models.PaymentMethod.MOBILE_PAYMENT]:
        is_paid = True
        paid_at = datetime.now()
        
    # 3. Monthly Settlement (Contract) or Cash -> Pay Later
    
    new_package = models.Package(
        tracking_number=tracking_number,
        sender_id=sender_id,
        recipient_name=recipient_data['name'],
        recipient_address=recipient_data['address'],
        recipient_phone=recipient_data['phone'],
        weight=package_data['weight'],
        width=package_data['width'],
        height=package_data['height'],
        length=package_data['length'],
        declared_value=package_data.get('declared_value', 0),
        content_description=package_data.get('content_description', ''),
        package_type=models.PackageType[package_data['package_type']],
        delivery_speed=models.DeliverySpeed[package_data['delivery_speed']],
        is_hazardous=package_data.get('is_hazardous', False),
        is_fragile=package_data.get('is_fragile', False),
        is_international=package_data.get('is_international', False),
        shipping_cost=cost,
        status=models.PackageStatus.CREATED
    )
    
    db.session.add(new_package)
    
    # Add initial tracking event
    initial_event = models.TrackingEvent(
        package=new_package,
        status=models.PackageStatus.CREATED,
        location="系統接單 (System)",
        description="訂單已建立，等待取件 (Order created, waiting for pickup)"
    )
    db.session.add(initial_event)

    # Create Bill
    bill = models.Bill(
        customer_id=sender_id,
        package=new_package,
        amount=cost,
        is_paid=is_paid,
        paid_at=paid_at,
        payment_method=payment_method
    )
    db.session.add(bill)
    
    try:
        db.session.commit()
        return new_package
    except IntegrityError:
        db.session.rollback()
        raise Exception("Database error")

def get_package_by_tracking(tracking_number):
    return db.session.execute(
        db.select(models.Package).filter_by(tracking_number=tracking_number)
    ).scalar_one_or_none()

def add_tracking_event(tracking_number, status_str, location, description, user_id=None):
    package = get_package_by_tracking(tracking_number)
    if not package:
        return False
        
    # Try to find the status by name or value
    try:
        if status_str in models.PackageStatus.__members__:
            new_status = models.PackageStatus[status_str]
        else:
            # Try by value
            new_status = models.PackageStatus(status_str)
    except ValueError:
        return False

    package.status = new_status
    
    event = models.TrackingEvent(
        package=package,
        status=new_status,
        location=location,
        description=description,
        handled_by_id=user_id
    )
    
    db.session.add(event)
    db.session.commit()
    return True

def get_user_packages(user_id):
    return db.session.execute(
        db.select(models.Package).filter_by(sender_id=user_id).order_by(models.Package.created_at.desc())
    ).scalars().all()

def update_package_details(tracking_number, package_data):
    """
    Update package details (for warehouse confirmation).
    """
    package = get_package_by_tracking(tracking_number)
    if not package:
        raise ValueError("Package not found")
        
    # Update fields
    if 'weight' in package_data:
        package.weight = package_data['weight']
    if 'width' in package_data:
        package.width = package_data['width']
    if 'height' in package_data:
        package.height = package_data['height']
    if 'length' in package_data:
        package.length = package_data['length']
    
    # Recalculate cost if weight/speed changed
    if 'weight' in package_data or 'delivery_speed' in package_data:
        speed = models.DeliverySpeed[package_data.get('delivery_speed', package.delivery_speed.name)]
        weight = package_data.get('weight', package.weight)
        
        # Update speed if provided
        if 'delivery_speed' in package_data:
            package.delivery_speed = speed
            
        new_cost = calculate_shipping_cost(weight, speed)
        package.shipping_cost = new_cost
        
        # Update bill amount if unpaid? (Optional logic, let's update it for now if unpaid)
        if package.bill and not package.bill.is_paid:
            package.bill.amount = new_cost

    # Update flags
    if 'is_fragile' in package_data:
        package.is_fragile = package_data['is_fragile']
    if 'is_hazardous' in package_data:
        package.is_hazardous = package_data['is_hazardous']
    if 'is_international' in package_data:
        package.is_international = package_data['is_international']
        
    db.session.commit()
    return package

def get_packages_by_status(status_list):
    """Get packages matching a list of statuses."""
    return db.session.execute(
        db.select(models.Package)
        .filter(models.Package.status.in_(status_list))
        .order_by(models.Package.created_at.desc())
    ).scalars().all()

def search_users(query_str):
    """Search users by username, email, or phone."""
    search = f"%{query_str}%"
    return db.session.execute(
        db.select(models.User).filter(
            (models.User.username.like(search)) |
            (models.User.email.like(search)) |
            (models.User.phone.like(search)) |
            (models.User.full_name.like(search))
        )
    ).scalars().all()

def get_user_by_id(user_id):
    return db.session.get(models.User, user_id)

def get_customer_bills(customer_id):
    return db.session.execute(
        db.select(models.Bill).filter_by(customer_id=customer_id).order_by(models.Bill.created_at.desc())
    ).scalars().all()

def get_all_pricing_rules():
    return db.session.execute(db.select(models.PricingRule)).scalars().all()

def update_pricing_rule(rule_id, base_rate, rate_per_kg):
    rule = db.session.get(models.PricingRule, rule_id)
    if rule:
        rule.base_rate = base_rate
        rule.rate_per_kg = rate_per_kg
        db.session.commit()
        return True
    return False

def get_all_users():
    return db.session.execute(db.select(models.User)).scalars().all()

def update_user_role(user_id, new_role_str):
    user = db.session.get(models.User, user_id)
    if user and new_role_str in models.UserRole.__members__:
        user.role = models.UserRole[new_role_str]
        db.session.commit()
        return True
    return False

def get_packages_for_driver(driver_id=None):
    """
    Get packages assigned to a driver.
    """
    query = db.select(models.Package).filter(
        models.Package.status.in_([
            models.PackageStatus.OUT_FOR_DELIVERY,
            models.PackageStatus.SORTING,
            models.PackageStatus.PICKED_UP
        ])
    )
    
    if driver_id:
        query = query.filter_by(assigned_driver_id=driver_id)
        
    return db.session.execute(
        query.order_by(models.Package.estimated_delivery.asc())
    ).scalars().all()

def auto_assign_packages():
    """
    Automatically assign unassigned SORTING packages to available drivers.
    Returns: Number of packages assigned.
    """
    # 1. Get unassigned packages (Status: SORTING)
    unassigned_packages = db.session.execute(
        db.select(models.Package).filter_by(
            status=models.PackageStatus.SORTING,
            assigned_driver_id=None
        )
    ).scalars().all()
    
    if not unassigned_packages:
        return 0
        
    # 2. Get all drivers
    drivers = db.session.execute(
        db.select(models.User).filter_by(role=models.UserRole.DRIVER)
    ).scalars().all()
    
    if not drivers:
        return 0 # No drivers to assign to
        
    # 3. Round-Robin Assignment
    assigned_count = 0
    num_drivers = len(drivers)
    
    for index, package in enumerate(unassigned_packages):
        driver = drivers[index % num_drivers]
        package.assigned_driver_id = driver.id
        # --- 狀態改動邏輯 ---
        if package.status == models.PackageStatus.SORTING:
            package.status = models.PackageStatus.OUT_FOR_DELIVERY
            
            # 新增 TrackingEvent 記錄
            event = models.TrackingEvent(
                package=package,
                status=models.PackageStatus.OUT_FOR_DELIVERY,
                location="系統自動分配",
                description=f"包裹已分配給司機 {driver.full_name} 進行派送"
            )
            db.session.add(event)
            
        assigned_count += 1
        
    db.session.commit()
    return assigned_count

def top_up_balance(user_id, amount):
    customer = db.session.get(models.Customer, user_id)
    if customer:
        customer.balance += amount
        db.session.commit()
        return True
    return False

def pay_bill_with_balance(bill_id, user_id):
    bill = db.session.get(models.Bill, bill_id)
    if not bill or bill.customer_id != user_id:
        return False, "Bill not found"
    
    if bill.is_paid:
        return False, "Already paid"
        
    customer = db.session.get(models.Customer, user_id)
    if customer.balance >= bill.amount:
        customer.balance -= bill.amount
        bill.is_paid = True
        bill.paid_at = datetime.now()
        db.session.commit()
        return True, "Payment successful"
    else:
        return False, "Insufficient balance"

def log_audit(user_id, action, target_id=None, details=None):
    """
    記錄系統操作日誌
    :param user_id: 操作者的使用者 ID
    :param action: 執行的動作 (例如: UPDATE_STATUS, ASSIGN_DRIVER, UPDATE_PRICING)
    :param target_id: 被操作的對象 (例如: 追蹤號碼、用戶ID)
    :param details: 額外的描述資訊
    """
    log_entry = models.AuditLog(
        user_id=user_id,
        action=action,
        target_id=str(target_id) if target_id else None,
        details=details
    )
    db.session.add(log_entry)
    db.session.commit()
    return log_entry

def search_packages(tracking_number=None, customer_username=None, 
                   date_from=None, date_to=None, 
                   vehicle_id=None, warehouse_location=None):
    """
    多條件搜尋包裹
    :param tracking_number: 追蹤編號 (模糊比對)
    :param customer_username: 客戶帳號 (模糊比對)
    :param date_from: 運送日期起始 (datetime)
    :param date_to: 運送日期結束 (datetime)
    :param vehicle_id: 運輸載具識別碼 (貨車車牌)
    :param warehouse_location: 倉儲地點 (從 TrackingEvent 搜尋)
    :return: 符合條件的包裹列表
    """
    query = db.select(models.Package)
    
    # 追蹤編號模糊搜尋
    if tracking_number:
        query = query.filter(models.Package.tracking_number.like(f"%{tracking_number}%"))
    
    # 客戶帳號搜尋 (透過 sender 關聯)
    if customer_username:
        query = query.join(models.Customer, models.Package.sender_id == models.Customer.id)
        query = query.filter(models.Customer.username.like(f"%{customer_username}%"))
    
    # 運送日期範圍搜尋
    if date_from:
        query = query.filter(models.Package.created_at >= date_from)
    if date_to:
        query = query.filter(models.Package.created_at <= date_to)
    
    # 運輸載具識別碼搜尋 (透過 assigned_driver 關聯到 Driver)
    if vehicle_id:
        query = query.join(models.Driver, models.Package.assigned_driver_id == models.Driver.id)
        query = query.filter(models.Driver.vehicle_id.like(f"%{vehicle_id}%"))
    
    # 倉儲地點搜尋 (透過 TrackingEvent 的 location)
    if warehouse_location:
        subquery = db.select(models.TrackingEvent.package_id).filter(
            models.TrackingEvent.location.like(f"%{warehouse_location}%")
        ).distinct()
        query = query.filter(models.Package.id.in_(subquery))
    
    # 按建立時間排序
    query = query.order_by(models.Package.created_at.desc())
    
    return db.session.execute(query).scalars().all()

def get_all_drivers():
    """
    取得所有司機 (用於下拉選單)
    :return: 司機列表，包含 id, full_name, vehicle_id
    """
    return db.session.execute(
        db.select(models.Driver)
    ).scalars().all()

def get_all_warehouse_locations():
    """
    取得所有倉儲地點 (從 WarehouseStaff 和 TrackingEvent 取得)
    :return: 倉儲地點列表 (不重複)
    """
    locations = set()
    
    # 從 WarehouseStaff 取得倉庫編號
    warehouse_staff = db.session.execute(
        db.select(models.WarehouseStaff.warehouse_location_id)
        .filter(models.WarehouseStaff.warehouse_location_id.isnot(None))
    ).scalars().all()
    locations.update(warehouse_staff)
    
    # 從 TrackingEvent 取得所有掃描地點
    event_locations = db.session.execute(
        db.select(models.TrackingEvent.location).distinct()
    ).scalars().all()
    locations.update(event_locations)
    
    return sorted(list(locations))
