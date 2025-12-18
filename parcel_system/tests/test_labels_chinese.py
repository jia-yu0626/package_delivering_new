
import unittest
from app.models import Package, DeliverySpeed, PackageStatus, Customer, CustomerType

class TestChineseLabels(unittest.TestCase):
    def test_package_delivery_speed_labels(self):
        # Test all delivery speeds
        p_overnight = Package(delivery_speed=DeliverySpeed.OVERNIGHT)
        self.assertEqual(p_overnight.delivery_speed_label, "隔夜達")
        
        p_2day = Package(delivery_speed=DeliverySpeed.TWO_DAY)
        self.assertEqual(p_2day.delivery_speed_label, "兩日達")
        
        p_std = Package(delivery_speed=DeliverySpeed.STANDARD)
        self.assertEqual(p_std.delivery_speed_label, "標準速遞")
        
        p_eco = Package(delivery_speed=DeliverySpeed.ECONOMY)
        self.assertEqual(p_eco.delivery_speed_label, "經濟速遞")

    def test_package_status_labels(self):
        # Sample check for status
        p = Package(status=PackageStatus.CREATED)
        self.assertEqual(p.status_label, "已建立")
        
        p = Package(status=PackageStatus.DELIVERED)
        self.assertEqual(p.status_label, "已送達")

    def test_customer_type_labels(self):
        # Sample check for customer type
        c = Customer(customer_type=CustomerType.CONTRACT)
        self.assertEqual(c.type_label, "合約客戶")

if __name__ == '__main__':
    unittest.main()
