# Thiết kế giao diện Hoodoo

## 1. Hướng hình ảnh
Tham khảo https://adcbook.net.vn/: header tìm kiếm lớn, menu danh mục bên trái, banner ngang, dải tiện ích, product grid và giá VND nổi bật. Dùng thương hiệu dự án Hoodoo, không giả mạo ADCBook. Một storefront văn phòng phẩm nhiều sản phẩm, không biến thành landing page SaaS.

Palette tham khảo [STHM](https://sthm.vn/): be #f4e8d0, xanh rêu #455c0c, nền kem #f8f4ea, bề mặt #fffcf5, chữ #353b2a, viền #ded7c6. Nút, logo, giá và trạng thái chọn dùng xanh rêu; header, footer và hero dùng be. Màu đỏ chỉ dành cho lỗi/cảnh báo thất bại. Typography Be Vietnam Pro, fallback Segoe UI / Arial hỗ trợ tiếng Việt. Giữ nguyên bố cục, kích thước và responsive hiện tại.

```text
[tiện ích / chính sách demo]
[hoodoo] [tìm kiếm........ mic ảnh] [tài khoản] [đơn] [giỏ]
[danh mục] [trang chủ] [sản phẩm] [ưu đãi] [hỗ trợ]
[category rail] [banner giấy bút tập vở] [ưu đãi nhỏ]
[giao hàng] [đơn vị rõ ràng] [hỗ trợ] [kiểm tra tồn kho]
[filter category brand price stock] [sort]
[product][product][product][product]
```
Review theo brief: bỏ hero trống với slogan chung; banner minh hoạ dụng cụ học tập và rail danh mục tạo trọng tâm mua sắm. Các ảnh catalogue là minh hoạ tự tạo local, không phụ thuộc hotlink.

## 2. Màn hình và luồng
- Home/catalogue: category, keyword, price min/max, brand, availability, thuộc tính dạng key:value, sort, phân trang, clear filters; ảnh search ranking có nhãn giới hạn similarity.
- Detail route /product/:id: ảnh, mô tả, brand, category, specs, selling unit, pack qty, price, availability, quantity, add; review listing và review form nếu đăng nhập.
- Cart: chỉnh quantity nguyên dương, xoá, subtotal; empty có link mua hàng. Checkout: name, phone, address, payment, promo, full breakdown; lưu input khi lỗi; gửi idempotency key giữ nguyên khi retry mạng.
- Auth/account: login/register/profile/password/recovery/reset; error gần form; người dùng thấy role và demo status. Không dùng alert/prompt cho thao tác chính.
- Orders: lịch sử own orders, payment riêng order/shipping, timeline, snapshot, pending tracking, retry payment, cancel eligible và service request.
- Demo payment: màn hình riêng ghi rõ không thu tiền; pending/success/failure trên cùng order. Double click không tạo lại đơn.
- Staff workspace: tabs theo role. Product/category editor; promotions; customer status; inventory receipt/adjustment + movement history; replenishment; fulfilment/shipment; support cases; audit và report period. Không hiển thị tab ngoài role.
- Reports: kỳ UTC, generated time, paid revenue không gồm COD chưa thu, counts theo trạng thái, on-hand/reserved/available, promotion/service metrics, CSV export.

## 3. Trạng thái và accessibility
Loading có text; success có feedback; empty có hướng thoát; lỗi có retry hoặc sửa form, giữ dữ liệu hợp lệ. Giá/tồn kho luôn từ server. Button pending disabled chống double submit. Labels rõ, keyboard focus visible, aria-live thông báo, modal role dialog + Escape/return focus. Không chỉ dùng màu cho payment/status.
Desktop content 1240px. <=1000px bỏ rail và đưa categories vào thanh cuộn. <=640px header wrap, grid 2 cột, form/card theo một cột; cart và staff table cuộn trong container không tràn viewport. Reduced motion tắt transition. Phải xem screenshot desktop/mobile trước bàn giao.

## 4. Phạm vi xác minh
E2E đi qua browse/detail/cart/register/checkout/payment/order và staff. Microphone thực và relevance của image baseline ghi riêng, không suy ra từ mocked browser API.
