from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column, backref
from werkzeug.security import generate_password_hash, check_password_hash
import enum
from .extensions import Base

# --- Enums (列舉：定義固定選項，確保資料一致性) ---

class UserRole(enum.Enum):
    """使用者角色類型"""
    CUSTOMER = "customer"        # 客戶
    DRIVER = "driver"            # 司機
    WAREHOUSE = "warehouse"      # 倉儲人員
    ADMIN = "admin"              # 管理員
    CS = "customer_service"      # 客服人員

class CustomerType(enum.Enum):
    """客戶分類"""
    CONTRACT = "contract"        # 合約客戶 (通常是公司長期配合)
    NON_CONTRACT = "non_contract" # 一般散客
    PREPAID = "prepaid"          # 預付型客戶

class PackageType(enum.Enum):
    """包裹包裝類型"""
    ENVELOPE = "envelope"        # 信封/平郵
    SMALL_BOX = "small_box"      # 小型箱
    MEDIUM_BOX = "medium_box"    # 中型箱
    LARGE_BOX = "large_box"      # 大型箱

class DeliverySpeed(enum.Enum):
    """運送時效等級"""
    OVERNIGHT = "overnight"      # 隔夜達 (最快)
    TWO_DAY = "two_day"          # 兩日達
    STANDARD = "standard"        # 標準速遞
    ECONOMY = "economy"          # 經濟速遞 (最慢/便宜)

class PackageStatus(enum.Enum):
    """包裹目前的物流狀態"""
    CREATED = "created"           # 已建立運單
    PICKED_UP = "picked_up"       # 司機已取件
    IN_TRANSIT = "in_transit"     # 運輸中 (幹線運輸)
    SORTING = "sorting"           # 分揀中心處理中
    OUT_FOR_DELIVERY = "out_for_delivery" # 末端派送中
    DELIVERED = "delivered"       # 已成功送達
    EXCEPTION = "exception"       # 物流異常
    LOST = "lost"                 # 遺失
    DELAYED = "delayed"           # 延誤
    DAMAGED = "damaged"           # 損毀

class PaymentMethod(enum.Enum):
    """支付方式"""
    MONTHLY = "monthly"          # 月結 (合約戶常用)
    CASH = "cash"                # 現金
    CREDIT_CARD = "credit_card"  # 信用卡
    MOBILE_PAYMENT = "mobile_payment" # 行動支付 (LinePay, ApplePay等)
    PREPAID = "prepaid"          # 預付扣款

# --- 共用的狀態標籤字典 (讓 Package 和 TrackingEvent 同步) ---
PACKAGE_STATUS_LABELS = {
    PackageStatus.CREATED: "已建立",
    PackageStatus.PICKED_UP: "起運地收件",
    PackageStatus.IN_TRANSIT: "運輸至物流中心",
    PackageStatus.SORTING: "分揀中",
    PackageStatus.OUT_FOR_DELIVERY: "派送中",
    PackageStatus.DELIVERED: "已送達",
    PackageStatus.EXCEPTION: "異常狀況",
    PackageStatus.LOST: "遺失包裹",
    PackageStatus.DELAYED: "配送延誤",
    PackageStatus.DAMAGED: "包裹損毀"
}

# --- Models (類別：對應資料庫表格) ---

class User(Base):
    """使用者基礎類別 (採用 Joined Table Inheritance 多型設計)"""
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str] = mapped_column(String(200), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.CUSTOMER)
    
    # 用於區分子類別（Customer/Employee）的欄位
    type: Mapped[str] = mapped_column(String(50))
    
    __mapper_args__ = {
        'polymorphic_identity': 'user',
        'polymorphic_on': type
    }

    def set_password(self, password):
        """密碼加密存儲"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """驗證密碼是否正確"""
        return check_password_hash(self.password_hash, password)

class Customer(User):
    """客戶詳細資料 (繼承自 User)"""
    __tablename__ = 'customers'
    
    id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    customer_type: Mapped[CustomerType] = mapped_column(Enum(CustomerType), default=CustomerType.NON_CONTRACT)
    billing_preference: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), default=PaymentMethod.CASH)
    balance: Mapped[float] = mapped_column(Float, default=0.0) # 僅適用於預付型客戶
    prepaid_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # 預付方名稱 (例如: 台灣積體電路股份有限公司)
    
    # 關聯設定：一個客戶可以擁有多個包裹與帳單
    packages: Mapped[List["Package"]] = relationship("Package", back_populates="sender")
    bills: Mapped[List["Bill"]] = relationship("Bill", back_populates="customer")

    __mapper_args__ = {
        'polymorphic_identity': 'customer',
    }

    @property
    def type_label(self):
        """回傳客戶類型的中文顯示名稱"""
        labels = {
            CustomerType.CONTRACT: "合約客戶",
            CustomerType.NON_CONTRACT: "非合約客戶",
            CustomerType.PREPAID: "預付客戶"
        }
        return labels.get(self.customer_type, "一般客戶")

class Employee(User):
    """員工基礎資料 (繼承自 User)"""
    __tablename__ = 'employees'
    id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    department: Mapped[str] = mapped_column(String(50), nullable=True)
    
    __mapper_args__ = {
        'polymorphic_identity': 'employee',
    }

class Package(Base):
    """包裹主資料表格"""
    __tablename__ = 'packages'

    id: Mapped[int] = mapped_column(primary_key=True)
    tracking_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False) # 物流單號
    sender_id: Mapped[int] = mapped_column(ForeignKey('customers.id'), nullable=False)
    
    # 收件人資訊
    recipient_name: Mapped[str] = mapped_column(String(100), nullable=False)
    recipient_address: Mapped[str] = mapped_column(String(200), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # 規格資訊
    weight: Mapped[float] = mapped_column(Float, nullable=False) # 重量 (kg)
    width: Mapped[float] = mapped_column(Float, nullable=False)  # 寬 (cm)
    height: Mapped[float] = mapped_column(Float, nullable=False) # 高 (cm)
    length: Mapped[float] = mapped_column(Float, nullable=False) # 長 (cm)
    declared_value: Mapped[float] = mapped_column(Float, default=0.0) # 報值金額 (保險用)
    content_description: Mapped[str] = mapped_column(String(255), nullable=True) # 內容物描述
    
    # 服務選項
    package_type: Mapped[PackageType] = mapped_column(Enum(PackageType), default=PackageType.SMALL_BOX)
    delivery_speed: Mapped[DeliverySpeed] = mapped_column(Enum(DeliverySpeed), default=DeliverySpeed.STANDARD)
    status: Mapped[PackageStatus] = mapped_column(Enum(PackageStatus), default=PackageStatus.CREATED)
    
    # 特殊處理旗標
    is_hazardous: Mapped[bool] = mapped_column(Boolean, default=False)   # 易燃物/危險品
    is_fragile: Mapped[bool] = mapped_column(Boolean, default=False)     # 易碎品
    is_international: Mapped[bool] = mapped_column(Boolean, default=False) # 國際件
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now) # 寄件時間
    estimated_delivery: Mapped[datetime] = mapped_column(DateTime, nullable=True) # 預計抵達時間
    
    shipping_cost: Mapped[float] = mapped_column(Float, default=0.0) # 運費金額
    
    # 關聯設定
    sender: Mapped["Customer"] = relationship("Customer", back_populates="packages", foreign_keys=[sender_id])
    tracking_events: Mapped[List["TrackingEvent"]] = relationship("TrackingEvent", back_populates="package", cascade="all, delete-orphan")
    
    # 負責派送的司機
    assigned_driver_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id'), nullable=True)
    assigned_driver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_driver_id])

    @property
    def status_label(self):
        """獲取物流狀態的中文顯示名稱"""
        return PACKAGE_STATUS_LABELS.get(self.status, self.status.value)

    @property
    def delivery_speed_label(self):
        """獲取服務類型的中文顯示名稱"""
        labels = {
            DeliverySpeed.OVERNIGHT: "隔夜達",
            DeliverySpeed.TWO_DAY: "兩日達",
            DeliverySpeed.STANDARD: "標準速遞",
            DeliverySpeed.ECONOMY: "經濟速遞"
        }
        return labels.get(self.delivery_speed, self.delivery_speed.value)

class TrackingEvent(Base):
    """物流軌跡事件 (每當包裹被掃描一次就會新增一筆)"""
    __tablename__ = 'tracking_events'

    id: Mapped[int] = mapped_column(primary_key=True)
    package_id: Mapped[int] = mapped_column(ForeignKey('packages.id'), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now) # 掃描時間
    location: Mapped[str] = mapped_column(String(100), nullable=False) # 掃描地點 (例如：台北分揀中心)
    status: Mapped[PackageStatus] = mapped_column(Enum(PackageStatus), nullable=False) # 當時狀態
    description: Mapped[str] = mapped_column(String(255), nullable=False) # 詳細描述 (例如：包裹已抵達...)
    
    # 選擇性：記錄是由哪位員工操作掃描的
    handled_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id'), nullable=True)
    
    package: Mapped["Package"] = relationship("Package", back_populates="tracking_events")

    @property
    def status_label(self):
        """獲取物流狀態的中文顯示名稱"""
        return PACKAGE_STATUS_LABELS.get(self.status, self.status.value)

class PricingRule(Base):
    """運費計算規則表"""
    __tablename__ = 'pricing_rules'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    service_type: Mapped[DeliverySpeed] = mapped_column(Enum(DeliverySpeed), unique=True) # 服務等級
    base_rate: Mapped[float] = mapped_column(Float, nullable=False)   # 起步價 (基本費用)
    rate_per_kg: Mapped[float] = mapped_column(Float, nullable=False) # 每公斤加收金額
    rate_per_km: Mapped[float] = mapped_column(Float, default=0.5)    # 每公里加收金額 (簡易里程計算用)

class Bill(Base):
    """帳單/發票資訊"""
    __tablename__ = 'bills'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey('customers.id'), nullable=False)
    package_id: Mapped[int] = mapped_column(ForeignKey('packages.id'), nullable=False, unique=True) # 每個包裹對應一個帳單
    amount: Mapped[float] = mapped_column(Float, nullable=False) # 總計金額
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False) # 是否已付款
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True) # 付款日期
    
    customer: Mapped["Customer"] = relationship("Customer", back_populates="bills")
    package: Mapped["Package"] = relationship("Package", backref=backref("bill", uselist=False))
    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(Enum(PaymentMethod), nullable=True)

class WarehouseStaff(Employee):
    """倉儲人員類別 (繼承自 Employee，具備操作包裹的方法)"""
    __tablename__ = 'warehouse_staff'
    
    id: Mapped[int] = mapped_column(ForeignKey('employees.id'), primary_key=True)
    warehouse_location_id: Mapped[str] = mapped_column(String(50), nullable=True) # 隸屬的倉庫編號
    
    __mapper_args__ = {
        'polymorphic_identity': 'warehouse_staff',
    }
    
    def create_package(self, properties):
        """
        建立新包裹的邏輯處理
        :param properties: 包含寄件人、收件人與包裹規格的字典
        """
        from . import services # 延遲匯入避免循環引用
        
        sender_id = properties.get('sender_id')
        recipient_data = {
            'name': properties.get('recipient_name'),
            'address': properties.get('recipient_address'),
            'phone': properties.get('recipient_phone')
        }
        package_data = {
            'weight': properties.get('weight'),
            'width': properties.get('width'),
            'height': properties.get('height'),
            'length': properties.get('length'),
            'package_type': properties.get('package_type', 'SMALL_BOX'),
            'delivery_speed': properties.get('delivery_speed', 'STANDARD'),
            'declared_value': properties.get('declared_value', 0),
            'content_description': properties.get('content_description', ''),
            'is_hazardous': properties.get('is_hazardous', False),
            'is_fragile': properties.get('is_fragile', False),
            'is_international': properties.get('is_international', False)
        }
        payment_method = properties.get('payment_method', PaymentMethod.CASH)
        
        # 呼叫後端服務層邏輯來建立包裹
        return services.create_package(sender_id, recipient_data, package_data, payment_method)

    def record_tracking_event(self, tracking_number, status, description):
        """
        記錄一筆新的掃描軌跡
        """
        from . import services
        # 若無明確地點，則使用倉庫人員所屬的倉庫編號
        location = self.warehouse_location_id or f"Warehouse Staff {self.id}"
        return services.add_tracking_event(tracking_number, status, location, description, user_id=self.id)

    def handle_package_anomaly(self, tracking_number, description):
        """
        處理包裹異常狀況 (例如發現外箱毀損)
        """
        from . import services
        location = self.warehouse_location_id or f"Warehouse Staff {self.id}"
        # 將狀態設為 DAMAGED 並記錄描述
        return services.add_tracking_event(tracking_number, PackageStatus.DAMAGED.name, location, f"Anomaly: {description}", user_id=self.id)

class AuditLog(Base):
    """系統操作日誌 (記錄所有重要的系統操作)"""
    __tablename__ = 'audit_logs'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)  # 操作者 ID
    action: Mapped[str] = mapped_column(String(50), nullable=False)  # 執行的動作
    target_id: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 被操作的對象 (可能是包裹追蹤號、用戶ID等)
    details: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # 額外描述
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)  # 操作時間
    
    # 關聯：操作者
    user: Mapped["User"] = relationship("User")