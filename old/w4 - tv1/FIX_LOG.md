# Week 4 Fix Log

## Lỗi đã sửa
1. **ModuleNotFoundError: No module named sklearn**
   - Thêm `requirements.txt`.
   - Thêm `INSTALL_WEEK4.bat` để cài đúng package trên Windows.
   - Notebook có cell tự kiểm tra/cài package.

2. **FileNotFoundError: model_ready_v1_TV1_fallback.csv**
   - File fallback cũ không tồn tại trong project.
   - Bản mới dùng `w4 - tv1/model_ready_v1.csv`.
   - Nếu file này thiếu, code tự tạo từ `data_processed/retake_pairs_v1.csv`.

3. **NameError: results_df is not defined**
   - Nguyên nhân: cell model chưa chạy thành công / bị lỗi trước đó.
   - Bản mới tạo `results_df` rõ ràng ở cell Cross-Validation.
   - Cell chart có guard với thông báo dễ hiểu.

4. **Đường dẫn notebook phụ thuộc current working directory**
   - Bản mới tự tìm project root dựa trên `data_processed/retake_pairs_v1.csv`.

## Cách chạy đề xuất
### Notebook
1. Mở `TV1_Regression_Master.ipynb`.
2. Chọn đúng Python Kernel ở góc phải VS Code.
3. `Restart Kernel`.
4. `Run All`.

### Python script
Trong Terminal tại folder `w4 - tv1`:
```bat
INSTALL_WEEK4.bat
py TV1_Regression_Master.py
```
