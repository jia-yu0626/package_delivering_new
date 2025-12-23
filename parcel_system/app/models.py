from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean, Text
from sqlalchemy.orm import relationship, Mapped, mapped_column, backref
from werkzeug.security import generate_password_hash, check_password_hash
import enum
from .extensions import Base

# --- Enums (列舉) ---
class UserRole(enum.Enum):
    CUSTOMER = "customer"
    DRIVER = "driver"
    WAREHOUSE = "warehouse"
    ADMIN = "admin"
    CS = "customer_service" # 客服

class CustomerType(enum.Enum):
    CONTRACT = "contract" # 合約
    NON_CONTRACT = "non_contract" # 非合約
    PREPAID = "prepaid" # 預付

class PackageType(enum.Enum):
    ENVELOPE = "envelope" # 平郵信封
    SMALL_BOX = "small_box" # 小型箱
    MEDIUM_BOX = "medium_box" # 中型箱
    LARGE_BOX = "large_box" # 大型箱

class DeliverySpeed(enum.Enum):
    OVERNIGHT = "overnight" # 隔夜達
    TWO_DAY = "two_day" # 兩日達
    STANDARD = "standard" # 標準速遞
    ECONOMY = "economy" # 經濟速遞

class PackageStatus(enum.Enum):
    CREATED = "created" # 已建立
    PICKED_UP = "picked_up" # 已取件
    IN_TRANSIT = "in_transit" # 運送中 (進出貨車/倉儲)
    SORTING = "sorting" # 分揀中
    OUT_FOR_DELIVERY = "out_for_delivery" # 派送中
    DELIVERED = "delivered" # 已送達
    EXCEPTION = "exception" # 異常 (General)
    LOST = "lost" # 遺失
    DELAYED = "delayed" # 延誤
    DAMAGED = "damaged" # 損毀

class PaymentMethod(enum.Enum):
    MONTHLY = "monthly" # 月結
    CASH = "cash" # 現金
    CREDIT_CARD = "credit_card" # 信用卡
    MOBILE_PAYMENT = "mobile_payment" # 行動支付
    PREPAID = "prepaid" # 預付

# --- Models (類別) ---

class User(Base):
    __tablename__ = 'users'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)
    address: Mapped[str] = mapped_column(String(200), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.CUSTOMER)
    
    # Polymorphic identity configuration
    type: Mapped[str] = mapped_column(String(50))
    
    __mapper_args__ = {
        'polymorphic_identity': 'user',
        'polymorphic_on': type
    }

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Customer(User):
    __tablename__ = 'customers'
    
    id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    customer_type: Mapped[CustomerType] = mapped_column(Enum(CustomerType), default=CustomerType.NON_CONTRACT)
    billing_preference: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod), default=PaymentMethod.CASH)
    balance: Mapped[float] = mapped_column(Float, default=0.0) # For Prepaid customers
    
    packages: Mapped[List["Package"]] = relationship("Package", back_populates="sender")
    bills: Mapped[List["Bill"]] = relationship("Bill", back_populates="customer")

    __mapper_args__ = {
        'polymorphic_identity': 'customer',
    }

    @property
    def type_label(self):
        labels = {
            CustomerType.CONTRACT: "合約客戶",
            CustomerType.NON_CONTRACT: "非合約客戶",
            CustomerType.PREPAID: "預付客戶"
        }
        return labels.get(self.customer_type, "一般客戶")

class Employee(User):
    __tablename__ = 'employees'
    id: Mapped[int] = mapped_column(ForeignKey('users.id'), primary_key=True)
    department: Mapped[str] = mapped_column(String(50), nullable=True)
    
    __mapper_args__ = {
        'polymorphic_identity': 'employee',
    }

class Package(Base):
    __tablename__ = 'packages'

    id: Mapped[int] = mapped_column(primary_key=True)
    tracking_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    sender_id: Mapped[int] = mapped_column(ForeignKey('customers.id'), nullable=False)
    recipient_name: Mapped[str] = mapped_column(String(100), nullable=False)
    recipient_address: Mapped[str] = mapped_column(String(200), nullable=False)
    recipient_phone: Mapped[str] = mapped_column(String(20), nullable=False)
    
    weight: Mapped[float] = mapped_column(Float, nullable=False) # kg
    width: Mapped[float] = mapped_column(Float, nullable=False) # cm
    height: Mapped[float] = mapped_column(Float, nullable=False) # cm
    length: Mapped[float] = mapped_column(Float, nullable=False) # cm
    declared_value: Mapped[float] = mapped_column(Float, default=0.0)
    content_description: Mapped[str] = mapped_column(String(255), nullable=True)
    
    package_type: Mapped[PackageType] = mapped_column(Enum(PackageType), default=PackageType.SMALL_BOX)
    delivery_speed: Mapped[DeliverySpeed] = mapped_column(Enum(DeliverySpeed), default=DeliverySpeed.STANDARD)
    status: Mapped[PackageStatus] = mapped_column(Enum(PackageStatus), default=PackageStatus.CREATED)
    
    # Special Handling Flags
    is_hazardous: Mapped[bool] = mapped_column(Boolean, default=False)
    is_fragile: Mapped[bool] = mapped_column(Boolean, default=False)
    is_international: Mapped[bool] = mapped_column(Boolean, default=False)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    estimated_delivery: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    
    # Pricing
    shipping_cost: Mapped[float] = mapped_column(Float, default=0.0)
    
    sender: Mapped["Customer"] = relationship("Customer", back_populates="packages", foreign_keys=[sender_id])
    tracking_events: Mapped[List["TrackingEvent"]] = relationship("TrackingEvent", back_populates="package", cascade="all, delete-orphan")
    
    # Driver Assignment
    assigned_driver_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id'), nullable=True)
    assigned_driver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[assigned_driver_id])

    @property
    def status_label(self):
        labels = {
            PackageStatus.CREATED: "已建立",
            PackageStatus.PICKED_UP: "已取件",
            PackageStatus.IN_TRANSIT: "運送中",
            PackageStatus.SORTING: "分揀中",
            PackageStatus.OUT_FOR_DELIVERY: "派送中",
            PackageStatus.DELIVERED: "已送達",
            PackageStatus.EXCEPTION: "異常狀況",
            PackageStatus.LOST: "遺失包裹",
            PackageStatus.DELAYED: "配送延誤",
            PackageStatus.DAMAGED: "包裹損毀"
        }
        return labels.get(self.status, self.status.value)

    @property
    def delivery_speed_label(self):
        labels = {
            DeliverySpeed.OVERNIGHT: "隔夜達",
            DeliverySpeed.TWO_DAY: "兩日達",
            DeliverySpeed.STANDARD: "標準速遞",
            DeliverySpeed.ECONOMY: "經濟速遞"
        }
        return labels.get(self.delivery_speed, self.delivery_speed.value)

class TrackingEvent(Base):
    __tablename__ = 'tracking_events'

    id: Mapped[int] = mapped_column(primary_key=True)
    package_id: Mapped[int] = mapped_column(ForeignKey('packages.id'), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    location: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[PackageStatus] = mapped_column(Enum(PackageStatus), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    
    # Optional: Link to the employee who scanned it
    handled_by_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id'), nullable=True)
    
    package: Mapped["Package"] = relationship("Package", back_populates="tracking_events")

    @property
    def status_label(self):
        labels = {
            PackageStatus.CREATED: "已建立",
            PackageStatus.PICKED_UP: "已取件",
            PackageStatus.IN_TRANSIT: "運送中",
            PackageStatus.SORTING: "分揀中",
            PackageStatus.OUT_FOR_DELIVERY: "派送中",
            PackageStatus.DELIVERED: "已送達",
            PackageStatus.EXCEPTION: "異常狀況",
            PackageStatus.LOST: "遺失包裹",
            PackageStatus.DELAYED: "配送延誤",
            PackageStatus.DAMAGED: "包裹損毀"
        }
        return labels.get(self.status, self.status.value)

class PricingRule(Base):
    __tablename__ = 'pricing_rules'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    service_type: Mapped[DeliverySpeed] = mapped_column(Enum(DeliverySpeed), unique=True)
    base_rate: Mapped[float] = mapped_column(Float, nullable=False)
    rate_per_kg: Mapped[float] = mapped_column(Float, nullable=False)
    rate_per_km: Mapped[float] = mapped_column(Float, default=0.5) # Simplified distance metric

class Bill(Base):
    __tablename__ = 'bills'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey('customers.id'), nullable=False)
    package_id: Mapped[int] = mapped_column(ForeignKey('packages.id'), nullable=False, unique=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    is_paid: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    
    customer: Mapped["Customer"] = relationship("Customer", back_populates="bills")
    package: Mapped["Package"] = relationship("Package", backref=backref("bill", uselist=False))
    payment_method: Mapped[Optional[PaymentMethod]] = mapped_column(Enum(PaymentMethod), nullable=True)

# Update Customer to include bills relationship
# Customer.bills = relationship("Bill", back_populates="customer")

class WarehouseStaff(Employee):
    __tablename__ = 'warehouse_staff'
    
    id: Mapped[int] = mapped_column(ForeignKey('employees.id'), primary_key=True)
    warehouse_location_id: Mapped[str] = mapped_column(String(50), nullable=True) # warehouseLocationID
    
    __mapper_args__ = {
        'polymorphic_identity': 'warehouse_staff',
    }
    
    def create_package(self, properties):
        """
        createPackage(properties): Create a package.
        properties: dict containing sender_id, recipient info, package info.
        """
        from . import services
        # Assuming properties dict matches services.create_package arguments structure
        # We need sender_id, recipient_data, package_data
        
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
        
        return services.create_package(sender_id, recipient_data, package_data, payment_method)

    def record_tracking_event(self, tracking_number, status, description):
        """
        recordTrackingEvent(): Record a tracking event.
        """
        from . import services
        # Uses own warehouse_location_id as location default if available, else generic
        location = self.warehouse_location_id or f"Warehouse Staff {self.id}"
        return services.add_tracking_event(tracking_number, status, location, description, user_id=self.id)

    def handle_package_anomaly(self, tracking_number, description):
        """
        handlePackageAnomaly(): Handle package anomaly (e.g., damage).
        """
        from . import services
        location = self.warehouse_location_id or f"Warehouse Staff {self.id}"
        # Records as DAMAGED or uses description to determine
        return services.add_tracking_event(tracking_number, PackageStatus.DAMAGED.name, location, f"Anomaly: {description}", user_id=self.id)

