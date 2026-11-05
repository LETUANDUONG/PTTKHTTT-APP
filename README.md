# Hoodoo

Web thương mại điện tử văn phòng phẩm theo chương 1–4 của `E-commerce-pttkht.docx` và các sơ đồ trong `VPP-diagrams`. Backend Python Flask, frontend React + Vite, PostgreSQL 17. Giao diện tham khảo bố cục [ADCBook](https://adcbook.net.vn/), sử dụng thương hiệu dự án Hoodoo và minh hoạ sản phẩm local. App và PostgreSQL chạy bằng Docker Compose; lịch sử Git được giữ.

## Chạy bằng Docker trên Windows

Cần Docker Desktop đang chạy với Linux containers. Từ thư mục dự án:

```powershell
.\run.ps1
```

Script tạo `.env` với mật khẩu PostgreSQL và session secret ngẫu nhiên nếu chưa có, build React trong Docker, tải model AI nếu thiếu và khởi động hai service. Mở [Hoodoo Docker](http://localhost:8080). Không cần Python hoặc Node trên máy để deploy.

Nếu cấu hình thủ công: sao chép `.env.example` thành `.env`, thay hai giá trị `replace-with-...`, rồi chạy `docker compose up --build -d --wait`.

- `app`: React production bundle được Flask/Gunicorn phục vụ, cổng `127.0.0.1:8080`.
- `db`: PostgreSQL 17, cổng `127.0.0.1:5432`, database/user mặc định `hoodoo`; password trong `.env`.
- Dữ liệu nằm trong named volume `hoodoo_postgres_data`; `docker compose down` giữ dữ liệu. **Không dùng `down -v` nếu cần giữ database.**
- `APP_PORT`, `POSTGRES_PORT`, `DEMO_MODE` và `COOKIE_SECURE` cấu hình trong `.env`. App chờ database healthy; `/healthz` kiểm tra kết nối DB.
- Thay `POSTGRES_PASSWORD` trong `.env` không tự đổi mật khẩu của database đã có volume; cần đổi role password trong PostgreSQL đồng thời.

```powershell
docker compose ps
docker compose logs --tail 100 app db
docker compose stop
docker compose up -d --wait
```

Database PostgreSQL mới được seed catalogue và tài khoản demo. File SQLite cũ `instance/hoodoo.sqlite` được giữ nguyên, không tự import vào PostgreSQL.

## Model tìm kiếm local

Lần đầu cần mạng để cài các gói trong `requirements-ai.txt` và tải model. Bước build dùng mirror PyPI Aliyun do đường tải PyPI trực tiếp chậm; PyTorch tải từ kho CPU chính thức. Có thể chọn PyPI gốc bằng `docker compose build --build-arg PYPI_INDEX=https://pypi.org/simple app`. Sau đó runtime dùng model local, mount read-only; không cần API key.

```powershell
docker compose build app
docker compose run --rm --no-deps -e HF_HUB_OFFLINE=0 -e TRANSFORMERS_OFFLINE=0 -v "${PWD}/models:/app/models" app python scripts/download_models.py
docker compose up -d --wait
```

Model nằm tại `models/whisper-small` và `models/clip-vit-b32`, Git ignored. Nếu thiếu model, API trả 503 kèm hướng dẫn. Model được giữ trong RAM và vector catalogue được cache theo file ảnh. CPU được giới hạn 4 thread mỗi engine; lần tìm đầu tiên cần thời gian nạp model. Cho phép micro ở `http://localhost:8080`, nói tên sản phẩm, bấm lại micro để dừng hoặc chờ tự dừng.

## Tài khoản demo

Mật khẩu chung: `Hoodoo@12345`. Tài khoản chỉ seed khi DB chưa có user và `DEMO_MODE=1` (mặc định).

| Email | Quyền |
|---|---|
| customer@hoodoo.local | Mua hàng và đơn riêng |
| admin@hoodoo.local | Catalogue, danh mục, khách hàng, ưu đãi và toàn bộ vận hành |
| warehouse@hoodoo.local | Kho, bổ sung hàng và fulfilment |
| sales@hoodoo.local | Đơn hàng, giao hàng và hỗ trợ |
| manager@hoodoo.local | Báo cáo và CSV |

Đăng nhập admin rồi vào **Quản trị**. Mã `HOODOO10` giảm 10% cho đơn từ 50.000đ, không cộng dồn. Phí giao hàng 25.000đ; miễn khi giá trị hàng sau ưu đãi từ 300.000đ.

## Chức năng

- Đăng ký, đăng nhập, profile, đổi mật khẩu, recovery token một lần và vô hiệu hoá tài khoản.
- Browse, keyword không dấu, bộ lọc kết hợp, sort, phân trang, detail, thông số, đơn vị bán và review.
- Tìm giọng nói tiếng Việt bằng Faster Whisper local; tìm ảnh PNG/JPEG/WebP bằng CLIP local, không dùng API trả phí.
- Giỏ khách vãng lai, gộp giỏ khi login, quantity, checkout quote, promotion, order snapshot và idempotency.
- Giữ kho trong transaction trước thanh toán; pending/failed/success tách biệt; retry trên cùng order, cancel đủ điều kiện, in-app notifications.
- Catalogue/category/promotion/customer administration; lịch sử kho, receipt/adjustment, replenishment, picking/packing/dispatch/delivery.
- Vận đơn và tracking nhập tay có chống event trùng; support cases, ngoại lệ vận hành và audit.
- Review sau giao hàng; báo cáo kỳ UTC, doanh thu payment đã thu, tồn thực tế/đã giữ/khả dụng và CSV.

## Tài liệu thiết kế

Bốn tài liệu này được tạo trước khi code, theo cách tổ chức docs DueMate:

1. [Architecture](docs/architecture.md)
2. [UI design](docs/ui-design.md)
3. [API definition](docs/api-definition.md)
4. [Testing](docs/testing.md)

[Biên bản kiểm thử](docs/test-evidence.md), [kết quả pytest XML](docs/pytest-results.xml), [kết quả Playwright JSON](docs/playwright-results.json), [inventory sơ đồ VPP](docs/vpp-inventory.json). `source-document.txt` giữ bản trích xuất đọc nguồn với tên thương hiệu đã chuẩn hóa thành Hoodoo; chương 5 không được dùng làm đặc tả.

```text
backend/
  presentation/          Sáu controller HTTP theo sơ đồ 3-layer
  application/           Các service và SearchOrchestrator
  data_infrastructure/   Database, indexes, adapters và image storage
  shared/                Validation, lỗi và project paths
  app.py                 Composition root
frontend/src/
  presentation/          CustomerUI, AdminStaffUI và UI dùng chung
  data_infrastructure/   HTTP client và SpeechRecognitionAdapter
  main.jsx               React entry point
frontend/e2e/            Playwright desktop/mobile tests
tests/         Python API/integration/concurrency/backup tests
scripts/       Tải model, server E2E và database riêng cho kiểm thử
docs/          Thiết kế, nguồn đối chiếu và test evidence
instance/      SQLite cũ, Git ignored; runtime mới dùng PostgreSQL volume
run.py         Entry point backend + production React bundle
run.ps1        Tạo .env và deploy bằng Docker Compose
test.ps1       Chạy toàn bộ kiểm thử
```

## Kiểm thử

Backend chạy trên PostgreSQL thật trong Docker, mỗi test tạo database `hoodoo_test_<uuid>` riêng và xóa khi kết thúc; không reset database ứng dụng. Role test cần quyền CREATEDB.

```powershell
docker compose run --rm app python -m pytest -q
```

Để chạy cả backend và Playwright trên Windows (cần Python 3.12+, Node.js 20.19+/22.12+, Microsoft Edge):

```powershell
.\test.ps1
```

Playwright khởi động backend AI trong container riêng, dùng database PostgreSQL riêng, port 5099; không cài PyTorch trên Windows. Hai project là desktop Edge 1440×1000 và mobile viewport/touch 390×664 bằng Chromium/Edge; không phải Safari hoặc điện thoại vật lý. Screenshots ở `docs/evidence/` (Git ignored). Lần kiểm thử sau đổi tên Hoodoo: **32 pytest passed, 10 Playwright passed**, frontend production build pass; evidence SQLite cũ chỉ là lịch sử.

## Phát triển không dùng container app

Ưu tiên chạy app AI trong Docker. Nếu chạy Flask ngoài container, dùng Python 3.12, cài cả `requirements.lock.txt` và `requirements-ai.txt`; giữ PostgreSQL trong Docker và cài Node dependencies. Đặt `DATABASE_URL` bằng DSN PostgreSQL của bạn, hoặc dùng các biến libpq `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD` (password lấy từ `.env`). Flask không tự đọc `.env`.

```powershell
docker compose up -d --wait db
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.lock.txt
npm --prefix frontend ci
npm --prefix frontend run build
# Đặt biến kết nối PostgreSQL trước lệnh sau.
.\.venv\Scripts\python run.py
```

Flask dev server ở [Hoodoo local](http://127.0.0.1:5000). `npm --prefix frontend run dev` chạy Vite với proxy `/api` tới port 5000. Chạy `npm --prefix frontend run build` để cập nhật bundle Flask phục vụ.

## Backup và restore PostgreSQL

Dùng file trong container rồi `docker compose cp` để tránh PowerShell làm hỏng dữ liệu dump nhị phân:

```powershell
New-Item -ItemType Directory -Force backups
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc -f /tmp/hoodoo.dump'
docker compose cp db:/tmp/hoodoo.dump backups/hoodoo.dump
```

Restore vào **database mới**, giữ nguyên database hiện tại:

```powershell
docker compose cp backups/hoodoo.dump db:/tmp/hoodoo-restore.dump
docker compose exec -T db sh -c 'createdb -U "$POSTGRES_USER" hoodoo_restored'
docker compose exec -T db sh -c 'pg_restore -U "$POSTGRES_USER" --exit-on-error --no-owner --no-privileges -d hoodoo_restored /tmp/hoodoo-restore.dump'
```

Sau khi kiểm tra database khôi phục, đổi `POSTGRES_DB=hoodoo_restored` trong `.env` và chạy `docker compose up -d --force-recreate --wait`. Database đích phải mới; không restore đè app đang chạy. Chưa chốt RPO/RTO production.

## Giới hạn tích hợp

Đây là bản local để chạy và kiểm thử đồ án. Online payment không thu tiền thật; màn hình demo cho chọn pending/success/failed. Vận chuyển và supplier là ghi nhận nội bộ/nhập tay. Recovery demo hiển thị link local, chưa gửi email. Không có hoàn tiền tự động.

Image search dùng CLIP ViT-B/32, xếp hạng cosine similarity; kết quả tương tự không đảm bảo cùng mã hoặc đơn vị bán. Voice dùng MediaRecorder và Faster Whisper small tiếng Việt, CPU int8; tối đa 15 giây/5 MB, nút micro tự dừng sau 8 giây. Hai model xử lý local; backend không lưu audio hoặc ảnh truy vấn. Kết quả kiểm thử thật và phần mô phỏng được phân biệt trong docs/test-evidence.md.

Chưa chứng nhận uptime, tải production, TLS, mã hoá ổ đĩa, mail/provider thật hoặc mức độ liên quan AI. Secret mặc định random theo lần boot nên session sẽ hết hạn khi restart; đặt biến môi trường `SECRET_KEY` ổn định nếu muốn giữ session. `COOKIE_SECURE=1` dành cho HTTPS. Không public bản demo với seed credentials hoặc recovery demo. `DEMO_MODE=0` tắt các demo endpoint và seed demo, nhưng chưa thay thế các tích hợp production.

Tham khảo kỹ thuật: [Flask testing](https://flask.palletsprojects.com/en/stable/testing/), [Vite](https://vite.dev/guide/), [MediaRecorder](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder), [Faster Whisper](https://github.com/SYSTRAN/faster-whisper), [CLIP image search](https://sbert.net/examples/sentence_transformer/applications/image-search/README.html).
